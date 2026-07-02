"""PortableConverterMD — 文件转 Markdown 桌面工具"""
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Qt, QUrl, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

# ============================================================
# 工具函数
# ============================================================


def _get_app_dir() -> str:
    """获取应用根目录（源码运行或 PyInstaller 打包均正确）。"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# 日志配置
_logger = None
_file_handler = None


def _get_logger(with_file: str = "") -> logging.Logger:
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


def _close_file_log():
    """关闭文件日志 handler（释放文件句柄）。"""
    global _logger, _file_handler
    if _file_handler:
        _file_handler.close()
        if _logger:
            _logger.removeHandler(_file_handler)
        _file_handler = None

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
    log = _get_logger()

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 生成输出文件名：同名 .md
    input_name = Path(file_path).stem
    output_path = os.path.join(output_dir, f"{input_name}.md")

    log.info(f"开始转换: {os.path.basename(file_path)}")

    # 调用 MarkItDown 转换
    converter = _get_converter()
    result = converter.convert(file_path)

    # 写入结果
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.text_content)

    log.info(f"转换成功: {os.path.basename(file_path)} → {os.path.basename(output_path)}")
    return output_path


# ============================================================
# 后台转换线程
# ============================================================


class ConvertWorker(QThread):
    """后台线程执行批量转换，不阻塞 GUI。"""
    progress_updated = Signal(int, int)       # current, total
    conversion_done = Signal(list)            # list[dict]: {file, output, error}

    def __init__(self, file_paths: list, output_dir: str):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir

    def run(self):
        # 日志写入应用根目录的 logs/ 文件夹
        log_dir = os.path.join(_get_app_dir(), "logs")
        log = _get_logger(log_dir)
        results = []
        total = len(self.file_paths)
        try:
            for i, file_path in enumerate(self.file_paths):
                try:
                    out_path = convert_file(file_path, self.output_dir)
                    results.append({"file": file_path, "output": out_path, "error": None})
                except Exception as e:
                    err_msg = f"{type(e).__name__}: {e}"
                    log.error(f"转换失败 [{os.path.basename(file_path)}]: {err_msg}")
                    log.debug(traceback.format_exc())
                    results.append({"file": file_path, "output": None, "error": err_msg})
                self.progress_updated.emit(i + 1, total)
        finally:
            _close_file_log()
        self.conversion_done.emit(results)


# ============================================================
# GUI 组件
# ============================================================


class DropZone(QWidget):
    """拖拽区域：支持拖入文件或点击选择。"""
    files_dropped = Signal(list)

    STYLE_NORMAL = """
        QWidget#dropZone {
            border: 2px dashed #c0c4cc;
            border-radius: 16px;
            background: qlineargradient(x1:0 y1:0, x2:0 y2:1,
                stop:0 #fafbfc, stop:1 #f0f2f5);
        }
        QLabel { border: none; background: transparent; }
    """
    STYLE_DRAG = """
        QWidget#dropZone {
            border: 2px solid #4a90d9;
            border-radius: 16px;
            background: qlineargradient(x1:0 y1:0, x2:0 y2:1,
                stop:0 #e8f0fe, stop:1 #d4e4fc);
        }
        QLabel { border: none; background: transparent; }
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumHeight(130)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)

        self.icon_label = QLabel("⬇")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 30px; color: #5b9bd5;")

        self.text_label = QLabel("拖拽文件到此处")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setObjectName("dropText")
        self.text_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #303133;")

        self.hint_label = QLabel("或点击选择文件")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setObjectName("dropHint")
        self.hint_label.setStyleSheet("font-size: 12px; color: #909399;")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(self.hint_label)
        self.setStyleSheet(self.STYLE_NORMAL)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.STYLE_DRAG)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.STYLE_NORMAL)

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            self.files_dropped.emit(files)
        self.setStyleSheet(self.STYLE_NORMAL)

    def mousePressEvent(self, event):
        """点击打开文件选择对话框。"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要转换的文件", "",
            "所有文件 (*.*)"
        )
        if files:
            self.files_dropped.emit(files)


class MainWindow(QMainWindow):
    """PortableConverterMD 主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PortableConverterMD")
        self.resize(620, 480)

        # 窗口图标
        icon_path = os.path.join(_get_app_dir(), "o.jpg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.file_paths: list[str] = []
        self.output_dir: str = ""
        self.worker: ConvertWorker | None = None

        # --- 中央组件 ---
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # --- 拖拽区 ---
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._add_files)
        layout.addWidget(self.drop_zone)

        # --- 文件列表 ---
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        layout.addWidget(self.file_list)

        # --- 文件列表操作栏 ---
        btn_row = QHBoxLayout()
        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.setObjectName("btnClear")
        self.btn_clear.clicked.connect(self._clear_files)
        self.btn_clear.setEnabled(False)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        self.lbl_count = QLabel("0 个文件")
        self.lbl_count.setObjectName("lblCount")
        btn_row.addWidget(self.lbl_count)
        layout.addLayout(btn_row)

        # --- 状态 ---
        self.lbl_status = QLabel("就绪")
        self.lbl_status.setObjectName("lblStatus")
        layout.addWidget(self.lbl_status)

        # --- 进度条 ---
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        # --- 操作按钮 ---
        action_row = QHBoxLayout()
        self.btn_convert = QPushButton("开始转换")
        self.btn_convert.setObjectName("btnConvert")
        self.btn_convert.clicked.connect(self._start_conversion)
        self.btn_convert.setEnabled(False)
        self.btn_convert.setMinimumHeight(42)
        action_row.addWidget(self.btn_convert)

        self.btn_open_dir = QPushButton("打开输出目录")
        self.btn_open_dir.setObjectName("btnOpenDir")
        self.btn_open_dir.clicked.connect(self._open_output_dir)
        self.btn_open_dir.setEnabled(False)
        self.btn_open_dir.setMinimumHeight(42)
        action_row.addWidget(self.btn_open_dir)
        layout.addLayout(action_row)

    # ---- 文件管理 ----

    def _add_files(self, paths: list[str]):
        """添加文件到列表，去重，默认勾选，显示文件大小。"""
        for path in paths:
            if path not in self.file_paths:
                self.file_paths.append(path)
                # 文件名 + 大小
                fname = os.path.basename(path)
                size = os.path.getsize(path)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / 1024 / 1024:.1f} MB"
                item = QListWidgetItem(f"{fname}    {size_str}")
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                item.setToolTip(path)
                self.file_list.addItem(item)
        self._update_ui()

    def _clear_files(self):
        """清空文件列表。"""
        self.file_list.clear()
        self.file_paths.clear()
        self._update_ui()

    def _update_ui(self):
        count = self.file_list.count()
        self.lbl_count.setText(f"{count} 个文件")
        has_files = count > 0
        self.btn_clear.setEnabled(has_files)
        self.btn_convert.setEnabled(has_files)

    # ---- 转换 ----

    def _get_checked_paths(self) -> list[str]:
        """获取勾选的文件路径列表。"""
        checked = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.Checked:
                checked.append(self.file_paths[i])
        return checked

    def _start_conversion(self):
        """开始批量转换。"""
        checked = self._get_checked_paths()
        if not checked:
            QMessageBox.information(self, "提示", "没有勾选任何文件。")
            return

        # 取第一个文件的目录作为输出根目录
        self.output_dir = os.path.join(
            os.path.dirname(checked[0]), "md_output"
        )

        # 禁用按钮，显示进度
        self.btn_convert.setEnabled(False)
        self.btn_open_dir.setEnabled(False)
        self.drop_zone.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(checked))

        # 启动后台线程
        self.worker = ConvertWorker(checked, self.output_dir)
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.conversion_done.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, current: int, total: int):
        self.progress.setValue(current)
        self.lbl_status.setText(f"已转换 {current}/{total}")

    def _on_done(self, results: list):
        success = sum(1 for r in results if r["output"] is not None)
        failed = [r for r in results if r["output"] is None]
        total = len(results)
        self.progress.setVisible(False)
        self.lbl_status.setText(f"完成：{success}/{total} 个文件转换成功")
        self.drop_zone.setEnabled(True)
        self.btn_open_dir.setEnabled(True)
        self.btn_convert.setEnabled(True)

        # 组装完成消息
        msg = f"成功转换 {success}/{total} 个文件。\n输出目录：{self.output_dir}"
        if failed:
            msg += "\n\n失败文件："
            for r in failed:
                fname = os.path.basename(r["file"])
                msg += f"\n  • {fname}: {r['error']}"
            log_path = os.path.join(_get_app_dir(), "logs", "conversion.log")
            msg += f"\n\n详细日志见：{log_path}"

        box = QMessageBox(self)
        box.setWindowTitle("转换完成")
        box.setText(msg)
        box.setIcon(QMessageBox.Warning if failed else QMessageBox.Information)
        if failed:
            box.setStandardButtons(QMessageBox.Ok)
            box.setDetailedText(
                "完整日志文件：" + os.path.join(_get_app_dir(), "logs", "conversion.log")
            )
        box.exec()

    def _open_output_dir(self):
        """用系统文件管理器打开输出目录。"""
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)


# ============================================================
# 入口
# ============================================================


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # ---- 全局样式表 ----
    app.setStyleSheet("""
        QMainWindow {
            background: #f5f6f8;
        }
        QListWidget {
            border: 1px solid #e0e3e8;
            border-radius: 8px;
            background: white;
            padding: 4px;
            font-size: 13px;
            outline: none;
        }
        QListWidget::item {
            padding: 8px 12px;
            border-radius: 4px;
            margin: 1px 0;
        }
        QListWidget::item:selected {
            background: #f0f5ff;
            color: #303133;
        }
        QListWidget::item:hover {
            background: #f5f7fa;
        }
        QListWidget::indicator {
            width: 16px;
            height: 16px;
        }
        QPushButton {
            border-radius: 8px;
            padding: 8px 20px;
            font-size: 13px;
            font-weight: bold;
            border: none;
        }
        QPushButton#btnConvert {
            background: #4a90d9;
            color: white;
        }
        QPushButton#btnConvert:hover {
            background: #357abd;
        }
        QPushButton#btnConvert:pressed {
            background: #2a6cb8;
        }
        QPushButton#btnConvert:disabled {
            background: #c8d6e5;
            color: #a0a8b4;
        }
        QPushButton#btnOpenDir {
            background: white;
            color: #4a90d9;
            border: 1px solid #4a90d9;
        }
        QPushButton#btnOpenDir:hover {
            background: #e8f0fe;
        }
        QPushButton#btnOpenDir:disabled {
            background: white;
            color: #c0c4cc;
            border-color: #c0c4cc;
        }
        QPushButton#btnClear {
            background: transparent;
            color: #909399;
            font-weight: normal;
            padding: 4px 12px;
        }
        QPushButton#btnClear:hover {
            color: #e74c3c;
            background: #fef0f0;
        }
        QProgressBar {
            border: none;
            border-radius: 6px;
            background: #e8ecf0;
            height: 8px;
            text-align: center;
            font-size: 11px;
            color: #606266;
        }
        QProgressBar::chunk {
            border-radius: 6px;
            background: qlineargradient(x1:0 y1:0, x2:1 y2:0,
                stop:0 #4a90d9, stop:1 #5ba0e8);
        }
        QLabel#lblStatus {
            color: #606266;
            font-size: 12px;
        }
        QLabel#lblCount {
            color: #909399;
            font-size: 12px;
        }
    """)

    # 应用图标（窗口 + 任务栏）
    icon_path = os.path.join(_get_app_dir(), "o.jpg")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        app.setWindowIcon(icon)

    # Windows 任务栏标识
    if sys.platform == "win32":
        try:
            from PySide6.QtWin import setCurrentProcessExplicitAppUserModelID
            setCurrentProcessExplicitAppUserModelID("PortableConverterMD")
        except ImportError:
            pass

    # 全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
