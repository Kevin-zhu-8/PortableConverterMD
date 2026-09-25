"""OCR 后端

优先级：
1. Windows 内置 OCR（Windows.Media.Ocr，随系统提供，零体积、无需下载语言包之外的依赖）
2. Tesseract（可选回退）：程序目录下存在 `tesseract\\tesseract.exe` 时用 subprocess 调用，
   不引入 pytesseract，避免把 pandas/numpy 拉进打包

设计约束（实测）：
- 同一个 OcrEngine 实例不能并发调用 RecognizeAsync（会抛 "Another RecognizeAsync
  operation is already running"），因此 engine 存在 threading.local 里，一线程一份。
- Windows OCR 中文结果会在汉字间插入空格（"扫 描 件"），需要做 CJK 去空格后处理。
- 单页成本随像素增长（1000x400 -> 0.03s，3000x1200 -> 0.12s），无模型加载固定开销。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import threading

# ------------------------------------------------------------ 后端探测

_BACKEND_UNKNOWN = "unknown"
_backend = _BACKEND_UNKNOWN
_backend_lock = threading.Lock()
_local = threading.local()


def tesseract_exe() -> str:
    """外部 Tesseract 可执行文件路径；没有则返回空串。"""
    for cand in _tesseract_candidates():
        if os.path.exists(cand):
            return cand
    return ""


def _tesseract_candidates():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        yield os.path.join(base, "tesseract", "tesseract.exe")
    root = os.path.dirname(os.path.abspath(__file__))
    yield os.path.join(root, "tesseract", "tesseract.exe")


def _tessdata_dir() -> str:
    home = os.path.dirname(tesseract_exe()) if tesseract_exe() else ""
    d = os.path.join(home, "tessdata") if home else ""
    return d if d and os.path.isdir(d) else ""


def _tesseract_lang() -> str:
    d = _tessdata_dir()
    if d and os.path.exists(os.path.join(d, "chi_sim.traineddata")):
        return "chi_sim+eng"
    return "eng"


def _windows_modules():
    """返回 (OcrEngine, BitmapDecoder, InMemoryRandomAccessStream, DataWriter)。"""
    try:  # pywinrt >= 2.0 拆分包
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

        return OcrEngine, BitmapDecoder, InMemoryRandomAccessStream, DataWriter
    except ImportError:
        from winsdk.windows.graphics.imaging import BitmapDecoder  # type: ignore
        from winsdk.windows.media.ocr import OcrEngine  # type: ignore
        from winsdk.windows.storage.streams import (  # type: ignore
            DataWriter, InMemoryRandomAccessStream,
        )

        return OcrEngine, BitmapDecoder, InMemoryRandomAccessStream, DataWriter


def _windows_engine():
    """线程内缓存的 OcrEngine（并发调用必须一线程一份）。"""
    engine = getattr(_local, "win_engine", None)
    if engine is not None:
        return engine

    OcrEngine, _, _, _ = _windows_modules()
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        langs = list(OcrEngine.available_recognizer_languages)
        engine = OcrEngine.try_create_from_language(langs[0]) if langs else None
    if engine is None:
        raise RuntimeError("Windows 未安装任何 OCR 语言包")
    _local.win_engine = engine
    return engine


def backend() -> str:
    """返回当前可用后端：'windows' / 'tesseract' / ''（不可用）。结果缓存。"""
    global _backend
    if _backend != _BACKEND_UNKNOWN:
        return _backend
    with _backend_lock:
        if _backend != _BACKEND_UNKNOWN:
            return _backend
        name = ""
        try:
            _windows_modules()
            _windows_engine()
            name = "windows"
        except Exception:
            if tesseract_exe():
                name = "tesseract"
        _backend = name
        return _backend


def backend_label() -> str:
    b = backend()
    if b == "windows":
        try:
            lang = _windows_engine().recognizer_language.language_tag
        except Exception:
            lang = "?"
        return f"Windows OCR ({lang})"
    if b == "tesseract":
        return f"Tesseract ({_tesseract_lang()})"
    return "不可用"


# ------------------------------------------------------------ 文本清理

# 汉字/中文标点之间被 OCR 插入的空格需要去掉（"扫 描 件" -> "扫描件"）
_CJK = r"\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef"
_CJK_SPACE = re.compile(f"(?<=[{_CJK}])[ \t]+(?=[{_CJK}])")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")


def clean_text(text: str) -> str:
    """规整 OCR 输出：CJK 去内部空格、压缩连续空格、去掉行尾空白。"""
    if not text:
        return ""
    out_lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = _CJK_SPACE.sub("", line)
        line = _MULTI_SPACE.sub(" ", line).strip()
        if line:
            out_lines.append(line)
    return "\n".join(out_lines)


# ------------------------------------------------------------ 识别

def _recognize_windows(img) -> str:
    import asyncio
    import io

    OcrEngine, BitmapDecoder, InMemoryRandomAccessStream, DataWriter = _windows_modules()
    engine = _windows_engine()

    # 超过系统上限时等比缩小
    max_dim = OcrEngine.max_image_dimension
    if max(img.size) > max_dim:
        r = max_dim / max(img.size)
        img = img.resize((max(1, int(img.width * r)), max(1, int(img.height * r))))

    async def _run() -> str:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(buf.getvalue())
        await writer.store_async()
        await writer.flush_async()
        stream.seek(0)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        result = await engine.recognize_async(bitmap)
        return "\n".join(line.text for line in result.lines)

    return asyncio.run(_run())


def _recognize_tesseract(img) -> str:
    exe = tesseract_exe()
    if not exe:
        raise RuntimeError("未找到 Tesseract")
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, "page.png")
        img.convert("RGB").save(png, format="PNG")
        env = dict(os.environ)
        td_dir = _tessdata_dir()
        if td_dir:
            env["TESSDATA_PREFIX"] = td_dir
        creationflags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
        proc = subprocess.run(
            [exe, png, "stdout", "-l", _tesseract_lang(), "--oem", "1"],
            capture_output=True, env=env, creationflags=creationflags,
        )
        if proc.returncode != 0:
            err = (proc.stderr or b"").decode("utf-8", "replace").strip()
            raise RuntimeError(f"Tesseract 执行失败：{err[:200]}")
        return proc.stdout.decode("utf-8", "replace")


def recognize(img) -> str:
    """对 PIL.Image 做 OCR，返回清理后的文本。"""
    b = backend()
    if b == "windows":
        return clean_text(_recognize_windows(img))
    if b == "tesseract":
        return clean_text(_recognize_tesseract(img))
    raise RuntimeError(
        "本机没有可用的 OCR 引擎：Windows 未安装 OCR 语言包"
        "（设置 → 时间和语言 → 语言 → 添加语言功能 → 光学字符识别）。\n"
        "也可以在程序目录下放置 tesseract\\tesseract.exe 作为回退。"
    )
