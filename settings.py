"""
supaDraw Settings
─────────────────
Persistent JSON-based settings for user preferences.
"""

import json
import os
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".supaDraw")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")


DEFAULT_SETTINGS = {
    "pen_color": "#1a1a2e",
    "pen_width": 3.0,
    "last_tool": "PEN",
    "background": "NONE",
    "toolbar_x": 100,
    "toolbar_y": 100,
    "quick_access": ["PEN", "HIGHLIGHTER", "ERASER", "LINE", "RECTANGLE", "CIRCLE"],
    "window_opacity": 1.0,
    "curtain_opacity": 0.85,
}


class Settings:
    """Manages persistent application settings."""

    def __init__(self):
        self._data: Dict[str, Any] = DEFAULT_SETTINGS.copy()
        self._load()

    def _load(self):
        """Load settings from disk."""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    saved = json.load(f)
                    self._data.update(saved)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Ayarlar yüklenemedi, varsayılan kullanılıyor: {e}")

    def save(self):
        """Save settings to disk."""
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Ayarlar kaydedilemedi: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def get_quick_access(self) -> List[str]:
        return self._data.get("quick_access", DEFAULT_SETTINGS["quick_access"])

    def set_quick_access(self, tools: List[str]):
        self._data["quick_access"] = tools
