"""
supaDraw Screen Curtain (Perdeleme)
────────────────────────────────────
Screen masking feature to help students focus on specific content areas.
"""

from PyQt5.QtCore import Qt, QPoint, QRect, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QCursor
from PyQt5.QtWidgets import QWidget


class CurtainMode:
    """Curtain display modes."""
    OFF = "off"
    FULL = "full"           # Full curtain — drag edge to reveal
    SPOTLIGHT = "spotlight"  # Circular spotlight around cursor


class CurtainOverlay(QWidget):
    """
    Screen curtain/masking overlay.
    Covers the screen with a dark layer and provides
    reveal mechanisms for focused content viewing.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = CurtainMode.OFF
        self.opacity_level = 0.85

        # Full curtain mode
        self.reveal_rect = QRect(0, 0, 0, 0)
        self.dragging_edge = None  # "top", "bottom", "left", "right"
        self.drag_start = QPoint()

        # Spotlight mode
        self.spotlight_radius = 120
        self.spotlight_pos = QPoint(400, 300)

        self.setMouseTracking(True)
        self.hide()  # Hidden by default

    def set_mode(self, mode: str):
        """Switch curtain mode."""
        self.mode = mode
        if mode == CurtainMode.OFF:
            self.hide()
        else:
            if mode == CurtainMode.FULL:
                # Start with curtain covering bottom half
                parent = self.parent()
                if parent:
                    w, h = parent.width(), parent.height()
                    self.reveal_rect = QRect(0, 0, w, h // 3)
            self.show()
            self.raise_()
            self.update()

    def toggle(self):
        """Cycle through curtain modes: OFF → FULL → SPOTLIGHT → OFF."""
        if self.mode == CurtainMode.OFF:
            self.set_mode(CurtainMode.FULL)
        elif self.mode == CurtainMode.FULL:
            self.set_mode(CurtainMode.SPOTLIGHT)
        else:
            self.set_mode(CurtainMode.OFF)

    def paintEvent(self, event):
        """Paint the curtain overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.mode == CurtainMode.FULL:
            self._paint_full_curtain(painter)
        elif self.mode == CurtainMode.SPOTLIGHT:
            self._paint_spotlight(painter)

        painter.end()

    def _paint_full_curtain(self, painter: QPainter):
        """Paint full curtain with reveal area."""
        w, h = self.width(), self.height()
        dark = QColor(0, 0, 0, int(255 * self.opacity_level))

        # Paint dark areas around the reveal rect
        r = self.reveal_rect

        # Top region
        if r.top() > 0:
            painter.fillRect(0, 0, w, r.top(), dark)
        # Bottom region
        if r.bottom() < h:
            painter.fillRect(0, r.bottom(), w, h - r.bottom(), dark)
        # Left region
        if r.left() > 0:
            painter.fillRect(0, r.top(), r.left(), r.height(), dark)
        # Right region
        if r.right() < w:
            painter.fillRect(r.right(), r.top(), w - r.right(), r.height(), dark)

        # Draw reveal border
        border_pen = QPen(QColor("#f5a623"), 3)
        painter.setPen(border_pen)
        painter.drawRect(r)

        # Draw drag handles on edges
        handle_color = QColor("#f5a623")
        painter.setBrush(handle_color)
        painter.setPen(Qt.NoPen)
        handle_size = 12

        # Bottom handle
        painter.drawEllipse(
            r.center().x() - handle_size // 2,
            r.bottom() - handle_size // 2,
            handle_size, handle_size
        )
        # Right handle
        painter.drawEllipse(
            r.right() - handle_size // 2,
            r.center().y() - handle_size // 2,
            handle_size, handle_size
        )

    def _paint_spotlight(self, painter: QPainter):
        """Paint spotlight mode with circular reveal."""
        w, h = self.width(), self.height()

        # Dark overlay everywhere
        dark = QColor(0, 0, 0, int(255 * self.opacity_level))
        painter.fillRect(0, 0, w, h, dark)

        # Cut out spotlight circle with gradient edge
        painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        gradient = QRadialGradient(
            self.spotlight_pos.x(), self.spotlight_pos.y(),
            self.spotlight_radius
        )
        gradient.setColorAt(0.0, QColor(0, 0, 0, 255))
        gradient.setColorAt(0.75, QColor(0, 0, 0, 255))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            self.spotlight_pos,
            self.spotlight_radius,
            self.spotlight_radius
        )
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

    def mousePressEvent(self, event):
        """Handle edge dragging for curtain reveal."""
        if self.mode == CurtainMode.FULL:
            pos = event.pos()
            r = self.reveal_rect
            margin = 20

            if abs(pos.y() - r.bottom()) < margin and r.left() < pos.x() < r.right():
                self.dragging_edge = "bottom"
            elif abs(pos.x() - r.right()) < margin and r.top() < pos.y() < r.bottom():
                self.dragging_edge = "right"
            elif abs(pos.y() - r.top()) < margin and r.left() < pos.x() < r.right():
                self.dragging_edge = "top"
            elif abs(pos.x() - r.left()) < margin and r.top() < pos.y() < r.bottom():
                self.dragging_edge = "left"
            else:
                self.dragging_edge = None

            self.drag_start = pos

    def mouseMoveEvent(self, event):
        """Handle dragging and spotlight following."""
        pos = event.pos()

        if self.mode == CurtainMode.SPOTLIGHT:
            self.spotlight_pos = pos
            self.update()
            return

        if self.mode == CurtainMode.FULL and self.dragging_edge:
            r = self.reveal_rect
            if self.dragging_edge == "bottom":
                r.setBottom(max(r.top() + 50, pos.y()))
            elif self.dragging_edge == "right":
                r.setRight(max(r.left() + 50, pos.x()))
            elif self.dragging_edge == "top":
                r.setTop(min(r.bottom() - 50, pos.y()))
            elif self.dragging_edge == "left":
                r.setLeft(min(r.right() - 50, pos.x()))
            self.reveal_rect = r
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging_edge = None

    def wheelEvent(self, event):
        """Adjust spotlight radius with scroll wheel."""
        if self.mode == CurtainMode.SPOTLIGHT:
            delta = event.angleDelta().y()
            self.spotlight_radius += delta / 5
            self.spotlight_radius = max(50, min(500, self.spotlight_radius))
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)
