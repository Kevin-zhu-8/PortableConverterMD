"""PortableConverterMD — 转换引擎与日志"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------
# 工具
# ------------------------------------------------------------


def get_app_dir() -> str:
    """获取应用根目录（源码运行或 PyInstaller 打包均正确）。"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS  # PyInstaller 数据文件所在目录
    return os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------
# 日志
# ------------------------------------------------------------

_logger = None
_file_handler = None


def get_logger(with_file: str = "") -> logging.Logger:
    """获取日志记录器。
    - 不传参：仅控制台输出
    - 传目录路径：同时写 conversion.log 到该目录
    """
    global _logger, _file_handler
    if _logger is None:
        _logger = logging.getLogger("PortableConverterMD")
        _logger.setLevel(logging.DEBUG)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        ))
        _logger.addHandler(console)

    if with_file:
        if _file_handler:
            _file_handler.close()
            _logger.removeHandler(_file_handler)
            _file_handler = None
        os.makedirs(with_file, exist_ok=True)
        log_path = os.path.join(with_file, "conversion.log")
        _file_handler = logging.FileHandler(log_path, encoding="utf-8")
        _file_handler.setLevel(logging.DEBUG)
        _file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        _logger.addHandler(_file_handler)
        _logger.info(f"=== PortableConverterMD 日志开始 {datetime.now():%Y-%m-%d %H:%M:%S} ===")

    return _logger


def close_file_log():
    """关闭文件日志 handler（释放文件句柄）。"""
    global _logger, _file_handler
    if _file_handler:
        _file_handler.close()
        if _logger:
            _logger.removeHandler(_file_handler)
        _file_handler = None


# ------------------------------------------------------------
# 转换
# ------------------------------------------------------------

_md = None


def _get_converter():
    """延迟初始化 MarkItDown 实例（首次转换时才加载）。"""
    global _md
    if _md is None:
        from markitdown import MarkItDown
        _md = MarkItDown()
    return _md


def _ocr_pdf(file_path: str) -> str:
    """对 PDF 逐页 OCR，返回拼接文本。自动检测项目内的 Tesseract。"""
    try:
        import pytesseract
    except ImportError:
        raise RuntimeError("OCR 需要 pytesseract，请执行 pip install pytesseract")

    # 优先使用项目内置的 Tesseract
    bundled = os.path.join(get_app_dir(), "tesseract", "tesseract.exe")
    if os.path.exists(bundled):
        pytesseract.pytesseract.tesseract_cmd = bundled
        # 设置 tessdata 目录
        tessdata_dir = os.path.join(get_app_dir(), "tesseract", "tessdata")
        if os.path.isdir(tessdata_dir):
            os.environ.setdefault("TESSDATA_PREFIX", tessdata_dir)

    # 检查 tesseract 是否可用
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        raise RuntimeError(
            "未找到 Tesseract-OCR。请将 tesseract.exe 放在程序目录下，或从 "
            "https://github.com/UB-Mannheim/tesseract/wiki 下载安装。"
        )

    import pypdfium2

    pdf = pypdfium2.PdfDocument(file_path)
    pages = []
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=2)
            img = bitmap.to_pil()
            # 自动检测可用语言（中文优先）
            lang = "chi_sim+eng" if os.path.exists(
                os.path.join(tessdata_dir, "chi_sim.traineddata")
            ) else "eng"
            text = pytesseract.image_to_string(img, lang=lang)
            if text.strip():
                pages.append(text.strip())
    finally:
        pdf.close()

    if not pages:
        raise RuntimeError("OCR 未能从 PDF 中识别出文字。")
    return "\n\n---\n\n".join(pages)


def convert_file(file_path: str, output_dir: str) -> str:
    """转换单个文件为 Markdown，返回输出文件路径。"""
    file_path = str(file_path)
    output_dir = str(output_dir)
    log = get_logger()

    os.makedirs(output_dir, exist_ok=True)

    input_name = Path(file_path).stem
    output_path = os.path.join(output_dir, f"{input_name}.md")
    ext = Path(file_path).suffix.lower()

    log.info(f"开始转换: {os.path.basename(file_path)}")

    # PDF 直接走 OCR，更快
    if ext == ".pdf":
        log.info("PDF 文件，直接使用 OCR…")
        text = _ocr_pdf(file_path)
    else:
        converter = _get_converter()
        result = converter.convert(file_path)
        text = result.text_content.strip()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    log.info(f"转换成功: {os.path.basename(file_path)} → {os.path.basename(output_path)}")
    return output_path
