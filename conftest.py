"""pytest 全局夹具

必须在任何其他原生库（pypdfium2 / Pillow / winrt）之前加载 Qt：
实测「先 winrt 后 QtWidgets」会在导入阶段触发 access violation，
因此这里用 conftest 保证导入顺序，并统一使用 offscreen 平台。
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication  # noqa: F401  仅用于提前加载 Qt
except ImportError:  # 未安装 GUI 依赖时忽略（其余测试仍可运行）
    pass

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _isolated_qsettings(tmp_path_factory):
    """把 QSettings 重定向到临时 INI，测试不读写用户真实设置。"""
    try:
        from PySide6.QtCore import QSettings
    except ImportError:
        yield
        return
    path = tmp_path_factory.mktemp("qsettings")
    original_format = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(path))
    yield
    QSettings.setDefaultFormat(original_format)
