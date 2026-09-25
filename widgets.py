"""自绘控件：开关、分段控件、标题栏

全部用 QPainter 绘制，不依赖图片资源与 QSS 伪元素，
因此在任意 DPI 下都锐利，也能精确跟随主题（含深色）。
"""
from __future__ import annotations

from PySide6.QtCore import (
    Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton, QButtonGroup, QHBoxLayout, QLabel, QSizePolicy, QWidget,
)

import theme

TITLE_H = 40
WIN_BTN_W = 46


# ---------------------------------------------------------------- 字形

def paint_sliders(p: QPainter, box: QRectF, color: QColor, width: float = 1.5) -> None:
    """设置图标：两条滑轨 + 旋钮（比齿轮更容易画得精确干净）。"""
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(color)
    rail = box.width() * 0.62
    x0 = box.center().x() - rail / 2
    x1 = box.center().x() + rail / 2
    y_top = box.center().y() - box.height() * 0.17
    y_bot = box.center().y() + box.height() * 0.17
    p.drawLine(QRectF(x0, y_top, rail, 0).topLeft(), QRectF(x0, y_top, rail, 0).topRight())
    p.drawLine(QRectF(x0, y_bot, rail, 0).topLeft(), QRectF(x0, y_bot, rail, 0).topRight())
    knob = box.width() * 0.11
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(x0 + rail * 0.30 - knob / 2, y_top - knob / 2, knob, knob))
    p.drawEllipse(QRectF(x0 + rail * 0.70 - knob / 2, y_bot - knob / 2, knob, knob))


def paint_min(p: QPainter, box: QRectF, color: QColor, width: float = 1.0) -> None:
    p.setPen(QPen(color, width))
    w = box.width() * 0.38
    y = box.center().y() + box.height() * 0.16
    p.drawLine(QRectF(box.center().x() - w / 2, y, w, 0).topLeft(),
               QRectF(box.center().x() - w / 2, y, w, 0).topRight())


def paint_max(p: QPainter, box: QRectF, color: QColor, width: float = 1.0) -> None:
    p.setPen(QPen(color, width))
    s = box.width() * 0.36
    r = QRectF(box.center().x() - s / 2, box.center().y() - s / 2, s, s)
    p.drawRect(r)


def paint_restore(p: QPainter, box: QRectF, color: QColor, width: float = 1.0) -> None:
    p.setPen(QPen(color, width))
    s = box.width() * 0.32
    off = box.width() * 0.09
    p.drawRect(QRectF(box.center().x() - s / 2 - off, box.center().y() - s / 2 + off, s, s))
    path = QPainterPath()
    path.moveTo(box.center().x() - s / 2 + off, box.center().y() - s / 2 - off)
    path.lineTo(box.center().x() + s / 2 + off, box.center().y() - s / 2 - off)
    path.lineTo(box.center().x() + s / 2 + off, box.center().y() + s / 2 - off)
    p.drawPath(path)


def paint_close(p: QPainter, box: QRectF, color: QColor, width: float = 1.0) -> None:
    p.setPen(QPen(color, width))
    s = box.width() * 0.34
    c = box.center()
    p.drawLine(QRectF(c.x() - s / 2, c.y() - s / 2, 0, 0).topLeft(),
               QRectF(c.x() + s / 2, c.y() + s / 2, 0, 0).topLeft())
    p.drawLine(QRectF(c.x() + s / 2, c.y() - s / 2, 0, 0).topLeft(),
               QRectF(c.x() - s / 2, c.y() + s / 2, 0, 0).topLeft())


# ---------------------------------------------------------------- 开关

class ToggleSwitch(QAbstractButton):
    """iOS 风格开关：轨道 + 滑块，切换带 140ms 缓动。"""

    W, H = 34, 20

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._offset = 1.0 if checked else 0.0
        self._anim: QPropertyAnimation | None = None
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.W, self.H)

    def sizeHint(self) -> QSize:
        return QSize(self.W, self.H)

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = max(0.0, min(1.0, value))
        self.update()

    offset = Property(float, get_offset, set_offset)

    def nextCheckState(self) -> None:
        super().nextCheckState()
        self._animate()

    def setChecked(self, checked: bool) -> None:  # noqa: N802
        super().setChecked(checked)
        if hasattr(self, "_offset"):
            self._animate()

    def _animate(self) -> None:
        if not hasattr(self, "_offset"):
            return
        target = 1.0 if self.isChecked() else 0.0
        anim = QPropertyAnimation(self, b"offset", self)
        anim.setDuration(140)
        anim.setStartValue(self._offset)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anim = anim

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        track = QRectF(0, 0, self.W, self.H)
        radius = self.H / 2
        off_color = theme.color("check_border")
        on_color = theme.color("accent")
        base = QColor(off_color)
        on = QColor(on_color)
        mix = QColor(
            int(base.red() + (on.red() - base.red()) * self._offset),
            int(base.green() + (on.green() - base.green()) * self._offset),
            int(base.blue() + (on.blue() - base.blue()) * self._offset),
        )
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(mix)
        p.drawRoundedRect(track, radius, radius)

        knob_d = self.H - 6
        x = 3 + (self.W - knob_d - 6) * self._offset
        p.setBrush(theme.color("surface"))
        p.drawEllipse(QRectF(x, 3, knob_d, knob_d))
        p.end()


# ---------------------------------------------------------------- 分段控件

class SegmentedControl(QWidget):
    """互斥分段选择（选项少时比下拉更直观，也更精致）。"""

    changed = Signal(int)

    H = 28

    def __init__(self, options: list[str], current: int = 0, parent=None):
        super().__init__(parent)
        self._options = options
        self._index = current
        self._offset = float(current)
        self.setFixedHeight(self.H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim: QPropertyAnimation | None = None

    def sizeHint(self) -> QSize:
        return QSize(max(200, 110 * len(self._options)), self.H)

    def index(self) -> int:
        return self._index

    def set_index(self, index: int, animate: bool = True) -> None:
        index = max(0, min(len(self._options) - 1, index))
        if index == self._index and animate:
            return
        self._index = index
        if animate:
            anim = QPropertyAnimation(self, b"offset", self)
            anim.setDuration(150)
            anim.setStartValue(self._offset)
            anim.setEndValue(float(index))
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            self._anim = anim
        else:
            self.set_offset(float(index))
        self.changed.emit(index)

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    def mousePressEvent(self, event):
        seg = self.width() / max(1, len(self._options))
        idx = int(event.position().x() // seg)
        self.set_index(idx)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.color("sunken"))
        p.drawRoundedRect(rect, 8, 8)

        seg_w = self.width() / max(1, len(self._options))
        pill = QRectF(self._offset * seg_w + 2, 2, seg_w - 4, self.height() - 4)
        p.setBrush(theme.color("surface"))
        p.drawRoundedRect(pill, 6, 6)

        theme.set_font(self, theme.F_SMALL, theme.W_MEDIUM)
        for i, text in enumerate(self._options):
            active = i == self._index
            p.setPen(theme.color("ink" if active else "ink2"))
            p.setFont(theme.font(theme.F_SMALL,
                                 theme.W_MEDIUM if active else theme.W_REGULAR))
            p.drawText(QRectF(i * seg_w, 0, seg_w, self.height()),
                       int(Qt.AlignmentFlag.AlignCenter), text)
        p.end()


# ---------------------------------------------------------------- 标题栏按钮

class TitleButton(QAbstractButton):
    """标题栏窗口按钮（最小化/最大化/关闭）。"""

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(WIN_BTN_W, TITLE_H)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def paintEvent(self, event) -> None:
        t = theme.tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        hovered = self.underMouse()
        pressed = self.isDown()

        if hovered or pressed:
            if self.kind == "close":
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor("#D64541") if not pressed else QColor("#B93B38"))
                p.drawRect(rect)
                color = QColor("#FFFFFF")
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(t["ink"]))
                c = p.brush().color()
                c.setAlpha(28 if not pressed else 44)
                p.setBrush(c)
                p.drawRect(rect)
                color = theme.color("ink")
        else:
            color = theme.color("ink2")

        glyph = QRectF(rect.center().x() - 10, rect.center().y() - 10, 20, 20)
        if self.kind == "min":
            paint_min(p, glyph, color, 1.0)
        elif self.kind == "max":
            paint_max(p, glyph, color, 1.0)
        elif self.kind == "restore":
            paint_restore(p, glyph, color, 1.0)
        else:
            paint_close(p, glyph, color, 1.0)
        p.end()


# ---------------------------------------------------------------- 标题栏

class TitleBar(QWidget):
    """自绘标题栏：左侧设置按钮 + 标题，右侧最小化/最大化/关闭。"""

    settings_clicked = Signal()
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()
    drag_started = Signal()
    double_clicked = Signal()

    def __init__(self, title: str = "PortableConverterMD", parent=None):
        super().__init__(parent)
        self.setFixedHeight(TITLE_H)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("titleBar")

        row = QHBoxLayout(self)
        row.setContentsMargins(4, 0, 0, 0)
        row.setSpacing(2)
        self.setProperty("maximized", False)

        self.btn_settings = _SettingsButton()
        self.btn_settings.clicked.connect(self.settings_clicked)
        row.addWidget(self.btn_settings, 0, Qt.AlignmentFlag.AlignVCenter)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("winTitle")
        self.lbl_title.setFont(theme.font_semibold(theme.F_SMALL))   # 纯拉丁标题用真半粗体
        row.addWidget(self.lbl_title, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)

        self.btn_min = TitleButton("min")
        self.btn_min.clicked.connect(self.minimize_clicked)
        self.btn_max = TitleButton("max")
        self.btn_max.clicked.connect(self.maximize_clicked)
        self.btn_close = TitleButton("close")
        self.btn_close.clicked.connect(self.close_clicked)
        for b in (self.btn_min, self.btn_max, self.btn_close):
            row.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_maximized(self, maximized: bool) -> None:
        self.btn_max.kind = "restore" if maximized else "max"
        self.btn_max.update()
        self.setProperty("maximized", maximized)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_title_text(self, text: str) -> None:
        self.lbl_title.setText(text)

    def refresh_theme(self) -> None:
        """颜色由 QSS 控制，这里只需要重绘自绘按钮。"""
        for b in (self.btn_settings, self.btn_min, self.btn_max, self.btn_close):
            b.update()
        self.update()

    # 拖动 / 双击最大化交给主窗口处理
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_started.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()


class _SettingsButton(QAbstractButton):
    """标题栏左侧设置按钮（滑轨字形）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(34, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip("设置")

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        if self.underMouse() or self.isDown():
            p.setPen(Qt.PenStyle.NoPen)
            c = theme.color("ink")
            c.setAlpha(30 if not self.isDown() else 46)
            p.setBrush(c)
            p.drawRoundedRect(rect.adjusted(1, 2, -1, -2), 6, 6)
        glyph = QRectF(rect.center().x() - 9, rect.center().y() - 9, 18, 18)
        paint_sliders(p, glyph, theme.color("ink2"), 1.5)
        p.end()
