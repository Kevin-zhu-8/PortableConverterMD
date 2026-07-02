"""PortableConverterMD — 文件转 Markdown 桌面工具"""
import os
import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from converter import convert_file, get_app_dir
from ui import GLOBAL_CSS, MainWindow


def _headless_convert(file_paths: list[str]):
    """命令行模式：直接转换文件，弹窗告知结果。"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 10))

    output_dir = os.path.join(os.path.dirname(file_paths[0]), "md_output")
    success = 0
    failed = []

    for path in file_paths:
        try:
            convert_file(path, output_dir)
            success += 1
        except Exception as e:
            failed.append((os.path.basename(path), str(e)))

    total = len(file_paths)
    if failed:
        msg = f"成功 {success}/{total}\n\n失败："
        for name, err in failed:
            msg += f"\n  {name}: {err}"
        QMessageBox.warning(None, "PortableConverterMD", msg)
    else:
        QMessageBox.information(
            None, "PortableConverterMD",
            f"全部完成！{success} 个文件已转换。\n\n输出目录：{output_dir}"
        )
        os.startfile(output_dir)


def _has_args() -> bool:
    """检查是否通过命令行传入文件路径。"""
    if len(sys.argv) <= 1:
        return False
    # 过滤掉可能的 PyInstaller 内部参数
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    return len(args) > 0


def _get_file_args() -> list[str]:
    """获取命令行传入的有效文件路径。"""
    return [a for a in sys.argv[1:] if not a.startswith("-") and os.path.exists(a)]


def main():
    # 命令行模式：直接转换
    if _has_args():
        file_paths = _get_file_args()
        if file_paths:
            _headless_convert(file_paths)
            return

    # GUI 模式
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(GLOBAL_CSS)

    icon_path = os.path.join(get_app_dir(), "res", "PortableConverterMD.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

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
