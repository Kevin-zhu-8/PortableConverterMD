# -*- mode: python ; coding: utf-8 -*-
"""PortableConverterMD 打包规格（v2 精简版）

与 v1 的差别（均有实测依据，见 docs/architecture-review-v2-2026-09-25.md）：
1. 不再引入 markitdown[all] 及其传递依赖（magika/onnxruntime/pandas/numpy/azure/
   speech_recognition/boto3/IPython/jedi/sqlalchemy/psycopg2 …），只保留白名单库
2. OCR 用 Windows 内置 OCR（随系统提供），不再打包 Tesseract（省 216MB + 160MB 重复 DLL）
3. 裁掉 QWidgets 用不到的 Qt 二进制与插件（QML/Quick 栈、opengl32sw、QtSql/QtPdf…）
4. upx 关闭（压缩 DLL 会拖慢加载并提高杀软误报）
5. 在专用 venv 里构建，从源头避免全局环境的杂包被扫进来
"""
import os as _os
import glob as _glob
import importlib.util

_REPO = SPECPATH          # 本 spec 位于仓库根目录

# ---------------------------------------------------------------- datas
_SP = _os.path.dirname(importlib.util.find_spec("pypdfium2").origin)
_PP_RAW = _os.path.dirname(importlib.util.find_spec("pypdfium2_raw").origin)

_datas = [
    (_os.path.join(_REPO, "res", "PortableConverterMD.ico"), "res"),
    (_os.path.join(_REPO, "NOTICE"), "."),
    (_os.path.join(_PP_RAW, "pdfium.dll"), "pypdfium2_raw"),
    (_os.path.join(_PP_RAW, "version.json"), "pypdfium2_raw"),
    (_os.path.join(_SP, "version.json"), "pypdfium2"),
]

# ------------------------------------------- winrt（PEP 420 命名空间包，显式收集）
_winrt_root = _os.path.dirname(importlib.util.find_spec("winrt").origin or "")
_winrt_bins = []
if _winrt_root and _os.path.isdir(_winrt_root):
    for _p in _glob.glob(_os.path.join(_winrt_root, "*.pyd")):
        _winrt_bins.append((_p, "winrt"))
    _msvcp = _os.path.join(_winrt_root, "msvcp140.dll")
    if _os.path.exists(_msvcp):
        _winrt_bins.append((_msvcp, "winrt"))

# ---------------------------------------------------------------- excludes
_EXCLUDES = [
    "markitdown", "magika", "onnxruntime",
    "numpy", "pandas", "matplotlib", "scipy", "numba", "cv2",
    "azure", "msal", "cryptography", "requests", "urllib3", "charset_normalizer",
    "chardet", "httpx", "httpcore", "openai", "tiktoken",
    "speech_recognition", "pydub", "youtube_transcript_api", "pocketsphinx",
    "boto3", "botocore", "s3transfer",
    "sqlalchemy", "psycopg2", "fsspec", "tqdm",
    "pdfplumber", "pdfminer", "mammoth", "olefile", "pytesseract",
    "IPython", "jedi", "prompt_toolkit", "pyreadline3", "traitlets", "pygments",
    "pytest", "_pytest", "ipykernel", "notebook", "tkinter",
    # 用不到的重型可选组件：AVIF 解码器（7.5MB）、OpenSSL（本程序不联网）
    "PIL._avif", "ssl", "_ssl", "hashlib_hmac_signing",
]

_HIDDEN = [
    "pypdfium2", "pypdfium2_raw", "PIL", "PIL.Image",
    "docx", "openpyxl", "et_xmlfile", "pptx",
    "bs4", "markdownify", "lxml.etree", "lxml._elementpath",
    # Windows OCR
    "winrt", "winrt.system", "winrt.runtime", "winrt.runtime._internals",
    "winrt.windows.foundation", "winrt.windows.foundation.collections",
    "winrt.windows.globalization", "winrt.windows.graphics.imaging",
    "winrt.windows.media.ocr", "winrt.windows.security.cryptography",
    "winrt.windows.storage.streams",
]

a = Analysis(
    [_os.path.join(_REPO, "main.py")],
    pathex=[_REPO],
    binaries=_winrt_bins,
    datas=_datas,
    hiddenimports=_HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_EXCLUDES,
    noarchive=False,
)

# ------------------------------------------------- Qt 裁剪（仅 QWidgets 需要的一小撮）
_QT_KEEP_DLL = {"qt6core.dll", "qt6gui.dll", "qt6widgets.dll", "qt6svg.dll", "qt6opengl.dll"}
_QT_KEEP_PYD = {"qtcore.pyd", "qtgui.pyd", "qtwidgets.pyd", "qtsvg.pyd"}
_PLUGIN_KEEP = {
    "platforms": {"qwindows.dll", "qdirect2d.dll"},
    "styles": None,                                   # 体积很小，全部保留
    "iconengines": {"qsvgicon.dll"},
    "imageformats": {"qsvg.dll", "qico.dll"},
}
_DROP_DATAS_PREFIX = ("pyside6/qml", "pyside6/translations", "pyside6/plugins/qmltooling",
                      "pyside6/plugins/sqldrivers", "pyside6/plugins/designer",
                      "pyside6/plugins/help", "pyside6/plugins/networkinformation",
                      "pyside6/plugins/tls", "pyside6/plugins/generic",
                      "pyside6/plugins/renderers", "pyside6/plugins/printsupport",
                      "pyside6/plugins/multimedia", "pyside6/plugins/position",
                      "pyside6/plugins/texttospeech", "pyside6/plugins/virtualkeyboard",
                      "pyside6/plugins/webview")


def _keep_qt_binary(dest: str, name: str) -> bool:
    low = dest.replace("\\", "/").lower()
    lname = name.lower()
    if not low.startswith("pyside6/"):
        return True
    if lname == "opengl32sw.dll":
        return False
    if "/plugins/" in low:                                    # plugins/<kind>/<file>
        parts = low.split("/plugins/", 1)[1].split("/")
        kind = parts[0] if parts else ""
        if kind not in _PLUGIN_KEEP:
            return False
        allow = _PLUGIN_KEEP[kind]
        return True if allow is None else lname in allow
    depth = low.count("/")
    if depth == 1:                                            # PySide6/<file>
        if lname.startswith("qt6") and lname.endswith(".dll"):
            return lname in _QT_KEEP_DLL
        if lname.endswith(".pyd"):
            return lname in _QT_KEEP_PYD
    return True


def _keep_data(dest: str) -> bool:
    return not dest.replace("\\", "/").lower().startswith(_DROP_DATAS_PREFIX)


a.binaries = [b for b in a.binaries if _keep_qt_binary(b[0], _os.path.basename(b[0]))]
a.datas = [d for d in a.datas if _keep_data(d[0])]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PortableConverterMD",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_os.path.join(_REPO, "res", "PortableConverterMD.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PortableConverterMD",
)
