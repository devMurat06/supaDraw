#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  supaDraw — Etkileşimli Tahta Kalem Uygulaması              ║
║  ─────────────────────────────────────────────────────────── ║
║  Ekran üzerine şeffaf katman ile her türlü görüntü          ║
║  üzerinde çizim yapmanızı sağlayan hızlı ve pratik          ║
║  bir kalem programıdır.                                     ║
╚══════════════════════════════════════════════════════════════╝

Keyboard Shortcuts:
    Ctrl+Z      — Geri al
    Ctrl+Y      — İleri al
    1-9         — Hızlı renk değiştirme
    +/-         — Kalem kalınlığı
    Scroll      — Kalem kalınlığı (fare tekerleği)
"""

import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QColor, QIcon, QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QDesktopWidget,
    QSystemTrayIcon, QMenu, QAction
)

from src.canvas import DrawingCanvas
from src.toolbar import FloatingToolbar
from src.curtain import CurtainOverlay
from src.image_manager import ImageManager
from src.settings import Settings
from src.tools import ToolType, BackgroundType

# Path to logo
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")


class OverlayWindow(QWidget):
    """
    Transparent fullscreen overlay that sits on top of ALL other windows.
    Users draw on it, and use the 🖥️ toolbar button to switch to desktop mode.
    """

    def __init__(self):
        super().__init__()

        self._ready = False
        self.settings = Settings()
        self._draw_mode = True

        # ── Window Flags ─────────────────────────────────────────
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.MaximizeUsingFullscreenGeometryHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # ── Cover entire screen (NOT showFullScreen) ─────────────
        screen_geo = QDesktopWidget().screenGeometry()
        self.setGeometry(screen_geo)

        # ── Drawing Canvas ───────────────────────────────────────
        self.canvas = DrawingCanvas(self)
        self.canvas.setGeometry(0, 0, screen_geo.width(), screen_geo.height())

        # ── Screen Curtain ───────────────────────────────────────
        self.curtain = CurtainOverlay(self.canvas)
        self.curtain.setGeometry(0, 0, screen_geo.width(), screen_geo.height())

        # ── Image Manager ────────────────────────────────────────
        self.image_manager = ImageManager()

        # ── Floating Toolbar ─────────────────────────────────────
        self.toolbar = FloatingToolbar()
        tb_x = self.settings.get("toolbar_x", 100)
        tb_y = self.settings.get("toolbar_y", 100)
        self.toolbar.move(tb_x, tb_y)

        # ── System Tray ──────────────────────────────────────────
        self._setup_tray()

        # ── Connect Signals ──────────────────────────────────────
        self._connect_signals()

        # ── Restore settings ─────────────────────────────────────
        last_color = self.settings.get("pen_color", "#1a1a2e")
        self.canvas.set_color(QColor(last_color))
        last_width = self.settings.get("pen_width", 3.0)
        self.canvas.set_width(last_width)

        # ── Keep toolbar always on top of canvas ────────────────
        # The toolbar must NEVER be covered by drawing strokes.
        # We use a periodic check to enforce z-order.
        self._raise_timer = QTimer(self)
        self._raise_timer.timeout.connect(self._ensure_toolbar_on_top)
        self._raise_timer.start(250)  # Check every 250ms

        # ── Show ─────────────────────────────────────────────────
        self._ready = True
        self.show()
        self.raise_()
        self.activateWindow()
        self.toolbar.show()
        self.toolbar.raise_()
        QTimer.singleShot(200, self._focus_canvas)

    # ── Layer Management ─────────────────────────────────────────

    def _ensure_toolbar_on_top(self):
        """Ensure toolbar is always above the canvas overlay."""
        if self.toolbar.isVisible():
            self.toolbar.raise_()

    def changeEvent(self, event):
        """When overlay is activated, immediately re-raise toolbar."""
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange and self.isActiveWindow():
            QTimer.singleShot(10, self._ensure_toolbar_on_top)

    # ── Helpers ──────────────────────────────────────────────────

    def _focus_canvas(self):
        """Give keyboard focus to the canvas."""
        if self._draw_mode:
            self.canvas.setFocus()
            self.raise_()

    def _setup_tray(self):
        """System tray icon for quick mode switching."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = QIcon(LOGO_PATH) if os.path.exists(LOGO_PATH) else QIcon()
        self.tray = QSystemTrayIcon(icon, self)

        tray_menu = QMenu()
        draw_act = QAction("✏️  Çizim Modu", self)
        draw_act.triggered.connect(lambda: self._set_draw_mode(True))
        tray_menu.addAction(draw_act)

        desk_act = QAction("🖥️  Masaüstü Modu", self)
        desk_act.triggered.connect(lambda: self._set_draw_mode(False))
        tray_menu.addAction(desk_act)

        tray_menu.addSeparator()
        quit_act = QAction("✕  Çıkış", self)
        quit_act.triggered.connect(self._close)
        tray_menu.addAction(quit_act)

        self.tray.setContextMenu(tray_menu)
        self.tray.setToolTip("supaDraw")
        self.tray.activated.connect(self._on_tray_click)
        self.tray.show()

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_mode()

    # ── Signal Wiring ────────────────────────────────────────────

    def _connect_signals(self):
        tb = self.toolbar
        cv = self.canvas

        tb.tool_selected.connect(cv.set_tool)
        tb.color_selected.connect(cv.set_color)
        tb.width_changed.connect(cv.set_width)
        tb.background_selected.connect(cv.set_background)
        tb.curtain_toggled.connect(self.curtain.toggle)
        tb.undo_requested.connect(cv.undo)
        tb.redo_requested.connect(cv.redo)
        tb.clear_requested.connect(cv.clear_page)
        tb.page_add.connect(cv.add_page)
        tb.page_prev.connect(cv.prev_page)
        tb.page_next.connect(cv.next_page)
        cv.page_changed.connect(tb.update_page_label)
        tb.desktop_mode_toggled.connect(self._toggle_mode)
        tb.image_import.connect(self._import_image)
        tb.close_app.connect(self._close)

    # ── Mode Switching ───────────────────────────────────────────

    def _toggle_mode(self):
        """Toggle between drawing and desktop mode via 🖥️ button."""
        self._set_draw_mode(not self._draw_mode)

    def _set_draw_mode(self, draw: bool):
        """
        DRAW MODE:    Overlay visible — draw on screen.
        DESKTOP MODE: Overlay hidden — use apps below. Toolbar stays.
        """
        self._draw_mode = draw

        if draw:
            self.show()
            self.raise_()
            self.activateWindow()
            self.canvas.desktop_mode = False
            self.canvas.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.canvas.setCursor(Qt.CrossCursor)
            QTimer.singleShot(50, self._focus_canvas)
        else:
            self.hide()
            self.canvas.desktop_mode = True

        # Update toolbar button state
        self.toolbar.set_mode_indicator(draw)

        # Toolbar always stays visible
        self.toolbar.show()
        self.toolbar.raise_()

    # ── Actions ──────────────────────────────────────────────────

    def _import_image(self):
        self.image_manager.import_image(self)

    def _close(self):
        self.settings.set("toolbar_x", self.toolbar.x())
        self.settings.set("toolbar_y", self.toolbar.y())
        self.settings.set("pen_color", self.canvas.current_color.name())
        self.settings.set("pen_width", self.canvas.current_width)
        self.settings.save()
        self.toolbar.close()
        if hasattr(self, 'tray'):
            self.tray.hide()
        QApplication.quit()

    # ── Keyboard ─────────────────────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()

        # F1 — summon toolbar
        if key == Qt.Key_F1:
            self.toolbar.summon()
            return

        # F5 — toggle curtain
        if key == Qt.Key_F5:
            self.curtain.toggle()
            return

        # Pass all other keys to canvas
        self.canvas.keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._ready:
            self.canvas.setGeometry(self.rect())
            self.curtain.setGeometry(self.canvas.rect())


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("supaDraw")
    app.setApplicationDisplayName("supaDraw")
    app.setQuitOnLastWindowClosed(False)

    if os.path.exists(LOGO_PATH):
        app.setWindowIcon(QIcon(LOGO_PATH))

    font = QFont("Helvetica Neue", 11)
    app.setFont(font)

    window = OverlayWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
