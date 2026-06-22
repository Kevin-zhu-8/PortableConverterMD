"""PortableConverterMD — 文件转 Markdown 桌面工具"""
import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

# 延迟导入，GUI 启动时不加载 markitdown
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

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 生成输出文件名：同名 .md
    input_name = Path(file_path).stem
    output_path = os.path.join(output_dir, f"{input_name}.md")

    # 调用 MarkItDown 转换
    converter = _get_converter()
    result = converter.convert(file_path)

    # 写入结果
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.text_content)

    return output_path


# ============================================================
# 后台转换线程
# ============================================================


class ConvertWorker(QThread):
    """后台线程执行批量转换，不阻塞 GUI。"""
    progress_updated = Signal(int, int)  # current, total
    conversion_done = Signal(list)       # output_paths

    def __init__(self, file_paths: list, output_dir: str):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir

    def run(self):
        results = []
        total = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            try:
                out_path = convert_file(file_path, self.output_dir)
                results.append(out_path)
            except Exception as e:
                print(f"[PortableConverterMD] 转换失败 [{file_path}]: {e}")
                results.append(None)
            self.progress_updated.emit(i + 1, total)
        self.conversion_done.emit(results)
