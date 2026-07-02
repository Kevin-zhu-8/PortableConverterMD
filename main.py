"""PortableConverterMD — 文件转 Markdown 桌面工具"""
import os
import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from converter import get_app_dir
from ui import GLOBAL_CSS, MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(GLOBAL_CSS)

    # 应用图标
    icon_path = os.path.join(get_app_dir(), "PortableConverterMD.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Windows 任务栏
    if sys.platform == "win32":
        try:
            from PySide6.QtWin import setCurrentProcessExplicitAppUserModelID
            setCurrentProcessExplicitAppUserModelID("PortableConverterMD")
        except ImportError:
            pass

    app.setFont(QFont("Microsoft YaHei", 10))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
