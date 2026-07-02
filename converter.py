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
        return os.path.dirname(sys.executable)
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


def convert_file(file_path: str, output_dir: str) -> str:
    """转换单个文件为 Markdown，返回输出文件路径。"""
    file_path = str(file_path)
    output_dir = str(output_dir)
    log = get_logger()

    os.makedirs(output_dir, exist_ok=True)

    input_name = Path(file_path).stem
    output_path = os.path.join(output_dir, f"{input_name}.md")

    log.info(f"开始转换: {os.path.basename(file_path)}")

    converter = _get_converter()
    result = converter.convert(file_path)

    # 检测空结果（常见于扫描版 PDF）
    text = result.text_content.strip()
    ext = Path(file_path).suffix.lower()
    if not text and ext == ".pdf":
        raise RuntimeError(
            "PDF 转换结果为空，可能是扫描版/图片型 PDF（不含文字层）。"
            "请使用带 OCR 的工具先识别文字，或将 PDF 打印为可搜索 PDF 后再试。"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.text_content)

    log.info(f"转换成功: {os.path.basename(file_path)} → {os.path.basename(output_path)}")
    return output_path
