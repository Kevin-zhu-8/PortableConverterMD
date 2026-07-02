"""PortableConverterMD — 后台转换线程"""
import os
import traceback

from PySide6.QtCore import QThread, Signal

from converter import convert_file, get_app_dir, get_logger, close_file_log


class ConvertWorker(QThread):
    """后台线程执行批量转换，不阻塞 GUI。"""
    progress_updated = Signal(int, int)       # current, total
    file_started = Signal(str)                # 正在处理的文件名
    file_finished = Signal(str, bool, str)    # 文件名, 成功?, 错误信息
    conversion_done = Signal(list)            # list[dict]: {file, output, error}

    def __init__(self, file_paths: list, output_dir: str):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir

    def run(self):
        log_dir = os.path.join(get_app_dir(), "logs")
        log = get_logger(log_dir)
        results = []
        total = len(self.file_paths)
        try:
            for i, file_path in enumerate(self.file_paths):
                fname = os.path.basename(file_path)
                self.file_started.emit(fname)
                try:
                    out_path = convert_file(file_path, self.output_dir)
                    results.append({"file": file_path, "output": out_path, "error": None})
                    self.file_finished.emit(fname, True, "")
                except Exception as e:
                    err_msg = f"{type(e).__name__}: {e}"
                    log.error(f"转换失败 [{fname}]: {err_msg}")
                    log.debug(traceback.format_exc())
                    results.append({"file": file_path, "output": None, "error": err_msg})
                    self.file_finished.emit(fname, False, err_msg)
                self.progress_updated.emit(i + 1, total)
        finally:
            close_file_log()
        self.conversion_done.emit(results)
