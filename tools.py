"""
supaDraw Tool Definitions
─────────────────────────
Enum-based tool system with painting logic for each tool type.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QColor


class ToolType(Enum):
    """Available drawing tools."""
    PEN = auto()
    HIGHLIGHTER = auto()
    CHISEL = auto()        # Kesik uçlu kalem — Arapça dersleri
    ERASER = auto()
    LINE = auto()
    RECTANGLE = auto()
    CIRCLE = auto()
    ARROW = auto()
    CURSOR = auto()        # Desktop interaction mode


class BackgroundType(Enum):
    """Available background types for pages."""
    NONE = "none"          # Transparent — draw over desktop
    WHITE = "white"        # Clean whiteboard
    GRID = "grid"          # Math / geometry
    LINED = "lined"        # Note-taking
    DOTTED = "dotted"      # Engineering / design
    BLACKBOARD = "blackboard"  # Classic chalkboard look


@dataclass
class Stroke:
    """Represents a single drawn stroke."""
    points: List[QPointF] = field(default_factory=list)
    color: QColor = field(default_factory=lambda: QColor(0, 0, 0))
    width: float = 3.0
    tool: ToolType = ToolType.PEN
    opacity: float = 1.0

    # Shape-specific (for LINE, RECT, CIRCLE, ARROW)
    start_point: Optional[QPointF] = None
    end_point: Optional[QPointF] = None


@dataclass
class ImageStamp:
    """Represents an image placed on the canvas."""
    path: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 200.0
    height: float = 200.0
    rotation: float = 0.0


@dataclass
class Page:
    """Represents a single page with its content."""
    strokes: List[Stroke] = field(default_factory=list)
    images: List[ImageStamp] = field(default_factory=list)
    background: BackgroundType = BackgroundType.NONE
    undo_stack: List[List[Stroke]] = field(default_factory=list)
    redo_stack: List[List[Stroke]] = field(default_factory=list)


# ── Default Color Palette ─────────────────────────────────────────

DEFAULT_COLORS = [
    QColor("#1a1a2e"),   # Koyu lacivert
    QColor("#e94560"),   # Kırmızı
    QColor("#0f3460"),   # Mavi
    QColor("#16c79a"),   # Yeşil
    QColor("#f5a623"),   # Turuncu
    QColor("#8b5cf6"),   # Mor
    QColor("#ffffff"),   # Beyaz
    QColor("#f472b6"),   # Pembe
    QColor("#06b6d4"),   # Cyan
    QColor("#84cc16"),   # Lime yeşili
]

# ── Tool Configuration Defaults ───────────────────────────────────

TOOL_DEFAULTS = {
    ToolType.PEN: {"width": 3.0, "opacity": 1.0},
    ToolType.HIGHLIGHTER: {"width": 20.0, "opacity": 0.35},
    ToolType.CHISEL: {"width": 8.0, "opacity": 1.0},
    ToolType.ERASER: {"width": 25.0, "opacity": 1.0},
    ToolType.LINE: {"width": 3.0, "opacity": 1.0},
    ToolType.RECTANGLE: {"width": 3.0, "opacity": 1.0},
    ToolType.CIRCLE: {"width": 3.0, "opacity": 1.0},
    ToolType.ARROW: {"width": 3.0, "opacity": 1.0},
}
