"""PortableConverterMD — 门面层：应用路径、日志、转换入口

保持对外的四个名字（get_app_dir / get_logger / close_file_log / convert_file），
使 ui.py、worker.py、main.py 无需感知引擎实现细节。
真正的格式实现在 engine.py，OCR 后端在 ocr.py。
"""
import logging
import os
import sys
from datetime import datetime

import engine

__all__ = [
    "get_app_dir", "get_log_dir", "get_logger", "close_file_log",
    "convert_file", "convert_to_text", "supported_ext", "ocr_backend_label",
]


def get_app_dir() -> str:
    """应用根目录：源码运行=仓库根，PyInstaller 冻结后=_MEIPASS（_internal）。"""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_log_dir() -> str:
    """日志目录。

    必须落在用户可写位置：安装版在 {autopf}\\PortableConverterMD，
    普通用户对该目录（含 _internal）没有写权限，写进那里会导致后台线程直接失败。
    """
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "PortableConverterMD", "logs")
    os.makedirs(path, exist_ok=True)
    return path


# ------------------------------------------------------------ 日志

_logger: logging.Logger | None = None
_file_handler: logging.FileHandler | None = None


def get_logger(with_file: str = "") -> logging.Logger:
    """获取日志器。传目录则同时写 conversion.log；日志失败绝不影响转换。"""
    global _logger, _file_handler

    if _logger is None:
        _logger = logging.getLogger("PortableConverterMD")
        _logger.setLevel(logging.DEBUG)
        if not _logger.handlers:
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            console.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
            _logger.addHandler(console)

    if with_file:
        close_file_log()
        try:
            os.makedirs(with_file, exist_ok=True)
            _file_handler = logging.FileHandler(
                os.path.join(with_file, "conversion.log"), encoding="utf-8")
            _file_handler.setLevel(logging.DEBUG)
            _file_handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s"))
            _logger.addHandler(_file_handler)
            _logger.info("=== PortableConverterMD 日志开始 %s ===", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            _logger.info("OCR 后端：%s", ocr_backend_label())
        except Exception as e:                      # 日志不可写也必须能继续转换
            _file_handler = None
            _logger.warning("无法写入日志文件（%s），仅输出到控制台", e)

    return _logger


def close_file_log() -> None:
    """关闭文件日志句柄（Windows 上不关闭会导致文件被占用）。"""
    global _file_handler
    if _file_handler is not None:
        try:
            _file_handler.close()
            if _logger is not None:
                _logger.removeHandler(_file_handler)
        except Exception:
            pass
        _file_handler = None


# ------------------------------------------------------------ 转换

def convert_file(file_path: str, output_dir: str) -> str:
    """转换单个文件为 Markdown，返回输出文件路径。"""
    return engine.convert_file(file_path, output_dir)


def convert_to_text(file_path: str) -> str:
    """转换但不落盘（CLI/测试用）。"""
    return engine.convert_to_text(file_path)


def supported_ext() -> tuple:
    return engine.SUPPORTED_EXT


def ocr_backend_label() -> str:
    """当前 OCR 后端描述，用于日志与状态栏。"""
    try:
        import ocr
        return ocr.backend_label()
    except Exception as e:
        return f"不可用（{e}）"
