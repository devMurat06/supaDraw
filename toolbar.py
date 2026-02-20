"""
supaDraw Floating Toolbar
──────────────────────────
Movable, compact floating toolbar with tool selection, color picker,
quick-access bar, and page/curtain controls.
"""


from functools import partial
from PyQt5.QtCore import (
    Qt, QPoint, QSize, QTimer, QPropertyAnimation,
    QEasingCurve, pyqtSignal, QRect
)
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QIcon, QPixmap, QPainterPath, QLinearGradient,
    QCursor, QRegion
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSlider, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QColorDialog,
    QMenu, QAction
)

from src.tools import ToolType, BackgroundType, DEFAULT_COLORS


# ═══════════════════════════════════════════════════════════════════
#  STYLED TOOL BUTTON
# ═══════════════════════════════════════════════════════════════════

class ToolButton(QPushButton):
    """A circular tool button with icon/emoji and selection state."""

    long_pressed = pyqtSignal(str)  # tool name for quick-access customization

    def __init__(self, text: str, tool_id: str = "", parent=None):
        super().__init__(text, parent)
        self.tool_id = tool_id
        self._selected = False
        self._hover = False
        self._press_timer = QTimer()
        self._press_timer.setSingleShot(True)
        self._press_timer.timeout.connect(lambda: self.long_pressed.emit(self.tool_id))

        self.setFixedSize(44, 44)
        self.setFont(QFont("Apple Color Emoji", 16))
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #6366f1, stop:1 #4f46e5);
                    border: 2px solid #818cf8;
                    border-radius: 22px;
                    color: white;
                    font-size: 18px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 22px;
                    color: #e2e8f0;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.18);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
            """)

    def mousePressEvent(self, event):
        self._press_timer.start(500)  # Long press threshold
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_timer.stop()
        super().mouseReleaseEvent(event)


# ═══════════════════════════════════════════════════════════════════
#  COLOR SWATCH BUTTON
# ═══════════════════════════════════════════════════════════════════

class ColorSwatch(QPushButton):
    """Small circular color selector button."""

    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self.color = color
        self._selected = False
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def _update_style(self):
        border = "3px solid #818cf8" if self._selected else "2px solid rgba(255,255,255,0.2)"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self.color.name()};
                border: {border};
                border-radius: 14px;
            }}
            QPushButton:hover {{
                border: 2px solid rgba(255,255,255,0.6);
            }}
        """)


# ═══════════════════════════════════════════════════════════════════
#  SECTION SEPARATOR
# ═══════════════════════════════════════════════════════════════════

class Separator(QFrame):
    """Thin horizontal separator line."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet("background: rgba(255,255,255,0.1); border: none;")


# ═══════════════════════════════════════════════════════════════════
#  FLOATING TOOLBAR
# ═══════════════════════════════════════════════════════════════════

class FloatingToolbar(QWidget):
    """
    Premium floating toolbar for supaDraw.
    Draggable, compact, and visually polished.
    """

    # ── Signals ──────────────────────────────────────────────────
    tool_selected = pyqtSignal(ToolType)
    color_selected = pyqtSignal(QColor)
    width_changed = pyqtSignal(float)
    background_selected = pyqtSignal(BackgroundType)
    curtain_toggled = pyqtSignal()
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    page_add = pyqtSignal()
    page_prev = pyqtSignal()
    page_next = pyqtSignal()
    desktop_mode_toggled = pyqtSignal()
    image_import = pyqtSignal()
    close_app = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self._current_tool = ToolType.PEN
        self._current_color = DEFAULT_COLORS[0]
        self._tool_buttons = {}
        self._color_swatches = []

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(260)

        self._build_ui()
        self._apply_shadow()
        self._select_tool(ToolType.PEN)
        self._select_color(DEFAULT_COLORS[0])

    # ── Build UI ─────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Main container for glassmorphism
        self.container = QWidget()
        self.container.setObjectName("toolbarContainer")
        self.container.setStyleSheet("""
            #toolbarContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 32, 48, 235),
                    stop:1 rgba(22, 24, 38, 245));
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # ── Drag Handle ──────────────────────────────────────────
        handle = QLabel("⠿  supaDraw")
        handle.setAlignment(Qt.AlignCenter)
        handle.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,0.5);
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 2px;
                padding: 4px;
            }
        """)
        layout.addWidget(handle)

        layout.addWidget(Separator())

        # ── Drawing Tools ────────────────────────────────────────
        tools_row = QHBoxLayout()
        tools_row.setSpacing(4)

        tool_defs = [
            ("✏️", ToolType.PEN, "Kalem"),
            ("🖍️", ToolType.HIGHLIGHTER, "Fosforlu"),
            ("🖌️", ToolType.CHISEL, "Kesik Uç"),
            ("🧹", ToolType.ERASER, "Silgi"),
        ]

        for emoji, tool, tooltip in tool_defs:
            btn = ToolButton(emoji, tool.name)
            btn.setToolTip(tooltip)
            btn.clicked.connect(partial(self._on_tool_click, tool))
            btn.long_pressed.connect(self._on_long_press)
            tools_row.addWidget(btn)
            self._tool_buttons[tool] = btn

        layout.addLayout(tools_row)

        # ── Shape Tools ──────────────────────────────────────────
        shapes_row = QHBoxLayout()
        shapes_row.setSpacing(4)

        shape_defs = [
            ("╱", ToolType.LINE, "Çizgi"),
            ("▭", ToolType.RECTANGLE, "Dikdörtgen"),
            ("○", ToolType.CIRCLE, "Daire"),
            ("→", ToolType.ARROW, "Ok"),
        ]

        for emoji, tool, tooltip in shape_defs:
            btn = ToolButton(emoji, tool.name)
            btn.setToolTip(tooltip)
            btn.clicked.connect(partial(self._on_tool_click, tool))
            btn.long_pressed.connect(self._on_long_press)
            shapes_row.addWidget(btn)
            self._tool_buttons[tool] = btn

        layout.addLayout(shapes_row)

        layout.addWidget(Separator())

        # ── Color Palette ────────────────────────────────────────
        color_grid = QGridLayout()
        color_grid.setSpacing(4)

        for i, color in enumerate(DEFAULT_COLORS):
            swatch = ColorSwatch(color)
            swatch.clicked.connect(partial(self._on_color_click, color, i))
            color_grid.addWidget(swatch, i // 5, i % 5)
            self._color_swatches.append(swatch)

        # Custom color button
        custom_btn = QPushButton("+")
        custom_btn.setFixedSize(28, 28)
        custom_btn.setCursor(Qt.PointingHandCursor)
        custom_btn.setToolTip("Özel Renk Seç")
        custom_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                border: 1px dashed rgba(255,255,255,0.3);
                border-radius: 14px;
                color: #a0a8c0;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.18);
            }
        """)
        custom_btn.clicked.connect(self._on_custom_color)
        color_grid.addWidget(custom_btn, 1, 4)  # Keep in grid

        layout.addLayout(color_grid)

        # ── Width Slider ─────────────────────────────────────────
        width_row = QHBoxLayout()
        width_label = QLabel("╌")
        width_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 10px;")
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 60)
        self.width_slider.setValue(3)
        self.width_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255,255,255,0.1);
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #6366f1;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #818cf8);
                border-radius: 3px;
            }
        """)
        self.width_slider.valueChanged.connect(
            lambda v: self.width_changed.emit(float(v))
        )
        width_thick = QLabel("━")
        width_thick.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 14px;")
        width_row.addWidget(width_label)
        width_row.addWidget(self.width_slider)
        width_row.addWidget(width_thick)
        layout.addLayout(width_row)

        layout.addWidget(Separator())

        # ── Action Buttons ───────────────────────────────────────
        actions_row = QHBoxLayout()
        actions_row.setSpacing(4)

        action_defs = [
            ("↩", self.undo_requested.emit, "Geri Al (Ctrl+Z)"),
            ("↪", self.redo_requested.emit, "İleri Al (Ctrl+Y)"),
            ("🗑", self.clear_requested.emit, "Sayfayı Temizle"),
            ("🖼", self._on_image_import, "Resim Ekle"),
            ("🎭", self.curtain_toggled.emit, "Perdeleme"),
        ]

        for emoji, handler, tooltip in action_defs:
            btn = QPushButton(emoji)
            btn.setFixedSize(40, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 10px;
                    color: #c8d0e0;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.15);
                    border-color: rgba(255,255,255,0.25);
                }
                QPushButton:pressed {
                    background: rgba(99, 102, 241, 0.3);
                }
            """)
            btn.clicked.connect(handler)
            actions_row.addWidget(btn)

        layout.addLayout(actions_row)

        layout.addWidget(Separator())

        # ── Background Selector ──────────────────────────────────
        bg_row = QHBoxLayout()
        bg_row.setSpacing(3)

        bg_defs = [
            ("🔲", BackgroundType.NONE, "Şeffaf"),
            ("⬜", BackgroundType.WHITE, "Beyaz Tahta"),
            ("📏", BackgroundType.GRID, "Kareli"),
            ("📝", BackgroundType.LINED, "Çizgili"),
            ("⚫", BackgroundType.BLACKBOARD, "Kara Tahta"),
        ]

        for emoji, bg, tooltip in bg_defs:
            btn = QPushButton(emoji)
            btn.setFixedSize(40, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 8px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.12);
                }
            """)
            btn.clicked.connect(partial(self._on_bg_click, bg))
            bg_row.addWidget(btn)

        layout.addLayout(bg_row)

        layout.addWidget(Separator())

        # ── Page Navigation ──────────────────────────────────────
        page_row = QHBoxLayout()
        page_row.setSpacing(4)

        prev_btn = QPushButton("◀")
        prev_btn.setFixedSize(36, 30)
        prev_btn.setCursor(Qt.PointingHandCursor)
        prev_btn.setToolTip("Önceki Sayfa")
        prev_btn.setStyleSheet(self._nav_btn_style())
        prev_btn.clicked.connect(self.page_prev.emit)

        self.page_label = QLabel("1 / 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("color: #a0a8c0; font-size: 11px;")

        next_btn = QPushButton("▶")
        next_btn.setFixedSize(36, 30)
        next_btn.setCursor(Qt.PointingHandCursor)
        next_btn.setToolTip("Sonraki Sayfa")
        next_btn.setStyleSheet(self._nav_btn_style())
        next_btn.clicked.connect(self.page_next.emit)

        add_btn = QPushButton("＋")
        add_btn.setFixedSize(36, 30)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setToolTip("Yeni Sayfa Ekle")
        add_btn.setStyleSheet(self._nav_btn_style())
        add_btn.clicked.connect(self.page_add.emit)

        page_row.addWidget(prev_btn)
        page_row.addWidget(self.page_label)
        page_row.addWidget(next_btn)
        page_row.addWidget(add_btn)

        layout.addLayout(page_row)

        layout.addWidget(Separator())

        # ── Bottom Controls ──────────────────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(4)

        self._desktop_btn = QPushButton("✏️")
        self._desktop_btn.setFixedSize(68, 34)
        self._desktop_btn.setCursor(Qt.PointingHandCursor)
        self._desktop_btn.setToolTip("Çizim / Masaüstü Modu Geçişi")
        self._desktop_btn.setStyleSheet(self._mode_btn_style(draw_mode=True))
        self._desktop_btn.clicked.connect(self.desktop_mode_toggled.emit)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(40, 34)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("Kapat")
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 10px;
                color: #f87171;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.35);
            }
        """)
        close_btn.clicked.connect(self.close_app.emit)

        bottom_row.addWidget(self._desktop_btn)
        bottom_row.addStretch()
        bottom_row.addWidget(close_btn)

        layout.addLayout(bottom_row)

        root.addWidget(self.container)

    # ── Helpers ──────────────────────────────────────────────────

    def _nav_btn_style(self):
        return """
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                color: #c8d0e0;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.15);
            }
        """

    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.container.setGraphicsEffect(shadow)

    # ── Event Handlers ───────────────────────────────────────────

    def _on_tool_click(self, tool: ToolType):
        self._select_tool(tool)
        self.tool_selected.emit(tool)

    def _select_tool(self, tool: ToolType):
        self._current_tool = tool
        for t, btn in self._tool_buttons.items():
            btn.set_selected(t == tool)

    def _on_color_click(self, color: QColor, index: int):
        self._select_color(color)
        self.color_selected.emit(color)

    def _select_color(self, color: QColor):
        self._current_color = color
        for swatch in self._color_swatches:
            swatch.set_selected(swatch.color.name() == color.name())

    def _on_custom_color(self):
        color = QColorDialog.getColor(self._current_color, self, "Renk Seç")
        if color.isValid():
            self._select_color(color)
            self.color_selected.emit(color)

    def _on_bg_click(self, bg: BackgroundType):
        self.background_selected.emit(bg)

    def _on_image_import(self):
        self.image_import.emit()

    def _on_long_press(self, tool_name: str):
        """Handle long press for quick-access customization."""
        # Currently a placeholder — would show add/remove menu
        pass

    def update_page_label(self, current: int, total: int):
        """Update the page navigation label."""
        self.page_label.setText(f"{current} / {total}")

    def set_mode_indicator(self, draw_mode: bool):
        """Update the mode toggle button to show current state."""
        if draw_mode:
            self._desktop_btn.setText("✏️")
            self._desktop_btn.setToolTip("Çizim Modu — Masaüstüne geçmek için tıklayın")
        else:
            self._desktop_btn.setText("🖥️")
            self._desktop_btn.setToolTip("Masaüstü Modu — Çizime dönmek için tıklayın")
        self._desktop_btn.setStyleSheet(self._mode_btn_style(draw_mode))

    def _mode_btn_style(self, draw_mode: bool) -> str:
        """Return style for the mode toggle button."""
        if draw_mode:
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(99, 102, 241, 0.3), stop:1 rgba(99, 102, 241, 0.15));
                    border: 1px solid rgba(99, 102, 241, 0.5);
                    border-radius: 10px;
                    color: #a5b4fc;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background: rgba(99, 102, 241, 0.4);
                }
            """
        else:
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(34, 197, 94, 0.3), stop:1 rgba(34, 197, 94, 0.15));
                    border: 1px solid rgba(34, 197, 94, 0.5);
                    border-radius: 10px;
                    color: #86efac;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background: rgba(34, 197, 94, 0.4);
                }
            """

    # ── Drag Movement ────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ── Summon to cursor ─────────────────────────────────────────

    def summon(self):
        """Move toolbar to current cursor position."""
        pos = QCursor.pos()
        self.move(pos.x() - self.width() // 2, pos.y() - 50)
