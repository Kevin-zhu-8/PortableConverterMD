"""用户偏好设置

统一使用 QSettings（HKCU\\Software\\PortableConverterMD\\PortableConverterMD），
界面、命令行/右键转换共用同一份设置。

设置项：
- output/mode        输出位置：与源文件同目录 / 源文件旁 output 文件夹
- output/custom_dir  自定义输出目录（非空时优先于 mode）
- startup/autostart  开机启动（实际状态以注册表 Run 项为准）
- startup/keep_in_background  关闭窗口后继续在后台（托盘）运行
- log/enabled        是否记录转换日志
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QSettings

ORG = "PortableConverterMD"
APP = "PortableConverterMD"

MODE_SAME_DIR = "same_dir"
MODE_SUBFOLDER = "subfolder"
SUBFOLDER_NAME = "output"

_DEFAULTS = {
    "output/mode": MODE_SUBFOLDER,
    "output/custom_dir": "",
    "startup/keep_in_background": False,
    "log/enabled": True,
}

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE = "PortableConverterMD"


# ---------------------------------------------------------------- 基础读写

def store() -> QSettings:
    return QSettings(ORG, APP)


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _get(key: str, default=None):
    return store().value(key, _DEFAULTS.get(key, default))


def _set(key: str, value) -> None:
    s = store()
    s.setValue(key, value)
    s.sync()


# ---------------------------------------------------------------- 输出位置

def output_mode() -> str:
    mode = str(_get("output/mode") or MODE_SUBFOLDER)
    return mode if mode in (MODE_SAME_DIR, MODE_SUBFOLDER) else MODE_SUBFOLDER


def set_output_mode(mode: str) -> None:
    _set("output/mode", mode if mode in (MODE_SAME_DIR, MODE_SUBFOLDER) else MODE_SUBFOLDER)


def custom_dir() -> str:
    return str(_get("output/custom_dir") or "")


def set_custom_dir(path: str) -> None:
    _set("output/custom_dir", path or "")


def mode_label(mode: str | None = None) -> str:
    mode = mode or output_mode()
    if mode == MODE_SAME_DIR:
        return "与源文件同目录"
    return f"源文件旁的 {SUBFOLDER_NAME} 文件夹"


def output_dir_for(file_path: str, mode: str | None = None,
                   custom: str | None = None) -> str:
    """按设置算出某个源文件的输出目录。"""
    custom = custom_dir() if custom is None else custom
    if custom:
        return custom
    folder = os.path.dirname(os.path.abspath(str(file_path)))
    if (mode or output_mode()) == MODE_SAME_DIR:
        return folder
    return os.path.join(folder, SUBFOLDER_NAME)


# ---------------------------------------------------------------- 后台常驻

def keep_in_background() -> bool:
    return _as_bool(_get("startup/keep_in_background"))


def set_keep_in_background(enabled: bool) -> None:
    _set("startup/keep_in_background", bool(enabled))


# ---------------------------------------------------------------- 日志

def logging_enabled() -> bool:
    return _as_bool(_get("log/enabled"))


def set_logging_enabled(enabled: bool) -> None:
    _set("log/enabled", bool(enabled))


# ---------------------------------------------------------------- 开机启动

def autostart_command() -> str:
    """写入 Run 项的命令行。"""
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}"'
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    launcher = pythonw if pythonw.exists() else exe
    main_py = Path(__file__).resolve().parent / "main.py"
    return f'"{launcher}" "{main_py}"'


def autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, _RUN_VALUE)
        return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_autostart(enabled: bool) -> bool:
    """写入/删除开机启动项，返回是否成功。"""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, _RUN_VALUE, 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, _RUN_VALUE)
                except FileNotFoundError:
                    pass
        return autostart_enabled() == bool(enabled)
    except OSError:
        return False
