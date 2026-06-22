"""PortableConverterMD — 文件转 Markdown 桌面工具"""
import os
from pathlib import Path

from PySide6.QtCore import QThread, Qt, QUrl, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

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


# ============================================================
# GUI 组件
# ============================================================


class DropZone(QLabel):
    """拖拽区域：支持拖入文件或点击选择。"""
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setText("📁  拖拽文件到此处（或点击选择）")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #aaa;
                border-radius: 12px;
                background: #f8f9fa;
                font-size: 14px;
                color: #666;
            }
            DropZone:hover {
                border-color: #4a90d9;
                background: #e8f0fe;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropZone {
                    border: 2px solid #4a90d9;
                    border-radius: 12px;
                    background: #d4e4fc;
                    font-size: 14px;
                    color: #333;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #aaa;
                border-radius: 12px;
                background: #f8f9fa;
                font-size: 14px;
                color: #666;
            }
            DropZone:hover {
                border-color: #4a90d9;
                background: #e8f0fe;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            self.files_dropped.emit(files)
        self.dragLeaveEvent(None)

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
        self.btn_clear.clicked.connect(self._clear_files)
        self.btn_clear.setEnabled(False)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        self.lbl_count = QLabel("0 个文件")
        btn_row.addWidget(self.lbl_count)
        layout.addLayout(btn_row)

        # --- 状态 ---
        self.lbl_status = QLabel("就绪")
        layout.addWidget(self.lbl_status)

        # --- 进度条 ---
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # --- 操作按钮 ---
        action_row = QHBoxLayout()
        self.btn_convert = QPushButton("开始转换")
        self.btn_convert.clicked.connect(self._start_conversion)
        self.btn_convert.setEnabled(False)
        self.btn_convert.setMinimumHeight(40)
        action_row.addWidget(self.btn_convert)

        self.btn_open_dir = QPushButton("打开输出目录")
        self.btn_open_dir.clicked.connect(self._open_output_dir)
        self.btn_open_dir.setEnabled(False)
        self.btn_open_dir.setMinimumHeight(40)
        action_row.addWidget(self.btn_open_dir)
        layout.addLayout(action_row)

    # ---- 文件管理 ----

    def _add_files(self, paths: list[str]):
        """添加文件到列表，去重，默认勾选。"""
        for path in paths:
            if path not in self.file_paths:
                self.file_paths.append(path)
                item = QListWidgetItem(os.path.basename(path))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
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
        success = sum(1 for r in results if r is not None)
        total = len(results)
        self.progress.setVisible(False)
        self.lbl_status.setText(f"完成：{success}/{total} 个文件转换成功")
        self.drop_zone.setEnabled(True)
        self.btn_open_dir.setEnabled(True)
        self.btn_convert.setEnabled(True)
        QMessageBox.information(
            self, "转换完成",
            f"成功转换 {success}/{total} 个文件。\n输出目录：{self.output_dir}"
        )

    def _open_output_dir(self):
        """用系统文件管理器打开输出目录。"""
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)


# ============================================================
# 入口
# ============================================================


def main():
    import sys
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
