"""
supaDraw Background Renderer
─────────────────────────────
Paints various background patterns for different lesson contexts.
"""

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from src.tools import BackgroundType


def draw_background(painter: QPainter, rect: QRectF, bg_type: BackgroundType):
    """Draw the specified background pattern on the given rect."""

    if bg_type == BackgroundType.NONE:
        return  # Transparent — nothing to draw

    if bg_type == BackgroundType.WHITE:
        painter.fillRect(rect, QColor("#f8f9fa"))
        return

    if bg_type == BackgroundType.BLACKBOARD:
        _draw_blackboard(painter, rect)
        return

    if bg_type == BackgroundType.GRID:
        painter.fillRect(rect, QColor("#ffffff"))
        _draw_grid(painter, rect, spacing=40)
        return

    if bg_type == BackgroundType.LINED:
        painter.fillRect(rect, QColor("#fffef5"))
        _draw_lines(painter, rect, spacing=36)
        return

    if bg_type == BackgroundType.DOTTED:
        painter.fillRect(rect, QColor("#fafafa"))
        _draw_dots(painter, rect, spacing=30)
        return


def _draw_grid(painter: QPainter, rect: QRectF, spacing: int = 40):
    """Draw a math-style grid."""
    pen = QPen(QColor("#d0d4dc"), 0.8)
    painter.setPen(pen)

    x = rect.left()
    while x <= rect.right():
        painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
        x += spacing

    y = rect.top()
    while y <= rect.bottom():
        painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
        y += spacing

    # Bold lines every 5 cells
    bold_pen = QPen(QColor("#a8afc0"), 1.5)
    painter.setPen(bold_pen)
    x = rect.left()
    i = 0
    while x <= rect.right():
        if i % 5 == 0:
            painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
        x += spacing
        i += 1

    y = rect.top()
    i = 0
    while y <= rect.bottom():
        if i % 5 == 0:
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
        y += spacing
        i += 1


def _draw_lines(painter: QPainter, rect: QRectF, spacing: int = 36):
    """Draw notebook-style horizontal lines."""
    pen = QPen(QColor("#c8d8e8"), 1.0)
    painter.setPen(pen)

    # Red margin line
    margin_x = rect.left() + 80
    margin_pen = QPen(QColor("#e8a0a0"), 1.2)
    painter.setPen(margin_pen)
    painter.drawLine(int(margin_x), int(rect.top()), int(margin_x), int(rect.bottom()))

    # Horizontal lines
    painter.setPen(pen)
    y = rect.top() + 60  # Start after header area
    while y <= rect.bottom():
        painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
        y += spacing


def _draw_dots(painter: QPainter, rect: QRectF, spacing: int = 30):
    """Draw engineering-style dot grid."""
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#c0c4cc"))

    x = rect.left() + spacing
    while x <= rect.right():
        y = rect.top() + spacing
        while y <= rect.bottom():
            painter.drawEllipse(int(x) - 1, int(y) - 1, 3, 3)
            y += spacing
        x += spacing


def _draw_blackboard(painter: QPainter, rect: QRectF):
    """Draw a classic chalkboard background."""
    # Dark green background
    painter.fillRect(rect, QColor("#1a3a2a"))

    # Subtle texture lines
    pen = QPen(QColor(255, 255, 255, 8), 0.5)
    painter.setPen(pen)
    y = rect.top()
    while y <= rect.bottom():
        painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
        y += 3

    # Wooden frame border
    frame_pen = QPen(QColor("#5c3a1e"), 8)
    painter.setPen(frame_pen)
    painter.drawRect(rect.adjusted(4, 4, -4, -4))

    # Inner frame highlight
    inner_pen = QPen(QColor("#8b6914"), 2)
    painter.setPen(inner_pen)
    painter.drawRect(rect.adjusted(10, 10, -10, -10))
