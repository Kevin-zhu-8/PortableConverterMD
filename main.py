"""PortableConverterMD — 文件转 Markdown 桌面工具"""
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

import theme
import engine
import settings
from converter import convert_file, get_app_dir
from ui import MainWindow


def _create_app() -> QApplication:
    """创建 QApplication 并统一外观（DPI 取整策略必须在创建前设置）。"""
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    theme.apply(app)
    app.setFont(theme.app_font())

    icon_path = os.path.join(get_app_dir(), "res", "PortableConverterMD.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    return app


def _format_ext_list(limit: int = 24) -> str:
    exts = [e.lstrip(".") for e in engine.SUPPORTED_EXT]
    text = "、".join(exts[:limit])
    return text + ("…" if len(exts) > limit else "")


def split_supported(file_paths: list[str]) -> tuple[list[str], list[str]]:
    """按扩展名把路径分成 (支持的, 不支持的)——右键/命令行共用的类型判定。"""
    supported, unsupported = [], []
    for path in file_paths:
        (supported if engine.supports(path) else unsupported).append(path)
    return supported, unsupported


def _headless_convert(file_paths: list[str]):
    """命令行/右键模式：直接转换，弹窗告知结果。

    输出目录按用户设置（与源文件同目录 / 源文件旁 output 文件夹 / 自定义目录）。
    不支持的文件类型会被跳过并如实告知，而不是报一堆转换异常。
    """
    _create_app()

    supported, unsupported = split_supported(file_paths)

    if not supported:
        names = "\n  ".join(os.path.basename(p) for p in unsupported[:8])
        more = f"\n  …等 {len(unsupported)} 个" if len(unsupported) > 8 else ""
        QMessageBox.warning(
            None, "PortableConverterMD",
            f"以下文件类型暂不支持转换：\n\n  {names}{more}\n\n"
            f"支持的类型：{_format_ext_list()}")
        return

    success = 0
    failed = []
    output_dirs = []

    for path in supported:
        out_dir = settings.output_dir_for(path)
        try:
            convert_file(path, out_dir)
            success += 1
            if out_dir not in output_dirs:
                output_dirs.append(out_dir)
        except Exception as e:
            failed.append((os.path.basename(path), str(e)))

    total = len(supported)
    skipped = f"\n已跳过 {len(unsupported)} 个不支持的文件。" if unsupported else ""

    if failed:
        msg = f"成功 {success}/{total}\n\n失败："
        for name, err in failed:
            msg += f"\n  {name}: {err}"
        if unsupported:
            msg += skipped
        QMessageBox.warning(None, "PortableConverterMD", msg)
        return

    where = output_dirs[0] if len(output_dirs) == 1 else f"{len(output_dirs)} 个目录"
    QMessageBox.information(
        None, "PortableConverterMD",
        f"全部完成！{success} 个文件已转换。\n\n输出位置：{where}{skipped}"
    )
    if output_dirs:
        os.startfile(output_dirs[0])


def _has_args() -> bool:
    """检查是否通过命令行传入文件路径。"""
    if len(sys.argv) <= 1:
        return False
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    return len(args) > 0


def _get_file_args() -> list[str]:
    """获取命令行传入的有效文件路径。"""
    return [a for a in sys.argv[1:] if not a.startswith("-") and os.path.exists(a)]


def main():
    if _has_args():
        file_paths = _get_file_args()
        if file_paths:
            _headless_convert(file_paths)
            return

    # 任务栏图标必须在 QApplication 创建前设置
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PortableConverterMD")

    app = _create_app()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
