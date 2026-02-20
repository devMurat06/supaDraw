"""
supaDraw Image Manager
───────────────────────
Import, place, scale, and manage images on the canvas.
"""

import os
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QImage, QPainter
from PyQt5.QtWidgets import QFileDialog, QWidget

LIBRARY_DIR = os.path.join(os.path.expanduser("~"), ".supaDraw", "library")


class ImageManager:
    """Manages image imports and placement on the canvas."""

    SUPPORTED_FORMATS = "Images (*.png *.jpg *.jpeg *.bmp *.svg *.gif *.webp)"

    def __init__(self):
        os.makedirs(LIBRARY_DIR, exist_ok=True)
        self.placed_images = []  # List of (QPixmap, QRectF)

    def import_image(self, parent: QWidget = None) -> QPixmap:
        """Open file dialog and return selected image as QPixmap."""
        path, _ = QFileDialog.getOpenFileName(
            parent,
            "Resim Seç — supaDraw",
            os.path.expanduser("~"),
            self.SUPPORTED_FORMATS
        )
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                # Copy to library for future access
                self._copy_to_library(path)
                return pixmap
        return None

    def _copy_to_library(self, path: str):
        """Copy image to the local library folder."""
        try:
            import shutil
            dest = os.path.join(LIBRARY_DIR, os.path.basename(path))
            if not os.path.exists(dest):
                shutil.copy2(path, dest)
        except Exception:
            pass  # Non-critical — library copy is a convenience feature

    def get_library_images(self):
        """Return list of pixmaps from the local library."""
        images = []
        if os.path.exists(LIBRARY_DIR):
            for fname in os.listdir(LIBRARY_DIR):
                fpath = os.path.join(LIBRARY_DIR, fname)
                if os.path.isfile(fpath):
                    pixmap = QPixmap(fpath)
                    if not pixmap.isNull():
                        images.append((fname, pixmap))
        return images
