"""
supaDraw Drawing Canvas
────────────────────────
Transparent overlay widget that handles all drawing operations.
Supports pens, shapes, undo/redo, and multi-page management.
"""

import math
from PyQt5.QtCore import (
    Qt, QPointF, QRectF, QLineF, QTimer, pyqtSignal
)
from PyQt5.QtGui import (
    QPainter, QPen, QColor, QBrush, QPainterPath,
    QPixmap, QCursor, QPolygonF, QFont
)
from PyQt5.QtWidgets import QWidget

from src.tools import (
    ToolType, BackgroundType, Stroke, Page,
    TOOL_DEFAULTS, DEFAULT_COLORS
)
from src.backgrounds import draw_background


class DrawingCanvas(QWidget):
    """
    Full-screen transparent drawing surface.
    Handles stroke input, shape drawing, and page management.
    """

    # ── Signals ──────────────────────────────────────────────────
    tool_changed = pyqtSignal(ToolType)
    color_changed = pyqtSignal(QColor)
    page_changed = pyqtSignal(int, int)  # current, total

    # ── Constants ────────────────────────────────────────────────
    SMOOTHING_FACTOR = 0.3
    MIN_SHAPE_SIZE = 10

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Drawing state ────────────────────────────────────────
        self.current_tool = ToolType.PEN
        self.current_color = QColor("#1a1a2e")
        self.current_width = 3.0
        self.current_opacity = 1.0

        # ── Pages ────────────────────────────────────────────────
        self.pages = [Page()]
        self.current_page_idx = 0

        # ── Active stroke tracking ───────────────────────────────
        self.drawing = False
        self.current_stroke = None
        self.shape_start = None
        self.shape_preview_end = None

        # ── Desktop (click-through) mode ─────────────────────────
        self.desktop_mode = False

        # ── Widget setup ─────────────────────────────────────────
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)  # Accept keyboard focus

    # ── Properties ───────────────────────────────────────────────

    @property
    def page(self) -> Page:
        return self.pages[self.current_page_idx]

    # ── Tool Selection ───────────────────────────────────────────

    def set_tool(self, tool: ToolType):
        """Switch the active drawing tool."""
        self.current_tool = tool
        defaults = TOOL_DEFAULTS.get(tool, {})
        self.current_width = defaults.get("width", 3.0)
        self.current_opacity = defaults.get("opacity", 1.0)

        # Eraser uses white on non-transparent backgrounds
        if tool == ToolType.ERASER:
            if self.page.background != BackgroundType.NONE:
                self.current_color = QColor("#f8f9fa")

        self.tool_changed.emit(tool)
        self.update()

    def set_color(self, color: QColor):
        """Set the drawing color."""
        self.current_color = color
        self.color_changed.emit(color)

    def set_width(self, width: float):
        """Set the pen width."""
        self.current_width = max(1.0, min(80.0, width))

    # ── Background / Page Management ─────────────────────────────

    def set_background(self, bg: BackgroundType):
        """Change the current page background."""
        self.page.background = bg
        self.update()

    def add_page(self):
        """Add a new blank page after the current one."""
        new_page = Page(background=self.page.background)
        self.current_page_idx += 1
        self.pages.insert(self.current_page_idx, new_page)
        self.page_changed.emit(self.current_page_idx + 1, len(self.pages))
        self.update()

    def prev_page(self):
        """Navigate to the previous page."""
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.page_changed.emit(self.current_page_idx + 1, len(self.pages))
            self.update()

    def next_page(self):
        """Navigate to the next page."""
        if self.current_page_idx < len(self.pages) - 1:
            self.current_page_idx += 1
            self.page_changed.emit(self.current_page_idx + 1, len(self.pages))
            self.update()

    # ── Undo / Redo ──────────────────────────────────────────────

    def undo(self):
        """Undo the last stroke."""
        page = self.page
        if page.strokes:
            page.undo_stack.append(page.strokes.copy())
            page.strokes = page.strokes[:-1]
            self.update()

    def redo(self):
        """Redo the last undone action."""
        page = self.page
        if page.undo_stack:
            # The undo_stack stores the full strokes list before the undo
            last_state = page.undo_stack.pop()
            if len(last_state) > len(page.strokes):
                page.strokes = last_state
                self.update()

    def clear_page(self):
        """Clear all strokes on the current page."""
        page = self.page
        if page.strokes:
            page.undo_stack.append(page.strokes.copy())
            page.strokes = []
            self.update()

    # ── Desktop Mode Toggle ──────────────────────────────────────

    def toggle_desktop_mode(self):
        """Toggle click-through desktop mode."""
        self.desktop_mode = not self.desktop_mode
        if self.desktop_mode:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._update_cursor()

    # ── Mouse Events ─────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        pos = event.pos()

        if self.current_tool == ToolType.CURSOR:
            return

        # Shape tools
        if self.current_tool in (ToolType.LINE, ToolType.RECTANGLE,
                                  ToolType.CIRCLE, ToolType.ARROW):
            self.shape_start = QPointF(pos)
            self.shape_preview_end = QPointF(pos)
            self.drawing = True
            return

        # Eraser — area erasing
        if self.current_tool == ToolType.ERASER:
            self._erase_at(QPointF(pos))
            self.drawing = True
            return

        # Pen / Highlighter / Chisel
        self.drawing = True
        color = QColor(self.current_color)
        self.current_stroke = Stroke(
            points=[QPointF(pos)],
            color=color,
            width=self.current_width,
            tool=self.current_tool,
            opacity=self.current_opacity,
        )

    def mouseMoveEvent(self, event):
        if not self.drawing:
            return

        pos = event.pos()

        # Shape preview
        if self.current_tool in (ToolType.LINE, ToolType.RECTANGLE,
                                  ToolType.CIRCLE, ToolType.ARROW):
            self.shape_preview_end = QPointF(pos)
            self.update()
            return

        # Eraser dragging
        if self.current_tool == ToolType.ERASER:
            self._erase_at(QPointF(pos))
            return

        # Stroke drawing with smoothing
        if self.current_stroke:
            last = self.current_stroke.points[-1]
            smoothed = QPointF(
                last.x() + (pos.x() - last.x()) * (1 - self.SMOOTHING_FACTOR),
                last.y() + (pos.y() - last.y()) * (1 - self.SMOOTHING_FACTOR),
            )
            self.current_stroke.points.append(smoothed)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        if not self.drawing:
            return

        self.drawing = False
        page = self.page

        # Finalize shape
        if self.current_tool in (ToolType.LINE, ToolType.RECTANGLE,
                                  ToolType.CIRCLE, ToolType.ARROW):
            if self.shape_start and self.shape_preview_end:
                stroke = Stroke(
                    color=QColor(self.current_color),
                    width=self.current_width,
                    tool=self.current_tool,
                    opacity=self.current_opacity,
                    start_point=self.shape_start,
                    end_point=self.shape_preview_end,
                )
                page.strokes.append(stroke)
                page.redo_stack.clear()
            self.shape_start = None
            self.shape_preview_end = None
            self.update()
            return

        # Finalize stroke
        if self.current_stroke and len(self.current_stroke.points) > 1:
            page.strokes.append(self.current_stroke)
            page.redo_stack.clear()

        self.current_stroke = None
        self.update()

    # ── Eraser Logic ─────────────────────────────────────────────

    def _erase_at(self, pos: QPointF):
        """Remove strokes near the given position."""
        page = self.page
        eraser_radius = self.current_width
        remaining = []

        for stroke in page.strokes:
            if stroke.start_point and stroke.end_point:
                # Shape — check distance to bounding area
                mid = QPointF(
                    (stroke.start_point.x() + stroke.end_point.x()) / 2,
                    (stroke.start_point.y() + stroke.end_point.y()) / 2,
                )
                dist = math.hypot(pos.x() - mid.x(), pos.y() - mid.y())
                if dist > eraser_radius * 2:
                    remaining.append(stroke)
            else:
                # Freehand stroke — check if any point is near
                hit = False
                for pt in stroke.points:
                    dist = math.hypot(pos.x() - pt.x(), pos.y() - pt.y())
                    if dist < eraser_radius:
                        hit = True
                        break
                if not hit:
                    remaining.append(stroke)

        if len(remaining) < len(page.strokes):
            page.undo_stack.append(page.strokes.copy())
            page.strokes = remaining
            self.update()

    # ── Painting ─────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = QRectF(self.rect())
        page = self.page

        # CRITICAL: macOS does not deliver mouse events to fully
        # transparent window regions. We paint a barely-visible fill
        # (alpha=1 out of 255) so the OS registers this as clickable.
        if page.background == BackgroundType.NONE:
            painter.fillRect(rect, QColor(0, 0, 0, 1))
        
        # Draw background
        draw_background(painter, rect, page.background)

        # Draw committed strokes
        for stroke in page.strokes:
            self._paint_stroke(painter, stroke)

        # Draw active stroke
        if self.current_stroke and len(self.current_stroke.points) > 1:
            self._paint_stroke(painter, self.current_stroke)

        # Draw shape preview
        if self.drawing and self.shape_start and self.shape_preview_end:
            preview = Stroke(
                color=QColor(self.current_color),
                width=self.current_width,
                tool=self.current_tool,
                opacity=self.current_opacity * 0.6,
                start_point=self.shape_start,
                end_point=self.shape_preview_end,
            )
            self._paint_stroke(painter, preview)

        # Draw eraser cursor
        if self.current_tool == ToolType.ERASER and not self.desktop_mode:
            cursor_pos = self.mapFromGlobal(QCursor.pos())
            painter.setPen(QPen(QColor(200, 200, 200, 150), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(cursor_pos, int(self.current_width), int(self.current_width))

        # Page indicator
        if len(self.pages) > 1:
            self._paint_page_indicator(painter)

        painter.end()

    def _paint_stroke(self, painter: QPainter, stroke: Stroke):
        """Render a single stroke or shape."""
        color = QColor(stroke.color)
        color.setAlphaF(stroke.opacity)

        pen = QPen(color, stroke.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

        # ── Shapes ───────────────────────────────────────────────
        if stroke.start_point and stroke.end_point:
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            s, e = stroke.start_point, stroke.end_point

            if stroke.tool == ToolType.LINE:
                painter.drawLine(s, e)

            elif stroke.tool == ToolType.RECTANGLE:
                painter.drawRect(QRectF(s, e).normalized())

            elif stroke.tool == ToolType.CIRCLE:
                painter.drawEllipse(QRectF(s, e).normalized())

            elif stroke.tool == ToolType.ARROW:
                self._draw_arrow(painter, pen, s, e)

            return

        # ── Freehand Strokes ─────────────────────────────────────
        if len(stroke.points) < 2:
            return

        if stroke.tool == ToolType.CHISEL:
            # Chisel pen — angled flat tip
            self._paint_chisel(painter, stroke, color)
        elif stroke.tool == ToolType.HIGHLIGHTER:
            # Highlighter — wide, semi-transparent
            pen.setCapStyle(Qt.FlatCap)
            pen.setJoinStyle(Qt.BevelJoin)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(stroke.points[0])
            for pt in stroke.points[1:]:
                path.lineTo(pt)
            painter.drawPath(path)
        else:
            # Standard pen — smooth Bézier curves
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(stroke.points[0])

            if len(stroke.points) == 2:
                path.lineTo(stroke.points[1])
            else:
                for i in range(1, len(stroke.points) - 1):
                    mid = QPointF(
                        (stroke.points[i].x() + stroke.points[i + 1].x()) / 2,
                        (stroke.points[i].y() + stroke.points[i + 1].y()) / 2,
                    )
                    path.quadTo(stroke.points[i], mid)
                path.lineTo(stroke.points[-1])

            painter.drawPath(path)

    def _paint_chisel(self, painter: QPainter, stroke: Stroke, color: QColor):
        """Paint chisel/calligraphy pen with angled flat tip."""
        angle = math.radians(45)
        half_w = stroke.width * 0.7

        for i in range(len(stroke.points) - 1):
            p1 = stroke.points[i]
            p2 = stroke.points[i + 1]

            dx = math.cos(angle) * half_w
            dy = math.sin(angle) * half_w

            poly = QPolygonF([
                QPointF(p1.x() - dx, p1.y() - dy),
                QPointF(p1.x() + dx, p1.y() + dy),
                QPointF(p2.x() + dx, p2.y() + dy),
                QPointF(p2.x() - dx, p2.y() - dy),
            ])

            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawPolygon(poly)

    def _draw_arrow(self, painter: QPainter, pen: QPen, start: QPointF, end: QPointF):
        """Draw a line with an arrowhead at the end."""
        painter.drawLine(start, end)

        # Arrowhead
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        arrow_len = max(15, pen.widthF() * 4)
        a1 = angle + math.radians(150)
        a2 = angle - math.radians(150)

        p1 = QPointF(end.x() + arrow_len * math.cos(a1),
                      end.y() + arrow_len * math.sin(a1))
        p2 = QPointF(end.x() + arrow_len * math.cos(a2),
                      end.y() + arrow_len * math.sin(a2))

        painter.setBrush(pen.color())
        painter.drawPolygon(QPolygonF([end, p1, p2]))

    def _paint_page_indicator(self, painter: QPainter):
        """Paint a small page number indicator at the bottom."""
        text = f"{self.current_page_idx + 1} / {len(self.pages)}"
        font = QFont("Helvetica Neue", 11)
        painter.setFont(font)

        # Background pill
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text) + 20
        th = fm.height() + 10
        x = self.width() // 2 - tw // 2
        y = self.height() - th - 10

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.drawRoundedRect(x, y, tw, th, th // 2, th // 2)

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(x, y, tw, th, Qt.AlignCenter, text)

    def _update_cursor(self):
        """Update cursor based on current tool."""
        if self.current_tool == ToolType.ERASER:
            self.setCursor(Qt.CrossCursor)
        elif self.current_tool == ToolType.CURSOR:
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    # ── Keyboard Shortcuts ───────────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()
        mod = event.modifiers()

        # Ctrl+Z — Undo
        if key == Qt.Key_Z and mod & Qt.ControlModifier:
            self.undo()
            return

        # Ctrl+Y — Redo
        if key == Qt.Key_Y and mod & Qt.ControlModifier:
            self.redo()
            return

        # Ctrl+Shift+Z — Redo (alternative)
        if key == Qt.Key_Z and mod & Qt.ControlModifier and mod & Qt.ShiftModifier:
            self.redo()
            return

        # Delete / Backspace — clear page
        if key in (Qt.Key_Delete, Qt.Key_Backspace) and mod & Qt.ControlModifier:
            self.clear_page()
            return

        # Digit keys for quick color switching
        if Qt.Key_1 <= key <= Qt.Key_9:
            idx = key - Qt.Key_1
            if idx < len(DEFAULT_COLORS):
                self.set_color(DEFAULT_COLORS[idx])
            return

        # +/- for pen size
        if key == Qt.Key_Plus or key == Qt.Key_Equal:
            self.set_width(self.current_width + 2)
            return
        if key == Qt.Key_Minus:
            self.set_width(self.current_width - 2)
            return

        super().keyPressEvent(event)

    def wheelEvent(self, event):
        """Scroll to change pen width."""
        delta = event.angleDelta().y()
        self.set_width(self.current_width + delta / 60)
        event.accept()
