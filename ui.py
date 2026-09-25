"""PortableConverterMD — 界面层

设计原则
- 精密仪器感：单色中性底 + 一个深钴蓝强调色，发丝分隔线代替灰边框
- 小巧：默认 560×470，空态只显示拖放区，有文件时拖放区收成细条
- 细节：自绘复选框/状态字形/等宽数字列（同行数字对齐）、同心圆角、
  仅 160ms 的柔和进场动画、跟随系统暗色与暗色标题栏
"""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import (
    QAbstractAnimation, QEasingCurve, QEvent, QObject, QPropertyAnimation, QRectF,
    QSettings, QSize, Qt, QTimer, Signal,
)
from PySide6.QtGui import (
    QColor, QDragEnterEvent, QDropEvent, QFontMetrics, QIcon, QPainter,
    QPainterPath, QPen,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QStyle,
    QStyledItemDelegate, QSystemTrayIcon, QVBoxLayout, QWidget,
)

import settings
import theme
from converter import get_app_dir, get_log_dir, ocr_backend_label
from settings_panel import SettingsPanel
from widgets import TITLE_H, TitleBar
from worker import ConvertWorker

# 列表项数据角色
ROLE_STATE = Qt.ItemDataRole.UserRole + 1      # idle / running / done / failed
ROLE_SIZE = Qt.ItemDataRole.UserRole + 2
ROLE_ERROR = Qt.ItemDataRole.UserRole + 3

SUPPORT_HINT = "docx · xlsx · pptx · pdf · 图片 OCR · html · csv · json · zip"
BATCH_LIMIT = 500

# ------------------------------------------------------------ 通用绘制


def _draw_check(p: QPainter, box: QRectF, color: QColor, width: float = 1.7) -> None:
    path = QPainterPath()
    path.moveTo(box.left() + box.width() * 0.24, box.center().y() + box.height() * 0.02)
    path.lineTo(box.left() + box.width() * 0.43, box.center().y() + box.height() * 0.21)
    path.lineTo(box.left() + box.width() * 0.77, box.center().y() - box.height() * 0.22)
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                  Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)


def _draw_cross(p: QPainter, box: QRectF, color: QColor, width: float = 1.7) -> None:
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    r = box.adjusted(box.width() * 0.26, box.height() * 0.26, -box.width() * 0.26, -box.height() * 0.26)
    p.drawLine(r.topLeft(), r.bottomRight())
    p.drawLine(r.topRight(), r.bottomLeft())


def _draw_plus(p: QPainter, box: QRectF, color: QColor, width: float = 1.5) -> None:
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    c = box.center()
    d = box.width() * 0.30
    p.drawLine(c.x() - d, c.y(), c.x() + d, c.y())
    p.drawLine(c.x(), c.y() - d, c.x(), c.y() + d)


def _draw_tray_arrow(p: QPainter, box: QRectF, color: QColor, width: float = 1.5) -> None:
    """下载/入库字形：底部托盘 + 向下箭头（1.5px 细线，比图标字体更干净）。"""
    from PySide6.QtCore import QPointF

    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                  Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    w, h = box.width(), box.height()
    tray = QPainterPath()
    tray.moveTo(box.left() + w * 0.10, box.top() + h * 0.62)
    tray.lineTo(box.left() + w * 0.10, box.top() + h * 0.88)
    tray.lineTo(box.left() + w * 0.90, box.top() + h * 0.88)
    tray.lineTo(box.left() + w * 0.90, box.top() + h * 0.62)
    p.drawPath(tray)
    p.drawLine(QPointF(box.left() + w * 0.50, box.top() + h * 0.12),
               QPointF(box.left() + w * 0.50, box.top() + h * 0.60))
    arrow = QPainterPath()
    arrow.moveTo(box.left() + w * 0.31, box.top() + h * 0.43)
    arrow.lineTo(box.left() + w * 0.50, box.top() + h * 0.63)
    arrow.lineTo(box.left() + w * 0.69, box.top() + h * 0.43)
    p.drawPath(arrow)


def _enum_value(value):
    """PySide6 各版本对枚举/int 的互转不一致，统一取底层整数值。"""
    return getattr(value, "value", value)


def _font(widget, size: int, weight: int = 400) -> None:
    """字号统一在代码里设置：QSS 里写 font-size 会显著拖慢首帧。"""
    widget.setFont(theme.font(size, weight))


def _human_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"


# ------------------------------------------------------------ 字形组件


class _Glyph(QWidget):
    """自绘字形：展开态画托盘箭头，收起态画加号。"""

    def __init__(self, size: int = 26):
        super().__init__()
        self._compact = False
        self._active = False
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_compact(self, compact: bool) -> None:
        self._compact = compact
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def paintEvent(self, event) -> None:
        t = theme.tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = theme.color("accent") if self._active else theme.color("ink3")
        box = QRectF(0, 0, self.width(), self.height())
        if self._compact:
            _draw_plus(p, box, color, 1.6)
        else:
            _draw_tray_arrow(p, box, color, 1.5)
        p.end()


class _Badge(QWidget):
    """完成弹窗顶部的圆形徽标（矢量绘制，任意 DPI 都锐利）。"""

    def __init__(self, ok: bool, size: int = 44):
        super().__init__()
        self._ok = ok
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        t = theme.tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.color("ok_soft" if self._ok else "err_soft"))
        p.drawEllipse(rect)
        inner = rect.adjusted(rect.width() * 0.30, rect.height() * 0.30,
                              -rect.width() * 0.30, -rect.height() * 0.30)
        if self._ok:
            _draw_check(p, inner, theme.color("ok"), 2.2)
        else:
            p.setPen(QPen(theme.color("err"), 2.2, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap))
            c = inner.center()
            p.drawLine(c.x(), inner.top() + inner.height() * 0.02,
                       c.x(), inner.top() + inner.height() * 0.58)
            p.drawPoint(c.x(), inner.bottom() - inner.height() * 0.06)
        p.end()


# ------------------------------------------------------------ 拖放区


class DropZone(QWidget):
    """自适应拖放区：空态为大块提示，有文件时收成细条。"""

    files_dropped = Signal(list)

    EXPANDED_MIN_H = 132
    COMPACT_H = 44

    def __init__(self):
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("dragActive", False)
        self.setProperty("hovered", False)
        self._compact = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(theme.S4, theme.S3, theme.S4, theme.S3)
        outer.setSpacing(0)

        # 展开态：字形 + 标题 + 支持格式
        self._expanded = QWidget()
        exp = QVBoxLayout(self._expanded)
        exp.setContentsMargins(0, 0, 0, 0)
        exp.setSpacing(theme.S2)
        exp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.glyph = _Glyph(26)
        exp.addWidget(self.glyph, 0, Qt.AlignmentFlag.AlignHCenter)
        self.title = QLabel("拖入文件，或点击选择")
        self.title.setObjectName("dropTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exp.addWidget(self.title)
        self.hint = QLabel(SUPPORT_HINT)
        self.hint.setObjectName("dropHint")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exp.addWidget(self.hint)
        outer.addWidget(self._expanded, 1)

        # 收起态：按需创建（首帧少建 5 个控件，启动更快）
        self._compact_box = None
        self.glyph_small = None
        self.small = None

        # 直接落到展开态：这里不再调 _apply_mode()，避免构造期多余的 setVisible
        # （每一次都会触发样式抛光，是首帧开销的大头）
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(self.EXPANDED_MIN_H)
        _font(self.title, theme.F_LEAD, theme.W_MEDIUM)     # 主提示语：靠字号而非粗体
        _font(self.hint, theme.F_META)

    def _ensure_compact_box(self) -> QWidget:
        """收起态子控件懒创建。"""
        if self._compact_box is not None:
            return self._compact_box
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.S2)
        row.addStretch(1)
        self.glyph_small = _Glyph(18)
        self.glyph_small.set_compact(True)
        row.addWidget(self.glyph_small, 0, Qt.AlignmentFlag.AlignVCenter)
        self.small = QLabel("继续添加文件，或拖入文件夹")
        self.small.setObjectName("dropSmall")
        _font(self.small, theme.F_SMALL, 500)
        row.addWidget(self.small, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        self.layout().addWidget(box, 1)
        self._compact_box = box
        return box

    # ---- 状态 ----

    def _apply_mode(self) -> None:
        compact = self._compact
        if compact:
            self._ensure_compact_box().setVisible(True)
        if self._compact_box is not None:
            self._compact_box.setVisible(compact)
        self._expanded.setVisible(not compact)
        if compact:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setMinimumHeight(self.COMPACT_H)
            self.setMaximumHeight(self.COMPACT_H)
        else:
            # 空态让拖放区吃掉剩余空间，变成一个大号投放目标
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.setMinimumHeight(self.EXPANDED_MIN_H)
            self.setMaximumHeight(16777215)

    def set_compact(self, compact: bool) -> None:
        if compact == self._compact:
            return
        self._compact = compact
        self._apply_mode()
        self.update()

    def _set_flag(self, name: str, value: bool) -> None:
        if self.property(name) != value:
            self.setProperty(name, value)
            self.style().unpolish(self)
            self.style().polish(self)
            self.glyph.set_active(value)
            if self.glyph_small is not None:
                self.glyph_small.set_active(value)
            self.update()

    # ---- 事件 ----

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_flag("dragActive", True)

    def dragLeaveEvent(self, event):
        self._set_flag("dragActive", False)

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        self._set_flag("dragActive", False)
        if files:
            self.files_dropped.emit(files)

    def enterEvent(self, event):
        self._set_flag("hovered", True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_flag("hovered", False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择要转换的文件", "", "所有文件 (*.*)")
            if files:
                self.files_dropped.emit(files)


# ------------------------------------------------------------ 列表


class FileRowDelegate(QStyledItemDelegate):
    """自绘文件行：复选框 + 文件名 + 状态字形 + 等宽数字大小，行间发丝线。"""

    PAD_X = 12
    CHECK = 15
    GLYPH_COL = 20          # 右侧状态字形保留列（保证大小文本右对齐）
    GAP = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._f_name = theme.font(theme.F_SMALL, 400)
        self._f_meta = theme.font(theme.F_META, 400)
        self._f_mono = theme.font(theme.F_META, 400, mono=True)

    def refresh(self) -> None:
        self._f_name = theme.font(theme.F_SMALL, 400)
        self._f_meta = theme.font(theme.F_META, 400)
        self._f_mono = theme.font(theme.F_META, 400, mono=True)

    def sizeHint(self, option, index) -> QSize:
        return QSize(0, theme.ROW_HEIGHT)

    def paint(self, painter: QPainter, option, index) -> None:
        t = theme.tokens()
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        row = QRectF(option.rect)

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if selected or hovered:
            key = "row_selected" if selected else "row_hover"
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.color(key))
            painter.drawRoundedRect(row.adjusted(6, 2, -6, -2), theme.R_ROW, theme.R_ROW)

        # 复选框
        cx = row.left() + self.PAD_X
        box = QRectF(cx, row.center().y() - self.CHECK / 2, self.CHECK, self.CHECK)
        raw_state = index.data(Qt.ItemDataRole.CheckStateRole)
        checked = (raw_state is not None
                   and _enum_value(raw_state) == _enum_value(Qt.CheckState.Checked))
        if checked:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.color("accent"))
            painter.drawRoundedRect(box, 4, 4)
            _draw_check(painter, box, theme.color("accent_ink"), 1.6)
        else:
            pen_color = theme.color("accent") if hovered else theme.color("check_border")
            painter.setPen(QPen(pen_color, 1.3))
            painter.setBrush(theme.color("surface") if hovered else Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(box.adjusted(0.65, 0.65, -0.65, -0.65), 4, 4)

        # 右侧：状态字形列 + 元信息
        meta_right = row.right() - self.PAD_X
        glyph_rect = QRectF(meta_right - 14, row.center().y() - 7, 14, 14)
        state = index.data(ROLE_STATE) or "idle"

        fm_meta = QFontMetrics(self._f_meta)
        mono_color = theme.color("ink3")
        if state == "running":
            meta_text, meta_color = "转换中", theme.color("accent")
        elif state == "failed":
            meta_text, meta_color = "失败", theme.color("err")
        else:
            meta_text, meta_color = index.data(ROLE_SIZE) or "", mono_color

        meta_font = self._f_meta if state in ("running", "failed") else self._f_mono
        meta_w = QFontMetrics(meta_font).horizontalAdvance(meta_text)
        text_right = meta_right - self.GLYPH_COL - self.GAP

        painter.setFont(meta_font)
        painter.setPen(meta_color)
        painter.drawText(QRectF(text_right - meta_w, row.top(), meta_w, row.height()),
                         int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                         meta_text)

        if state == "done":
            _draw_check(painter, glyph_rect, theme.color("ok"), 1.6)
        elif state == "failed":
            _draw_cross(painter, glyph_rect, theme.color("err"), 1.5)

        # 文件名（中间省略，优先保留扩展名）
        name = index.data(Qt.ItemDataRole.DisplayRole) or ""
        name_left = box.right() + 10
        name_w = max(0.0, text_right - meta_w - self.GAP - name_left)
        painter.setFont(self._f_name)
        painter.setPen(theme.color("ink"))
        elided = QFontMetrics(self._f_name).elidedText(
            name, Qt.TextElideMode.ElideMiddle, int(name_w))
        painter.drawText(QRectF(name_left, row.top(), name_w, row.height()),
                         int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                         elided)

        # 行间发丝线（两侧内缩，避免与卡片边框贴死）
        if index.row() < (index.model().rowCount() - 1):
            from PySide6.QtCore import QPointF

            y = row.bottom() - 0.5
            painter.setPen(QPen(theme.color("line"), 1))
            painter.drawLine(QPointF(row.left() + self.PAD_X, y),
                             QPointF(row.right() - self.PAD_X, y))
        painter.restore()


class FileListWidget(QListWidget):
    """支持点选复选框、空格切换、Delete 移除的文件列表。"""

    delete_requested = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("fileList")
        self.setUniformItemSizes(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMouseTracking(True)
        self._delegate = FileRowDelegate(self)
        self.setItemDelegate(self._delegate)
        self.verticalScrollBar().setSingleStep(theme.ROW_HEIGHT)

    def refresh_theme(self) -> None:
        self._delegate.refresh()
        self.viewport().update()

    def _toggle(self, item: QListWidgetItem) -> None:
        item.setCheckState(Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked
                           else Qt.CheckState.Checked)

    def mousePressEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if item is not None and event.button() == Qt.MouseButton.LeftButton:
            rect = self.visualItemRect(item)
            if event.position().x() <= rect.left() + FileRowDelegate.PAD_X + FileRowDelegate.CHECK + 4:
                self._toggle(item)
                self.setCurrentItem(item)
                self.viewport().update()
                self.itemChanged.emit(item)
                return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        item = self.currentItem()
        if event.key() == Qt.Key.Key_Space and item is not None:
            self._toggle(item)
            self.viewport().update()
            self.itemChanged.emit(item)
            return
        if event.key() == Qt.Key.Key_Delete:
            rows = sorted((self.row(i) for i in self.selectedItems()), reverse=True)
            if rows:
                self.delete_requested.emit(rows)
            return
        super().keyPressEvent(event)


# ------------------------------------------------------------ 完成弹窗


class _CompletionDialog(QDialog):
    """完成提示：矢量徽标 + 失败清单 + 柔和进场。"""

    def __init__(self, output_dir: str, success: int, failed: list, total: int, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.setWindowTitle("转换完成")
        self.setMinimumWidth(400)
        self.setMaximumWidth(460)
        self.setModal(True)

        ok = not failed
        root = QVBoxLayout(self)
        root.setContentsMargins(theme.S5, theme.S5, theme.S5, theme.S4)
        root.setSpacing(theme.S3)

        badge_row = QHBoxLayout()
        badge_row.addStretch(1)
        badge_row.addWidget(_Badge(ok))
        badge_row.addStretch(1)
        root.addLayout(badge_row)

        title = QLabel("全部完成" if ok else "部分文件失败")
        title.setObjectName("dlgTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        if ok:
            sub_text = f"{success} 个文件已转换" + (f" · {self._short_dir(output_dir)}" if output_dir else "")
        else:
            sub_text = f"{success}/{total} 个文件转换成功"
        sub = QLabel(sub_text)
        sub.setObjectName("dlgSub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        root.addWidget(sub)

        if failed:
            scroll = QScrollArea()
            scroll.setObjectName("failScroll")
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(min(200, 12 + 44 * len(failed)))
            inner = QWidget()
            inner.setObjectName("failInner")
            box = QVBoxLayout(inner)
            box.setContentsMargins(theme.S3, theme.S2, theme.S3, theme.S2)
            box.setSpacing(theme.S2)
            for r in failed:
                line = QVBoxLayout()
                line.setSpacing(1)
                name = QLabel(os.path.basename(r["file"]))
                name.setObjectName("failName")
                _font(name, theme.F_SMALL)
                msg = QLabel(self._short_error(r.get("error") or ""))
                msg.setObjectName("failMsg")
                _font(msg, theme.F_META)
                msg.setToolTip(r.get("error") or "")
                line.addWidget(name)
                line.addWidget(msg)
                box.addLayout(line)
            box.addStretch(1)
            scroll.setWidget(inner)
            root.addWidget(scroll)

        root.addSpacing(theme.S1)
        buttons = QHBoxLayout()
        buttons.setSpacing(theme.S2)
        btn_log = QPushButton("打开日志")
        btn_log.setObjectName("link")
        btn_log.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_log.clicked.connect(self._open_log)
        buttons.addWidget(btn_log)
        buttons.addStretch(1)

        btn_close = QPushButton("关闭")
        btn_close.setObjectName("ghost")
        btn_close.setFixedHeight(32)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        buttons.addWidget(btn_close)

        if output_dir and os.path.isdir(output_dir):
            btn_open = QPushButton("打开输出目录")
            btn_open.setObjectName("primary")
            btn_open.setFixedHeight(32)
            btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open.clicked.connect(self._open_and_close)
            buttons.addWidget(btn_open)
        root.addLayout(buttons)

        _font(title, theme.F_TITLE, theme.W_MEDIUM)
        _font(sub, theme.F_SMALL)
        _font(btn_log, theme.F_META, theme.W_MEDIUM)
        _font(btn_close, theme.F_SMALL, theme.W_MEDIUM)
        if output_dir and os.path.isdir(output_dir):
            _font(btn_open, theme.F_SMALL, theme.W_MEDIUM)

        self._fade_in()

    # ---- 工具 ----

    @staticmethod
    def _short_dir(path: str, limit: int = 34) -> str:
        path = path.rstrip("\\/")
        name = os.path.basename(path) or path
        parent = os.path.basename(os.path.dirname(path))
        text = f"{parent}\\{name}" if parent else name
        return text if len(text) <= limit else "…" + text[-(limit - 1):]

    @staticmethod
    def _short_error(text: str, limit: int = 64) -> str:
        text = " ".join(text.split())
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def _fade_in(self) -> None:
        self.setWindowOpacity(0.0)
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(160)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._anim = anim

    def _open_and_close(self):
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)
        self.accept()

    def _open_log(self):
        try:
            from converter import get_log_dir
            path = get_log_dir()
            if os.path.isdir(path):
                os.startfile(path)
        except Exception:
            pass


# ------------------------------------------------------------ 主窗口


class MainWindow(QMainWindow):
    """PortableConverterMD 主窗口（Windows 上使用自绘标题栏）。"""

    RESIZE_MARGIN = 6

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PortableConverterMD")
        self.setMinimumSize(500, 360)
        if sys.platform == "win32":
            # 自绘标题栏：去掉原生边框，拖动/缩放仍交给系统（startSystemMove/Resize）
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        self._settings = settings.store()
        geom = self._settings.value("window/geometry")
        if geom is not None:
            self.restoreGeometry(geom)
        else:
            self.resize(560, 510)

        icon_path = os.path.join(get_app_dir(), "res", "PortableConverterMD.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.file_paths: list[str] = []
        self.output_dir: str = ""
        self.worker: ConvertWorker | None = None
        self._busy = False
        self._ocr_text = ""
        self._ocr_pending = False
        self._panel: SettingsPanel | None = None
        self._tray: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None
        self._tray_hint_shown = False
        self._quitting = False
        self._resize_filter: _EdgeResizeFilter | None = None
        self._maximized = False

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- 标题栏（设置按钮在左，窗口按钮在右，同一 y 轴） ----
        self.title_bar = TitleBar("PortableConverterMD")
        self.title_bar.settings_clicked.connect(self._open_settings)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.title_bar.maximize_clicked.connect(self._toggle_maximize)
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.drag_started.connect(self._start_drag)
        self.title_bar.double_clicked.connect(self._toggle_maximize)
        outer.addWidget(self.title_bar)

        body = QWidget()
        outer.addWidget(body, 1)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(theme.S4, theme.S3, theme.S4, theme.S4)
        layout.setSpacing(theme.S3)

        # 拖放区
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._add_files)
        layout.addWidget(self.drop_zone)

        # 元信息行：文件数/进度 在左，清空在右
        meta = QHBoxLayout()
        meta.setSpacing(theme.S2)
        self.lbl_status = QLabel("就绪")
        self.lbl_status.setObjectName("metaText")
        self.lbl_status.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        meta.addWidget(self.lbl_status, 1)
        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.setObjectName("link")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self._clear_files)
        self.btn_clear.setEnabled(False)
        meta.addWidget(self.btn_clear, 0, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(meta)

        # 文件列表
        self.file_list = FileListWidget()
        self.file_list.itemChanged.connect(lambda _: self._update_ui())
        self.file_list.delete_requested.connect(self._remove_rows)
        layout.addWidget(self.file_list, 1)

        # 进度轨道（常驻 3px，避免出现/消失导致布局跳动）
        self.progress = QProgressBar()
        self.progress.setObjectName("rail")
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(3)
        layout.addWidget(self.progress)

        # 底部：输出位置在左（点击打开设置），操作在右
        footer = QHBoxLayout()
        footer.setSpacing(theme.S2)
        self.lbl_output = QPushButton()
        self.lbl_output.setObjectName("link")
        self.lbl_output.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_output.clicked.connect(self._open_settings)
        footer.addWidget(self.lbl_output, 1)

        self.btn_open_dir = QPushButton("打开输出目录")
        self.btn_open_dir.setObjectName("ghost")
        self.btn_open_dir.setFixedHeight(32)
        self.btn_open_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_dir.clicked.connect(self._open_output_dir)
        self.btn_open_dir.setEnabled(False)
        footer.addWidget(self.btn_open_dir)

        self.btn_convert = QPushButton("开始转换")
        self.btn_convert.setObjectName("primary")
        self.btn_convert.setFixedHeight(32)
        self.btn_convert.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_convert.clicked.connect(self._start_conversion)
        self.btn_convert.setEnabled(False)
        self.btn_convert.setDefault(True)
        footer.addWidget(self.btn_convert)
        layout.addLayout(footer)

        self._anim = None
        _font(self.lbl_status, theme.F_META)
        _font(self.btn_clear, theme.F_META, theme.W_MEDIUM)
        _font(self.lbl_output, theme.F_META, theme.W_MEDIUM)
        _font(self.btn_open_dir, theme.F_SMALL, theme.W_MEDIUM)
        _font(self.btn_convert, theme.F_SMALL, theme.W_MEDIUM)
        self._refresh_output_label()
        self._update_ui()
        self._apply_theme()
        self._setup_tray(settings.keep_in_background())
        if sys.platform == "win32":
            self._resize_filter = _EdgeResizeFilter(self)
            app = QApplication.instance()
            if app is not None:
                app.installEventFilter(self._resize_filter)

    # ---- 主题 / 窗口 ----

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app is not None and not app.styleSheet():
            # 主程序（main.py）通常已应用主题，这里只做兜底
            try:
                theme.apply(app)
            except Exception:
                pass
        self.file_list.refresh_theme()
        self.title_bar.refresh_theme()

    def showEvent(self, event):
        super().showEvent(event)
        theme.apply_titlebar(self)
        theme.style_window(self)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            maximized = self.isMaximized()
            if maximized != self._maximized:
                self._maximized = maximized
                self.title_bar.set_maximized(maximized)

    def closeEvent(self, event):
        # 「关闭窗口后继续运行」：隐藏到托盘而不是退出
        if (settings.keep_in_background() and not self._quitting
                and self._tray is not None and self._tray.isVisible()):
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self._tray.showMessage(
                    "PortableConverterMD 仍在后台运行",
                    "点击托盘图标可重新打开，或右键托盘图标选择退出。",
                    QSystemTrayIcon.MessageIcon.Information, 4000)
            return
        try:
            self._settings.setValue("window/geometry", self.saveGeometry())
        except Exception:
            pass
        if self._resize_filter is not None:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self._resize_filter)
            self._resize_filter = None
        super().closeEvent(event)

    def _start_drag(self) -> None:
        if self.isMaximized():
            return
        handle = self.windowHandle()
        if handle is not None:
            handle.startSystemMove()

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # ---- 托盘（后台常开） ----

    def _setup_tray(self, enabled: bool) -> None:
        if enabled and QSystemTrayIcon.isSystemTrayAvailable():
            if self._tray is None:
                tray = QSystemTrayIcon(self.windowIcon(), self)
                menu = QMenu()
                act_show = menu.addAction("显示主窗口")
                act_show.triggered.connect(self._show_from_tray)
                act_settings = menu.addAction("设置…")
                act_settings.triggered.connect(self._open_settings)
                menu.addSeparator()
                act_quit = menu.addAction("退出")
                act_quit.triggered.connect(self._quit)
                tray.setContextMenu(menu)
                tray.setToolTip("PortableConverterMD")
                tray.activated.connect(self._on_tray_activated)
                tray.show()
                self._tray = tray
                self._tray_menu = menu      # setContextMenu 不接管所有权
        elif self._tray is not None:
            self._tray.hide()
            self._tray.deleteLater()
            self._tray = None
            self._tray_menu = None
            self._tray_hint_shown = False

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        if self._busy:
            answer = QMessageBox.question(
                self, "正在转换", "还有文件正在转换，确定退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._quitting = True
        if self._tray is not None:
            self._tray.hide()
        QApplication.quit()

    # ---- 设置面板 ----

    def _open_settings(self) -> None:
        if self._panel is None:
            panel = SettingsPanel(self)
            panel.output_mode_changed.connect(lambda _mode: self._refresh_output_label())
            panel.custom_dir_changed.connect(lambda _p: self._refresh_output_label())
            panel.keep_in_background_changed.connect(self._setup_tray)
            panel.output_mode_changed.connect(lambda _m: self._update_ui())
            self._panel = panel
        self._panel.popup_at(self.title_bar.btn_settings)

    # ---- 文件管理 ----

    def _add_files(self, paths: list[str]) -> None:
        """加入文件；目录会展开一层（按支持格式过滤），最多 BATCH_LIMIT 个。"""
        import engine

        expanded: list[str] = []
        for path in paths:
            if os.path.isdir(path):
                try:
                    for name in sorted(os.listdir(path)):
                        full = os.path.join(path, name)
                        if os.path.isfile(full) and engine.supports(full):
                            expanded.append(full)
                except OSError:
                    continue
            else:
                expanded.append(path)

        added = 0
        for path in expanded:
            if len(self.file_paths) >= BATCH_LIMIT:
                break
            if path in self.file_paths or not os.path.isfile(path):
                continue
            self.file_paths.append(path)
            item = QListWidgetItem(os.path.basename(path))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(ROLE_STATE, "idle")
            try:
                item.setData(ROLE_SIZE, _human_size(os.path.getsize(path)))
            except OSError:
                item.setData(ROLE_SIZE, "")
            item.setToolTip(path)
            self.file_list.addItem(item)
            added += 1

        if added:
            self.lbl_status.setText(self._summary_text())
        self._update_ui()

    def _remove_rows(self, rows: list[int]) -> None:
        for row in rows:
            if 0 <= row < len(self.file_paths):
                self.file_paths.pop(row)
                self.file_list.takeItem(row)
        self._update_ui()

    def _clear_files(self) -> None:
        self.file_list.clear()
        self.file_paths.clear()
        self._update_ui()

    def _summary_text(self) -> str:
        total_size = 0
        for path in self.file_paths:
            try:
                total_size += os.path.getsize(path)
            except OSError:
                pass
        return f"{len(self.file_paths)} 个文件 · {_human_size(total_size)}"

    def _refresh_output_label(self) -> None:
        custom = settings.custom_dir()
        if custom:
            text = custom
            if len(text) > 34:
                text = "…" + text[-33:]
            self.lbl_output.setText(f"输出：{text}")
            self.lbl_output.setToolTip(f"{custom}\n（点击打开设置）")
        else:
            self.lbl_output.setText(f"输出：{settings.mode_label()}")
            self.lbl_output.setToolTip("点击打开设置，可切换输出位置/开机启动/后台常驻/日志")

    def _update_ui(self) -> None:
        count = self.file_list.count()
        has_files = count > 0
        self.btn_clear.setEnabled(has_files)
        self.btn_convert.setEnabled(has_files and not self._busy)
        self.btn_open_dir.setEnabled(bool(self.output_dir) and os.path.isdir(self.output_dir))
        self.drop_zone.set_compact(has_files)
        self.file_list.setVisible(has_files)
        self.progress.setVisible(has_files)
        if has_files and not self._busy:
            self.lbl_status.setText(self._summary_text())
        elif not has_files:
            # OCR 探测要加载 winrt，放到首帧之后再跑，不拖慢窗口出现
            self.lbl_status.setText("就绪")
            self._schedule_ocr_label()

    def _schedule_ocr_label(self) -> None:
        if self._ocr_pending or self._ocr_text:
            return
        self._ocr_pending = True
        QTimer.singleShot(0, self._fill_ocr_label)

    def _fill_ocr_label(self) -> None:
        self._ocr_text = self._ocr_label()
        self._ocr_pending = False
        if not self.file_paths:
            self.lbl_status.setText(f"就绪 · OCR：{self._ocr_text}")

    @staticmethod
    def _ocr_label() -> str:
        try:
            return ocr_backend_label()
        except Exception:
            return "未知"

    # ---- 转换 ----

    def _get_checked_items(self) -> list:
        items = []
        for i in range(self.file_list.count()):
            if self.file_list.item(i).checkState() == Qt.CheckState.Checked:
                items.append((i, self.file_paths[i]))
        return items

    def _start_conversion(self) -> None:
        checked = self._get_checked_items()
        if not checked:
            QMessageBox.information(self, "提示", "没有勾选任何文件。")
            return

        # 「打开输出目录」按钮的目标：自定义目录，或第一个文件按当前设置算出的目录
        first_path = checked[0][1]
        self.output_dir = settings.output_dir_for(first_path)

        self.btn_convert.setEnabled(False)
        self.btn_open_dir.setEnabled(False)
        self.drop_zone.setEnabled(False)
        self._busy = True
        self.progress.setRange(0, len(checked))
        self._set_progress(0)

        # output_dir 传空 => 每个文件按设置各自计算输出目录
        self.worker = ConvertWorker(checked, settings.custom_dir())
        self.worker.file_started.connect(self._on_file_started)
        self.worker.file_finished.connect(self._on_file_finished)
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.conversion_done.connect(self._on_done)
        self.worker.start()

    def _set_progress(self, value: int) -> None:
        """让进度条平滑过渡，而不是生硬跳变。"""
        anim = QPropertyAnimation(self.progress, b"value", self)
        anim.setDuration(180)
        anim.setStartValue(self.progress.value())
        anim.setEndValue(value)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._anim = anim

    def _on_file_started(self, row: int, fname: str) -> None:
        item = self.file_list.item(row)
        if item is not None:
            item.setData(ROLE_STATE, "running")
            self.file_list.scrollToItem(item)
        total = self.progress.maximum()
        done = sum(1 for i in range(self.file_list.count())
                   if self.file_list.item(i).data(ROLE_STATE) in ("done", "failed"))
        self.lbl_status.setText(f"正在处理 {done + 1}/{total} · {fname}")
        self.file_list.viewport().update()

    def _on_file_finished(self, row: int, success: bool, error: str) -> None:
        item = self.file_list.item(row)
        if item is None:
            return
        item.setData(ROLE_STATE, "done" if success else "failed")
        item.setToolTip(error if not success else self.file_paths[row])
        self.file_list.viewport().update()

    def _on_progress(self, current: int, total: int) -> None:
        self._set_progress(current)

    def _on_done(self, results: list) -> None:
        success = sum(1 for r in results if r["output"] is not None)
        failed = [r for r in results if r["output"] is None]
        total = len(results)

        # 注意：不要在这里把 self.worker 置空——那会在信号回调中丢掉 worker 的最后一个
        # 引用，导致本次 emit 的其余槽（如测试监听）收不到 conversion_done。
        self._busy = False
        self.drop_zone.setEnabled(True)
        self.btn_open_dir.setEnabled(bool(self.output_dir) and os.path.isdir(self.output_dir))
        self.lbl_status.setText(f"完成 {success}/{total} · 全部成功" if not failed
                                else f"完成 {success}/{total} · {len(failed)} 个失败")
        self._update_ui()

        # 在托盘后台运行时，用系统通知告知结果，不打断用户
        if self._tray is not None and not self.isVisible():
            self._tray.showMessage(
                "转换完成" if not failed else "部分文件转换失败",
                f"{success}/{total} 个文件已转换",
                QSystemTrayIcon.MessageIcon.Information if not failed
                else QSystemTrayIcon.MessageIcon.Warning, 4000)
            return

        dlg = _CompletionDialog(self.output_dir, success, failed, total, self)
        dlg.exec()

    def _open_output_dir(self) -> None:
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)


# ------------------------------------------------------------ 无边框缩放

class _EdgeResizeFilter(QObject):
    """无边框窗口的边缘缩放：命中窗口外框 6px 时交给系统处理。

    用 QApplication 级事件过滤器，因为窗口边缘的鼠标事件会落在子控件上。
    """

    def __init__(self, window: MainWindow, margin: int = MainWindow.RESIZE_MARGIN):
        super().__init__(window)
        self.win = window
        self.margin = margin
        self._cursor = None

    def _edges_at(self, pos) -> Qt.Edge:
        m = self.margin
        w, h = self.win.width(), self.win.height()
        edges = Qt.Edge(0)
        if pos.x() < m:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= w - m:
            edges |= Qt.Edge.RightEdge
        if pos.y() < m:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= h - m:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _set_cursor(self, edges: Qt.Edge) -> None:
        if edges == self._cursor:
            return
        self._cursor = edges
        cursor = Qt.CursorShape.ArrowCursor
        if edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
            cursor = Qt.CursorShape.SizeHorCursor
        elif edges in (Qt.Edge.TopEdge, Qt.Edge.BottomEdge):
            cursor = Qt.CursorShape.SizeVerCursor
        elif edges in (Qt.Edge.LeftEdge | Qt.Edge.TopEdge,
                       Qt.Edge.RightEdge | Qt.Edge.BottomEdge):
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif edges in (Qt.Edge.RightEdge | Qt.Edge.TopEdge,
                       Qt.Edge.LeftEdge | Qt.Edge.BottomEdge):
            cursor = Qt.CursorShape.SizeBDiagCursor
        self.win.setCursor(cursor)

    def eventFilter(self, obj, event) -> bool:
        try:
            win = self.win
            if win is None or not win.isVisible() or win.isMaximized():
                return False
            etype = event.type()
            if etype not in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress):
                return False
            global_pos = event.globalPosition().toPoint()
            pos = win.mapFromGlobal(global_pos)
            inside = win.rect().contains(pos)
            if etype == QEvent.Type.MouseMove:
                self._set_cursor(self._edges_at(pos) if inside else Qt.Edge(0))
                return False
            if inside and event.button() == Qt.MouseButton.LeftButton:
                edges = self._edges_at(pos)
                if edges:
                    handle = win.windowHandle()
                    if handle is not None:
                        handle.startSystemResize(edges)
                    return True
        except RuntimeError:
            # 窗口已被销毁（解释器退出阶段的残留事件）
            return False
        return False

    def _open_output_dir(self) -> None:
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)
