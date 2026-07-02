"""PortableConverterMD — GUI 组件"""
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from converter import get_app_dir
from worker import ConvertWorker

# ------------------------------------------------------------
# CSS
# ------------------------------------------------------------

GLOBAL_CSS = """
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
"""

# ------------------------------------------------------------
# DropZone
# ------------------------------------------------------------


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

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        svg_path = os.path.join(get_app_dir(), "res", "icon_download.svg")
        icon = QIcon(svg_path)
        self.icon_label.setPixmap(icon.pixmap(52, 52))
        self.icon_label.setStyleSheet("border: none; background: transparent;")

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
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要转换的文件", "", "所有文件 (*.*)"
        )
        if files:
            self.files_dropped.emit(files)


# ------------------------------------------------------------
# 完成弹窗
# ------------------------------------------------------------


class _CompletionDialog(QDialog):
    """美观的转换完成弹窗。"""

    def __init__(self, output_dir: str, success: int, failed: list, total: int, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.setWindowTitle("转换完成")
        self.setMinimumWidth(420)
        self.setMaximumWidth(520)
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLabel#headerIcon {
                font-size: 40px;
            }
            QLabel#headerTitle {
                font-size: 18px;
                font-weight: bold;
                color: #303133;
            }
            QLabel#headerSub {
                font-size: 13px;
                color: #909399;
            }
            QLabel#failTitle {
                font-size: 13px;
                font-weight: bold;
                color: #e74c3c;
            }
            QLabel#failItem {
                font-size: 12px;
                color: #606266;
                padding: 4px 8px;
            }
            QLabel#outputPath {
                font-size: 12px;
                color: #909399;
                padding: 8px;
                background: #f5f6f8;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 20)

        # --- 头部 ---
        has_failure = len(failed) > 0
        icon_text = "✓" if not has_failure else "!"
        icon_color = "#52c41a" if not has_failure else "#faad14"

        header_icon = QLabel(icon_text)
        header_icon.setObjectName("headerIcon")
        header_icon.setAlignment(Qt.AlignCenter)
        header_icon.setStyleSheet(f"font-size: 44px; color: {icon_color}; font-weight: bold;")
        layout.addWidget(header_icon)

        header_title = QLabel("全部完成" if not has_failure else "部分文件失败")
        header_title.setObjectName("headerTitle")
        header_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_title)

        header_sub = QLabel(f"{success}/{total} 个文件转换成功")
        header_sub.setObjectName("headerSub")
        header_sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_sub)

        # --- 分隔线 ---
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background: #ebeef5; max-height: 1px;")
        layout.addWidget(line)

        # --- 失败详情 ---
        if has_failure:
            fail_title = QLabel(f"失败详情（{len(failed)} 个）")
            fail_title.setObjectName("failTitle")
            layout.addWidget(fail_title)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(140)
            scroll.setStyleSheet("QScrollArea { border: 1px solid #ebeef5; border-radius: 6px; }")
            fail_widget = QWidget()
            fail_layout = QVBoxLayout(fail_widget)
            fail_layout.setSpacing(2)
            fail_layout.setContentsMargins(8, 8, 8, 8)
            for r in failed:
                fname = os.path.basename(r["file"])
                lbl = QLabel(f"✗ {fname}")
                lbl.setObjectName("failItem")
                lbl.setToolTip(r["error"])
                fail_layout.addWidget(lbl)
            fail_layout.addStretch()
            scroll.setWidget(fail_widget)
            layout.addWidget(scroll)
        else:
            # 全部成功时不占多余空间
            spacer = QWidget()
            spacer.setFixedHeight(4)
            layout.addWidget(spacer)

        # --- 输出路径 ---
        out_lbl = QLabel(f"输出目录：{output_dir}")
        out_lbl.setObjectName("outputPath")
        out_lbl.setWordWrap(True)
        layout.addWidget(out_lbl)

        # --- 按钮 ---
        btn_box = QDialogButtonBox()
        btn_open = QPushButton("打开输出目录")
        btn_open.setObjectName("btnConvert")
        btn_open.setMinimumHeight(36)
        btn_open.clicked.connect(self._open_and_close)
        btn_log = QPushButton("查看日志")
        btn_log.setObjectName("btnClear")
        btn_log.setMinimumHeight(36)
        btn_log.clicked.connect(self._open_log)
        btn_close = QPushButton("关闭")
        btn_close.setObjectName("btnOpenDir")
        btn_close.setMinimumHeight(36)
        btn_close.clicked.connect(self.accept)
        btn_box.addButton(btn_open, QDialogButtonBox.ActionRole)
        btn_box.addButton(btn_log, QDialogButtonBox.ActionRole)
        btn_box.addButton(btn_close, QDialogButtonBox.RejectRole)
        layout.addWidget(btn_box)

    def _open_log(self):
        from converter import is_log_enabled
        if not is_log_enabled():
            return
        log_path = os.path.join(get_app_dir(), "logs", "conversion.log")
        if os.path.exists(log_path):
            os.startfile(log_path)

    def _open_and_close(self):
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)
        self.accept()


# ------------------------------------------------------------
# MainWindow
# ------------------------------------------------------------


class MainWindow(QMainWindow):
    """PortableConverterMD 主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PortableConverterMD")
        self.resize(620, 480)

        icon_path = os.path.join(get_app_dir(), "res/PortableConverterMD.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.file_paths: list[str] = []
        self.file_items: dict[str, QListWidgetItem] = {}  # path → item
        self.output_dir: str = ""
        self.custom_output_dir: str = ""
        self.worker: ConvertWorker | None = None

        # 中央组件
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # 拖拽区
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._add_files)
        layout.addWidget(self.drop_zone)

        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        layout.addWidget(self.file_list)

        # 操作栏
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

        # 状态
        self.lbl_status = QLabel("就绪")
        self.lbl_status.setObjectName("lblStatus")
        layout.addWidget(self.lbl_status)

        # 输出目录选择
        out_row = QHBoxLayout()
        self.lbl_output = QLabel("输出目录：默认（源文件旁 md_output）")
        self.lbl_output.setObjectName("lblOutput")
        self.lbl_output.setStyleSheet("color: #909399; font-size: 12px;")
        out_row.addWidget(self.lbl_output)
        out_row.addStretch()
        self.btn_choose_dir = QPushButton("更改目录")
        self.btn_choose_dir.setObjectName("btnChooseDir")
        self.btn_choose_dir.clicked.connect(self._choose_output_dir)
        self.btn_choose_dir.setStyleSheet("""
            QPushButton#btnChooseDir {
                background: transparent;
                color: #4a90d9;
                font-weight: normal;
                font-size: 12px;
                padding: 2px 10px;
                border: 1px solid #d0d5dd;
                border-radius: 4px;
            }
            QPushButton#btnChooseDir:hover {
                background: #e8f0fe;
                border-color: #4a90d9;
            }
        """)
        out_row.addWidget(self.btn_choose_dir)
        layout.addLayout(out_row)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        # 操作按钮
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

        self.btn_log = QPushButton("查看日志")
        self.btn_log.setObjectName("btnClear")
        self.btn_log.clicked.connect(self._open_log)
        self.btn_log.setMinimumHeight(42)
        action_row.addWidget(self.btn_log)
        layout.addLayout(action_row)

    # ---- 文件管理 ----

    def _add_files(self, paths: list[str]):
        for path in paths:
            if path not in self.file_paths:
                self.file_paths.append(path)
                fname = os.path.basename(path)
                size = os.path.getsize(path)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / 1024 / 1024:.1f} MB"
                item = QListWidgetItem(f"  {fname}    {size_str}")
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                item.setToolTip(path)
                self.file_list.addItem(item)
                self.file_items[path] = item
        self._update_ui()

    def _clear_files(self):
        self.file_list.clear()
        self.file_paths.clear()
        self.file_items.clear()
        self._update_ui()

    def _update_item_status(self, path: str, status: str):
        """更新文件列表项的状态图标。"""
        item = self.file_items.get(path)
        if not item:
            return
        fname = os.path.basename(path)
        size = os.path.getsize(path)
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / 1024 / 1024:.1f} MB"
        item.setText(f"{status} {fname}    {size_str}")

    def _choose_output_dir(self):
        """弹出文件夹选择对话框，设置自定义输出目录。"""
        chosen = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if chosen:
            self.custom_output_dir = chosen
            self.lbl_output.setText(f"输出目录：{chosen}")
            self.lbl_output.setStyleSheet("color: #303133; font-size: 12px;")

    def _update_ui(self):
        count = self.file_list.count()
        self.lbl_count.setText(f"{count} 个文件")
        has_files = count > 0
        self.btn_clear.setEnabled(has_files)
        self.btn_convert.setEnabled(has_files)

    # ---- 转换 ----

    def _get_checked_paths(self) -> list[str]:
        checked = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.Checked:
                checked.append(self.file_paths[i])
        return checked

    def _start_conversion(self):
        checked = self._get_checked_paths()
        if not checked:
            QMessageBox.information(self, "提示", "没有勾选任何文件。")
            return

        # 使用自定义目录，否则默认 md_output
        if self.custom_output_dir:
            self.output_dir = self.custom_output_dir
        else:
            self.output_dir = os.path.join(os.path.dirname(checked[0]), "md_output")

        self.btn_convert.setEnabled(False)
        self.btn_open_dir.setEnabled(False)
        self.drop_zone.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(checked))

        self.worker = ConvertWorker(checked, self.output_dir)
        self.worker.file_started.connect(self._on_file_started)
        self.worker.file_finished.connect(self._on_file_finished)
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.conversion_done.connect(self._on_done)
        self.worker.start()

    def _on_file_started(self, fname: str):
        """文件开始转换时高亮列表项。"""
        for path, item in self.file_items.items():
            if os.path.basename(path) == fname:
                item.setText(f"⟳ {fname}    转换中…")
                item.setForeground(QColor("#4a90d9"))
                self.file_list.scrollToItem(item)
        self.lbl_status.setText(f"正在处理：{fname}")

    def _on_file_finished(self, fname: str, success: bool, error: str):
        """单个文件完成时标记状态。"""
        for path, item in self.file_items.items():
            if os.path.basename(path) == fname:
                if success:
                    item.setText(f"✓ {fname}")
                    item.setForeground(QColor("#52c41a"))
                else:
                    item.setText(f"✗ {fname}")
                    item.setForeground(QColor("#e74c3c"))
                    item.setToolTip(error)

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

        dlg = _CompletionDialog(self.output_dir, success, failed, total, self)
        dlg.exec()

    def _open_output_dir(self):
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)

    def _open_log(self):
        """用系统默认编辑器打开日志文件。"""
        from converter import is_log_enabled
        if not is_log_enabled():
            QMessageBox.information(self, "提示",
                "日志功能已关闭。\n编辑 settings.json，将 enable_log 设为 true 即可开启。")
            return
        log_path = os.path.join(get_app_dir(), "logs", "conversion.log")
        if os.path.exists(log_path):
            os.startfile(log_path)
        else:
            QMessageBox.information(self, "提示", "暂无日志文件，完成一次转换后生成。")
