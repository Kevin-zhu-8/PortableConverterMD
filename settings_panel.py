"""设置面板：紧贴标题栏齿轮按钮的**下拉浮层**

设计约束：
1. **不能有任何窗口边框线**：不透明背景、不画自绘边框、不使用
   `DwmExtendFrameIntoClientArea`，并用 `DWMWA_BORDER_COLOR=NONE` 关掉 Win11 自带边框
   （见 theme.style_window）。
2. **尽量少占主窗口面积**：固定 300px 宽、内容自然高度（约 300px），
   像菜单一样挂在齿轮按钮下方，而不是铺满窗口。
3. 改动即时生效并持久化，没有"确定/取消"；点外部 / Esc / 右上角 ✕ 关闭。
"""
from __future__ import annotations

import os

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QAbstractButton, QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

import settings
import theme
from converter import get_log_dir
from widgets import SegmentedControl, ToggleSwitch, paint_close

PANEL_W = 300             # 固定宽度（下拉菜单感）
GAP_SECTION = 12
GAP_ROW = 6


def _label(text: str, size: int = theme.F_SMALL, weight: int = 400, color: str = "ink") -> QLabel:
    lbl = QLabel(text)
    theme.set_font(lbl, size, weight)
    lbl.setStyleSheet(f"color: {theme.tokens()[color]}; background: transparent;")
    return lbl


def _link_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("link")
    theme.set_font(btn, theme.F_META, 500)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(18)
    return btn


class _CloseButton(QAbstractButton):
    """下拉面板右上角关闭按钮（自绘 ✕）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip("关闭设置")

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self.underMouse() or self.isDown():
            c = theme.color("ink")
            c.setAlpha(28 if not self.isDown() else 44)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)
        paint_close(p, QRectF(4, 4, 18, 18), theme.color("ink2"), 1.1)
        p.end()


class _Section(QWidget):
    def __init__(self, title: str):
        super().__init__()
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(GAP_ROW)
        box.addWidget(_label(title, theme.F_META, theme.W_REGULAR, "ink3"))
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(GAP_ROW)
        box.addLayout(self.body)

    def add_row(self, label: str, control: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.S3)
        row.addWidget(_label(label), 1)
        row.addWidget(control, 0, Qt.AlignmentFlag.AlignRight)
        self.body.addLayout(row)
        return row


class SettingsPanel(QDialog):
    """设置下拉浮层。"""

    output_mode_changed = Signal(str)
    keep_in_background_changed = Signal(bool)
    logging_changed = Signal(bool)
    autostart_changed = Signal(bool)
    custom_dir_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("settingsPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("设置")
        self.setFixedWidth(PANEL_W)

        root = QVBoxLayout(self)
        root.setContentsMargins(theme.S4, theme.S3, theme.S4, theme.S3)
        root.setSpacing(GAP_SECTION)

        # ---------------- 头部 ----------------
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(theme.S2)
        header.addWidget(_label("设置", theme.F_BODY, theme.W_MEDIUM))
        header.addStretch(1)
        self.btn_close = _CloseButton()
        self.btn_close.clicked.connect(self.close)
        header.addWidget(self.btn_close, 0, Qt.AlignmentFlag.AlignRight)
        root.addLayout(header)

        # ---------------- 输出位置 ----------------
        sec_out = _Section("输出位置")
        self.seg_mode = SegmentedControl(
            ["与源文件同目录", f"{settings.SUBFOLDER_NAME} 文件夹"],
            current=0 if settings.output_mode() == settings.MODE_SAME_DIR else 1)
        self.seg_mode.changed.connect(self._on_mode)
        sec_out.body.addWidget(self.seg_mode)

        self.lbl_custom = _label("", theme.F_META, 400, "ink3")
        self.lbl_custom.setWordWrap(True)
        sec_out.body.addWidget(self.lbl_custom)

        row_custom = QHBoxLayout()
        row_custom.setContentsMargins(0, 0, 0, 0)
        row_custom.setSpacing(theme.S3)
        self.btn_pick = _link_button("选择自定义目录…")
        self.btn_pick.clicked.connect(self._pick_custom)
        row_custom.addWidget(self.btn_pick)
        self.btn_clear_custom = _link_button("清除")
        self.btn_clear_custom.clicked.connect(self._clear_custom)
        row_custom.addWidget(self.btn_clear_custom)
        row_custom.addStretch(1)
        sec_out.body.addLayout(row_custom)
        root.addWidget(sec_out)

        # ---------------- 启动与后台 ----------------
        sec_run = _Section("启动与后台")
        self.sw_autostart = ToggleSwitch(settings.autostart_enabled())
        self.sw_autostart.toggled.connect(self._on_autostart)
        sec_run.add_row("开机启动", self.sw_autostart)

        self.sw_background = ToggleSwitch(settings.keep_in_background())
        self.sw_background.toggled.connect(self._on_background)
        sec_run.add_row("关闭窗口后继续运行", self.sw_background)

        self.lbl_hint = _label("", theme.F_META, 400, "err")
        self.lbl_hint.setWordWrap(True)
        sec_run.body.addWidget(self.lbl_hint)
        root.addWidget(sec_run)

        # ---------------- 日志 ----------------
        sec_log = _Section("日志")
        self.sw_log = ToggleSwitch(settings.logging_enabled())
        self.sw_log.toggled.connect(self._on_log)
        sec_log.add_row("记录转换日志", self.sw_log)

        self.btn_log_dir = _link_button("打开日志文件夹")
        self.btn_log_dir.clicked.connect(self._open_log_dir)
        sec_log.body.addWidget(self.btn_log_dir, 0, Qt.AlignmentFlag.AlignLeft)
        root.addWidget(sec_log)

        self._refresh_custom()

    # ---------------------------------------------------------- 行为

    def _refresh_custom(self) -> None:
        custom = settings.custom_dir()
        if custom:
            text = custom if len(custom) <= 34 else "…" + custom[-33:]
            self.lbl_custom.setText(f"自定义目录：{text}")
            self.lbl_custom.setToolTip(custom)
            self.lbl_custom.setVisible(True)
        else:
            self.lbl_custom.setVisible(False)
        self.btn_pick.setVisible(not custom)
        self.btn_clear_custom.setVisible(bool(custom))

    def _on_mode(self, index: int) -> None:
        mode = settings.MODE_SAME_DIR if index == 0 else settings.MODE_SUBFOLDER
        settings.set_output_mode(mode)
        self.output_mode_changed.emit(mode)

    def _pick_custom(self) -> None:
        start = settings.custom_dir() or ""
        chosen = QFileDialog.getExistingDirectory(self, "选择输出目录", start)
        if chosen:
            settings.set_custom_dir(chosen)
            self._refresh_custom()
            self.custom_dir_changed.emit(chosen)

    def _clear_custom(self) -> None:
        settings.set_custom_dir("")
        self._refresh_custom()
        self.custom_dir_changed.emit("")

    def _on_background(self, checked: bool) -> None:
        settings.set_keep_in_background(checked)
        self.keep_in_background_changed.emit(checked)

    def _on_log(self, checked: bool) -> None:
        settings.set_logging_enabled(checked)
        self.logging_changed.emit(checked)

    def _on_autostart(self, checked: bool) -> None:
        ok = settings.set_autostart(checked)
        if not ok:
            self.sw_autostart.blockSignals(True)
            self.sw_autostart.setChecked(settings.autostart_enabled())
            self.sw_autostart.blockSignals(False)
            self.lbl_hint.setText("无法写入开机启动项（可能被安全软件拦截）")
            self.lbl_hint.setVisible(True)
        else:
            self.lbl_hint.setText("")
            self.lbl_hint.setVisible(False)
            self.autostart_changed.emit(checked)

    def _open_log_dir(self) -> None:
        try:
            path = get_log_dir()
            if os.path.isdir(path):
                os.startfile(path)
        except Exception:
            pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        theme.style_window(self)      # 圆角 + 明确不要窗口边框

    # ---------------------------------------------------------- 下拉

    def popup_at(self, anchor: QWidget = None) -> None:
        """像下拉菜单一样挂在齿轮按钮下方。"""
        self.adjustSize()
        parent = self.parentWidget()
        if anchor is not None:
            origin = anchor.mapToGlobal(QPoint(0, anchor.height()))
            pos = QPoint(origin.x() + 2, origin.y() + 4)     # 与窗口左内边距对齐
        elif parent is not None:
            origin = parent.mapToGlobal(QPoint(0, 0))
            pos = QPoint(origin.x() + theme.S4, origin.y() + 44)
        else:
            pos = QPoint(100, 100)

        screen = (anchor or parent or self).screen() or self.screen()
        if screen is not None:
            avail = screen.availableGeometry()
            pos.setX(max(avail.left() + 6, min(pos.x(), avail.right() - self.width() - 6)))
            if pos.y() + self.height() > avail.bottom() - 6:
                pos.setY(max(avail.top() + 6, avail.bottom() - self.height() - 6))
        self.move(pos)
        self.show()
        self.raise_()
        self.setFocus(Qt.FocusReason.PopupFocusReason)
