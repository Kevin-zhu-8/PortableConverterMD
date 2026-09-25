"""PortableConverterMD — 后台转换线程"""
import os
import traceback

from PySide6.QtCore import QThread, Signal

import settings
from converter import close_file_log, convert_file, get_log_dir, get_logger


class ConvertWorker(QThread):
    """后台线程执行批量转换，不阻塞 GUI。

    信号带列表行号（row），UI 按行回写状态——旧实现按文件名匹配，
    同名文件会互相串状态。
    """
    progress_updated = Signal(int, int)       # current, total
    file_started = Signal(int, str)           # row, 文件名
    file_finished = Signal(int, bool, str)    # row, 成功?, 错误信息
    conversion_done = Signal(list)            # list[dict]: {file, output, error}

    def __init__(self, items: list, output_dir: str = ""):
        """items: [(列表行号, 文件路径), ...]

        output_dir 为空时按用户设置计算每个文件的输出目录
        （与源文件同目录 / 源文件旁 output 文件夹）。
        """
        super().__init__()
        self.items = list(items)
        self.output_dir = output_dir

    def run(self):
        results = []
        total = len(self.items)

        # 日志目录不可写也不能让线程死掉（安装目录对普通用户只读）
        try:
            log = get_logger(get_log_dir() if settings.logging_enabled() else "")
        except Exception:
            log = get_logger()

        try:
            for i, (row, file_path) in enumerate(self.items):
                fname = os.path.basename(file_path)
                self.file_started.emit(row, fname)
                try:
                    out_dir = self.output_dir or settings.output_dir_for(file_path)
                    out_path = convert_file(file_path, out_dir)
                    results.append({"file": file_path, "output": out_path, "error": None})
                    self.file_finished.emit(row, True, "")
                    log.info("转换成功: %s → %s", fname, out_path)
                except Exception as e:
                    err_msg = f"{type(e).__name__}: {e}"
                    log.error("转换失败 [%s]: %s", fname, err_msg)
                    log.debug(traceback.format_exc())
                    results.append({"file": file_path, "output": None, "error": err_msg})
                    self.file_finished.emit(row, False, err_msg)
                self.progress_updated.emit(i + 1, total)
        finally:
            close_file_log()
            # 无论发生什么都要通知 UI 复位，否则按钮会永久禁用
            self.conversion_done.emit(results)
