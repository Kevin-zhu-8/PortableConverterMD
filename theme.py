"""设计令牌与主题：颜色、字号、圆角、间距、QSS 生成、系统暗色检测

约定
- 所有尺寸用 px，避免不同 DPI 下 point size 跳动
- 相邻嵌套圆角保持同心：外层 = 内层 + 内边距
- 分离用发丝线（低对比），深度只用一层柔和扩散阴影（仅完成弹窗）
"""
from __future__ import annotations

import sys
from functools import lru_cache

# ---------------------------------------------------------------- 令牌

LIGHT = {
    "canvas": "#F6F7F9",
    "surface": "#FFFFFF",
    "sunken": "#F1F3F7",
    "ink": "#16181D",
    "ink2": "#5C6673",
    "ink3": "#8C95A3",
    "line": "#E5E8ED",
    "line_strong": "#D5DAE2",
    "check_border": "#C6CEDB",
    "row_hover": "#F4F6FA",
    "row_selected": "#EDF1FB",
    "accent": "#2B5BD7",
    "accent_hover": "#2450C4",
    "accent_press": "#1D44A8",
    "accent_soft": "#EEF2FD",
    "accent_ink": "#FFFFFF",
    "ok": "#12805A",
    "ok_soft": "#E6F4EE",
    "err": "#C4392B",
    "err_soft": "#FBEDEB",
    "ghost_hover": "#EEF0F5",
    "shadow": "#0B1220",
}

DARK = {
    "canvas": "#15171B",
    "surface": "#1D2026",
    "sunken": "#22252C",
    "ink": "#E8EBF0",
    "ink2": "#A6AEBC",
    "ink3": "#767F8D",
    "line": "#2B2F37",
    "line_strong": "#3A404A",
    "check_border": "#474E5B",
    "row_hover": "#242830",
    "row_selected": "#252B3A",
    "accent": "#6C93F7",
    "accent_hover": "#82A2F9",
    "accent_press": "#5B84F5",
    "accent_soft": "#212942",
    "accent_ink": "#10131A",
    "ok": "#3FB984",
    "ok_soft": "#1A2C25",
    "err": "#E8796B",
    "err_soft": "#32211F",
    "ghost_hover": "#252932",
    "shadow": "#000000",
}

# 字号（px）
F_META = 11
F_SMALL = 12
F_BODY = 13
F_LEAD = 14
F_TITLE = 15

# 圆角
R_ROW = 6
R_CARD = 10

# 间距
S1, S2, S3, S4, S5 = 4, 8, 12, 16, 20

ROW_HEIGHT = 34

# 字重策略（实测于 Windows + 微软雅黑 UI）
#   w400 = Regular，w500 也落到 Regular —— 中文族只有 Regular/Bold 两个字面，
#   请求 600/700 会被 GDI 映射到 **Bold**，小字号下笔画会粘连（用户反馈"字太粗/笔画连在一起"）。
#   因此界面里一律不使用 > 500 的字重；层级靠字号与颜色表达。
#   需要真正的半粗体时只用于纯拉丁文本，用 font_semibold()（Segoe UI Semibold 字面）。
W_REGULAR = 400
W_MEDIUM = 500
W_MAX = 500

UI_FAMILIES = ["Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei"]
CJK_FALLBACK = ["Microsoft YaHei UI", "Microsoft YaHei"]
MONO_FAMILIES = ["Cascadia Mono", "Consolas", "Courier New"]
SEMIBOLD_FAMILIES = ["Segoe UI Variable Text Semibold", "Segoe UI Variable Display Semibold",
                     "Segoe UI Semibold", "Segoe UI"]

# 实际可用的字体族（启动时解析一次）。
# 实测：把不存在的族名留在列表里，每次字体解析都要走一次回退匹配，
# 首帧因此多花约 0.33s（本机 Segoe UI Variable Text 并不存在）。
_resolved_ui: list[str] | None = None
_resolved_mono: list[str] | None = None


def resolve_fonts() -> None:
    """解析一次可用字体族；需在 QApplication 创建之后调用。"""
    global _resolved_ui, _resolved_mono
    try:
        from PySide6.QtGui import QFontDatabase
        available = set(QFontDatabase.families())
    except Exception:
        available = set()

    def pick(candidates: list[str]) -> list[str]:
        got = [c for c in candidates if c in available]
        return got or [candidates[-1]]

    def uniq(items: list[str]) -> list[str]:
        seen, out = set(), []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    _resolved_ui = uniq(pick(UI_FAMILIES) + [f for f in CJK_FALLBACK if f in available])
    _resolved_mono = uniq(pick(MONO_FAMILIES))
    font.cache_clear()
    font_semibold.cache_clear()

_tokens = LIGHT
_dark = False
_forced: bool | None = None


def tokens() -> dict:
    return _tokens


def is_dark() -> bool:
    return _dark


def force(dark: bool | None) -> None:
    """强制主题（None = 跟随系统）。主要用于测试与离线截图。"""
    global _forced
    _forced = dark


def system_prefers_dark() -> bool:
    """读取 Windows「应用模式」设置；非 Windows 或读取失败时返回 False。"""
    if _forced is not None:
        return _forced
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return int(value) == 0
    except Exception:
        return False


def set_dark(dark: bool) -> None:
    global _tokens, _dark
    _dark = bool(dark)
    _tokens = DARK if _dark else LIGHT


def _qss() -> str:
    """只用 QSS 管颜色/几何；字号统一在代码里用 QFont 设置。

    实测：在 QSS 里写 font-size 会让每个控件走一遍样式字体解析，
    首帧因此多花约 0.3s（远大于它带来的便利）。
    """
    t = _tokens
    return f"""
/* ---------------------------------------------------------------- 基础 */
QWidget {{
    color: {t['ink']};
}}
QWidget#root {{
    background: {t['canvas']};
}}
QToolTip {{
    background: {t['ink']};
    color: {t['surface']};
    border: none;
    padding: 5px 8px;
    border-radius: 6px;
}}

/* ---------------------------------------------------------------- 拖放区 */
QWidget#dropZone {{
    background: {t['sunken']};
    border: 1px dashed {t['line_strong']};
    border-radius: {R_CARD}px;
}}
QWidget#dropZone[dragActive="true"] {{
    background: {t['accent_soft']};
    border: 1px dashed {t['accent']};
}}
QWidget#dropZone[hovered="true"] {{
    border: 1px dashed {t['accent']};
}}
QLabel#dropTitle {{
    color: {t['ink']};
}}
QLabel#dropHint {{
    color: {t['ink3']};
}}
QLabel#dropSmall {{
    color: {t['ink2']};
}}

/* ---------------------------------------------------------------- 文件列表 */
QListWidget#fileList {{
    background: {t['surface']};
    border: 1px solid {t['line']};
    border-radius: {R_CARD}px;
    padding: 4px 0;
    outline: none;
}}
QListWidget#fileList::item {{
    background: transparent;
    border: none;
}}

/* ---------------------------------------------------------------- 文本 */
QLabel#metaText {{
    color: {t['ink3']};
}}

/* ---------------------------------------------------------------- 按钮 */
QPushButton {{
    border-radius: 8px;
    padding: 0 14px;
    border: 1px solid transparent;
}}
QPushButton#primary {{
    background: {t['accent']};
    color: {t['accent_ink']};
}}
QPushButton#primary:hover  {{ background: {t['accent_hover']}; }}
QPushButton#primary:pressed{{ background: {t['accent_press']}; }}
QPushButton#primary:disabled {{
    background: {t['sunken']};
    color: {t['ink3']};
}}
QPushButton#ghost {{
    background: transparent;
    color: {t['ink2']};
    border: 1px solid {t['line_strong']};
}}
QPushButton#ghost:hover   {{ background: {t['ghost_hover']}; color: {t['ink']}; }}
QPushButton#ghost:pressed {{ background: {t['sunken']}; }}
QPushButton#ghost:disabled {{
    color: {t['ink3']};
    border-color: {t['line']};
}}
QPushButton#link {{
    background: transparent;
    border: none;
    padding: 0 6px;
    color: {t['ink3']};
    text-align: left;
}}
QPushButton#link:hover   {{ color: {t['accent']}; }}
QPushButton#link:pressed {{ color: {t['accent_press']}; }}

/* ---------------------------------------------------------------- 进度 */
QProgressBar#rail {{
    background: {t['line']};
    border: none;
    border-radius: 2px;
    max-height: 3px;
    min-height: 3px;
}}
QProgressBar#rail::chunk {{
    border-radius: 2px;
    background: {t['accent']};
}}

/* ---------------------------------------------------------------- 滚动条 */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {t['line_strong']};
    border-radius: 4px;
    min-height: 28px;
    margin: 0 3px;
}}
QScrollBar::handle:vertical:hover {{ background: {t['ink3']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ height: 0px; }}

/* ---------------------------------------------------------------- 标题栏 */
QWidget#titleBar {{
    background: {t['canvas']};
    border-bottom: 1px solid {t['line']};
}}
QLabel#winTitle {{
    color: {t['ink']};
    background: transparent;
}}

/* ---------------------------------------------------------------- 设置面板 */
QDialog#settingsPanel {{
    background: {t['surface']};
}}
QDialog#settingsPanel QLabel {{
    background: transparent;
}}
QMenu {{
    background: {t['surface']};
    border: 1px solid {t['line']};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px 6px 12px;
    border-radius: 6px;
    color: {t['ink']};
}}
QMenu::item:selected {{
    background: {t['accent_soft']};
    color: {t['ink']};
}}
QMenu::separator {{
    height: 1px;
    background: {t['line']};
    margin: 4px 8px;
}}

/* ---------------------------------------------------------------- 弹窗 */
QDialog {{ background: {t['surface']}; }}
QWidget#card {{ background: {t['surface']}; }}
QLabel#dlgTitle {{ color: {t['ink']}; }}
QLabel#dlgSub {{ color: {t['ink2']}; }}
QLabel#failName {{ color: {t['ink']}; }}
QLabel#failMsg {{ color: {t['err']}; }}
QScrollArea#failScroll {{
    background: {t['canvas']};
    border: 1px solid {t['line']};
    border-radius: 8px;
}}
QWidget#failInner {{ background: {t['canvas']}; }}
"""


def apply(app, dark: bool | None = None) -> None:
    """检测/设置主题并把 QSS 应用到整个应用。"""
    if dark is None:
        dark = system_prefers_dark()
    set_dark(dark)
    resolve_fonts()
    app.setStyleSheet(_qss())


def apply_titlebar(window, dark: bool | None = None) -> None:
    """让原生标题栏跟随暗色（Win10 20H1+ / Win11）。"""
    if sys.platform != "win32":
        return
    dark = is_dark() if dark is None else dark
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = wintypes.HWND(int(window.winId()))
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):                      # DWMWA_USE_IMMERSIVE_DARK_MODE
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, ctypes.c_uint(attr), ctypes.byref(value), ctypes.sizeof(value)
            ) == 0:
                break
    except Exception:
        pass


def style_window(window) -> None:
    """无边框窗口：向 DWM 申请圆角，并**明确要求不画窗口边框**。

    这里是黑边问题的最终处理：
    - 不用 `DwmExtendFrameIntoClientArea`（会形成一圈"扩展边框"，某些系统设置下是黑的）；
    - 用 `DWMWA_BORDER_COLOR = DWMWA_COLOR_NONE` 关掉 Win11 自带的 1px 窗口边框；
    - 窗口边缘不再由我们画发丝线（QSS 里的 border 已移除）。
    于是窗口四周不会有任何线条。
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = wintypes.HWND(int(window.winId()))
        dwm = ctypes.windll.dwmapi

        preference = ctypes.c_int(2)               # DWMWCP_ROUND
        dwm.DwmSetWindowAttribute(hwnd, ctypes.c_uint(33),
                                  ctypes.byref(preference), ctypes.sizeof(preference))

        none_border = ctypes.c_uint(0xFFFFFFFE)    # DWMWA_COLOR_NONE
        dwm.DwmSetWindowAttribute(hwnd, ctypes.c_uint(34),
                                  ctypes.byref(none_border), ctypes.sizeof(none_border))
    except Exception:
        pass


@lru_cache(maxsize=32)
def font(pixel_size: int, weight: int = W_REGULAR, mono: bool = False):
    """字体对象带缓存；字重被钳制在 500 以内（>=600 在中文下会变粗体并粘连笔画）。"""
    from PySide6.QtGui import QFont

    if _resolved_ui is None:
        resolve_fonts()
    families = (_resolved_mono if mono else _resolved_ui) or (
        MONO_FAMILIES if mono else UI_FAMILIES)
    w = int(weight) if weight else W_REGULAR
    if w > W_MAX:
        w = W_MAX
    f = QFont()
    f.setFamilies(families)
    f.setPixelSize(pixel_size)
    f.setWeight(QFont.Weight(w))
    return f


@lru_cache(maxsize=8)
def font_semibold(pixel_size: int):
    """真正的半粗体字面，**仅用于纯拉丁文本**（中文没有该字面，会退化成 Bold）。"""
    from PySide6.QtGui import QFont, QFontInfo

    if _resolved_ui is None:
        resolve_fonts()
    families = SEMIBOLD_FAMILIES
    probe = QFont(families[0])
    if QFontInfo(probe).family() != families[0]:
        families = _resolved_ui or UI_FAMILIES          # 系统没有 Semibold 时退回常规族
    f = QFont()
    f.setFamilies(families)
    f.setPixelSize(pixel_size)
    f.setWeight(QFont.Weight(W_REGULAR))
    return f


def app_font():
    """应用基础字体（Qt 会在中文缺字时自动回退到雅黑）。"""
    return font(F_BODY, 400)


def set_font(widget, pixel_size: int, weight: int = 400, mono: bool = False) -> None:
    """给控件设置字号（字号统一在代码里设置，QSS 里不写 font-size）。"""
    widget.setFont(font(pixel_size, weight, mono))


def qss() -> str:
    """当前主题的 QSS（供离线截图等场景使用）。"""
    return _qss()


def color(key: str):
    from PySide6.QtGui import QColor

    return QColor(_tokens[key])
