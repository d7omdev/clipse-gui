"""Simplified constants file."""

import os
from typing import Literal
from .config_manager import ConfigManager
import logging

log = logging.getLogger(__name__)

# Basic app info
APP_NAME: Literal["Clipse GUI"] = "Clipse GUI"
APPLICATION_ID: Literal["org.d7om.ClipseGUI"] = "org.d7om.ClipseGUI"
CONFIG_DIR: str = os.path.expanduser("~/.config/clipse-gui")
CONFIG_FILENAME: Literal["settings.ini"] = "settings.ini"
CONFIG_FILE_PATH: str = os.path.join(CONFIG_DIR, CONFIG_FILENAME)

# Default settings
DEFAULT_SETTINGS = {
    "General": {
        "clipse_dir": "~/.config/clipse",
        "history_filename": "clipboard_history.json",
        "enter_to_paste": "False",
        "compact_mode": "False",
        "protect_pinned_items": "False",
        "hover_to_select": "False",
        "highlight_search": "True",
        "save_debounce_ms": "300",
        "search_debounce_ms": "250",
        "paste_simulation_delay_ms": "150",
        "minimize_to_tray": "True",
        "tray_items_count": "20",
        "tray_paste_on_select": "True",
    },
    "Style": {
        "border_radius": "6",
        "accent_color": "#ffcc00",
        "selection_color": "#4a90e2",
        "selection_bg_color": "#4a90e2",
        "hover_color": "#4a90e2",
        "hover_bg_color": "#4a90e2",
        "visual_mode_color": "#9b59b6",
    },
    "Commands": {
        "copy_tool_cmd": "wl-copy",
        "x11_copy_tool_cmd": "xclip -i -selection clipboard",
        "paste_simulation_cmd_wayland": "wtype -M ctrl -P v -p v -m ctrl",
        "paste_simulation_cmd_x11": "xdotool key --clearmodifiers ctrl+v",
    },
    "UI": {
        "default_window_width": "500",
        "default_window_height": "700",
        "default_preview_text_width": "700",
        "default_preview_text_height": "550",
        "default_preview_img_width": "400",
        "default_preview_img_height": "200",
        "default_help_width": "550",
        "default_help_height": "550",
        "list_item_image_width": "200",
        "list_item_image_height": "100",
    },
    "Performance": {
        "initial_load_count": "30",
        "load_batch_size": "20",
        "load_threshold_factor": "0.95",
        "image_cache_max_size": "50",
    },
}

# Initialize config
config = ConfigManager(CONFIG_FILE_PATH, DEFAULT_SETTINGS)

# Derived constants - using simple fallbacks
CLIPSE_DIR = os.path.expanduser(
    config.get("General", "clipse_dir", fallback="~/.config/clipse")
)
HISTORY_FILENAME = config.get(
    "General", "history_filename", fallback="clipboard_history.json"
)
HISTORY_FILE_PATH = os.path.join(CLIPSE_DIR, HISTORY_FILENAME)

ENTER_TO_PASTE = config.getboolean("General", "enter_to_paste", fallback=False)
COMPACT_MODE = config.getboolean("General", "compact_mode", fallback=False)
PROTECT_PINNED_ITEMS = config.getboolean(
    "General", "protect_pinned_items", fallback=False
)
HOVER_TO_SELECT = config.getboolean("General", "hover_to_select", fallback=False)
HIGHLIGHT_SEARCH = config.getboolean("General", "highlight_search", fallback=True)
SAVE_DEBOUNCE_MS = config.getint("General", "save_debounce_ms", fallback=300)
SEARCH_DEBOUNCE_MS = config.getint("General", "search_debounce_ms", fallback=250)
PASTE_SIMULATION_DELAY_MS = config.getint(
    "General", "paste_simulation_delay_ms", fallback=150
)
MINIMIZE_TO_TRAY = config.getboolean("General", "minimize_to_tray", fallback=True)
TRAY_ITEMS_COUNT = config.getint("General", "tray_items_count", fallback=20)
TRAY_PASTE_ON_SELECT = config.getboolean(
    "General", "tray_paste_on_select", fallback=True
)

# Style settings
BORDER_RADIUS = config.getint("Style", "border_radius", fallback=6)
ACCENT_COLOR = config.get("Style", "accent_color", fallback="#ffcc00")
SELECTION_COLOR = config.get("Style", "selection_color", fallback="#4a90e2")
SELECTION_BG_COLOR = config.get("Style", "selection_bg_color", fallback="#4a90e2")
HOVER_COLOR = config.get("Style", "hover_color", fallback="#4a90e2")
HOVER_BG_COLOR = config.get("Style", "hover_bg_color", fallback="#4a90e2")
VISUAL_MODE_COLOR = config.get("Style", "visual_mode_color", fallback="#9b59b6")

COPY_TOOL_CMD = config.get("Commands", "copy_tool_cmd", fallback="wl-copy")
X11_COPY_TOOL_CMD = config.get(
    "Commands", "x11_copy_tool_cmd", fallback="xclip -i -selection clipboard"
)
PASTE_SIMULATION_CMD_WAYLAND = config.get(
    "Commands",
    "paste_simulation_cmd_wayland",
    fallback="wtype -M ctrl -P v -p v -m ctrl",
)
PASTE_SIMULATION_CMD_X11 = config.get(
    "Commands",
    "paste_simulation_cmd_x11",
    fallback="xdotool key --clearmodifiers ctrl+v",
)

DEFAULT_WINDOW_WIDTH = config.getint("UI", "default_window_width", fallback=500)
DEFAULT_WINDOW_HEIGHT = config.getint("UI", "default_window_height", fallback=700)
DEFAULT_PREVIEW_TEXT_WIDTH = config.getint(
    "UI", "default_preview_text_width", fallback=700
)
DEFAULT_PREVIEW_TEXT_HEIGHT = config.getint(
    "UI", "default_preview_text_height", fallback=550
)
DEFAULT_PREVIEW_IMG_WIDTH = config.getint(
    "UI", "default_preview_img_width", fallback=400
)
DEFAULT_PREVIEW_IMG_HEIGHT = config.getint(
    "UI", "default_preview_img_height", fallback=200
)
DEFAULT_HELP_WIDTH = config.getint("UI", "default_help_width", fallback=600)
DEFAULT_HELP_HEIGHT = config.getint("UI", "default_help_height", fallback=700)
LIST_ITEM_IMAGE_WIDTH = config.getint("UI", "list_item_image_width", fallback=200)
LIST_ITEM_IMAGE_HEIGHT = config.getint("UI", "list_item_image_height", fallback=100)

INITIAL_LOAD_COUNT = config.getint("Performance", "initial_load_count", fallback=30)
LOAD_BATCH_SIZE = config.getint("Performance", "load_batch_size", fallback=20)
LOAD_THRESHOLD_FACTOR = config.getfloat(
    "Performance", "load_threshold_factor", fallback=0.95
)
IMAGE_CACHE_MAX_SIZE = config.getint("Performance", "image_cache_max_size", fallback=50)

# CSS Styles
def get_app_css(
    border_radius=6,
    accent_color="#ffcc00",
    selection_color="#4a90e2",
    visual_mode_color="#9b59b6",
):
    """Generate app CSS with customizable style variables."""
    return f"""
.pinned-row {{
    border-left: 3px solid {accent_color};
    background-color: alpha({accent_color}, 0.01);
    font-weight: 500;
    border-radius: 0 {border_radius}px {border_radius}px 0;
}}
.list-row {{
    padding: 8px 12px;
    margin-top: 1px;
    margin-bottom: 1px;
    border-left: 3px solid transparent;
    border-radius: 0 {border_radius}px {border_radius}px 0;
    transition: background-color 0.2s ease,
                border-left-color 0.2s ease;
}}
.list-row:hover {{
    background-color: alpha({selection_color}, 0.07);
    border-left-color: alpha({selection_color}, 0.45);
}}
.list-row:selected {{
    background-color: alpha({selection_color}, 0.13);
    border-left-color: {selection_color};
}}

/* Visual mode selection */
.visual-mode-indicator {{
    background-color: {visual_mode_color};
    padding-right: 4px;
    padding-left: 4px;
    border-radius: {max(2, border_radius - 2)}px;

}}

.list-row.selected-row {{
    background-color: alpha({visual_mode_color}, 0.15);
    border-left-color: {visual_mode_color};
}}
.list-row.selected-row:hover {{
    background-color: alpha({visual_mode_color}, 0.2);
    border-left-color: {visual_mode_color};
}}

/* Pinned + visual mode selected */
.pinned-row.selected-row {{
    background-color: alpha({accent_color}, 0.14);
    border-left-color: {accent_color};
}}

.pinned-row:hover {{
    background-color: alpha({accent_color}, 0.08);
    border-left-color: alpha({accent_color}, 0.7);
}}
.pinned-row:selected {{
    background-color: alpha({accent_color}, 0.12);
    border-left-color: {accent_color};
}}
.timestamp {{
    font-size: 82%;
    color: alpha(#ffffff, 0.35);
    font-style: italic;
    margin-top: 2px;
}}
.status-label {{
    border-top: 1px solid alpha(#ffffff, 0.07);
    padding-top: 5px;
    margin-top: 5px;
    color: alpha(#ffffff, 0.4);
    font-style: italic;
    font-size: 90%;
}}
textview {{
    font-family: Monospace;
}}
.key-shortcut {{
    font-family: Monospace;
    font-weight: bold;
    font-size: 88%;
    background-color: alpha(#ffffff, 0.07);
    color: alpha(#ffffff, 0.75);
    padding: 2px 6px;
    border-radius: {border_radius}px;
    border: 1px solid alpha(#ffffff, 0.12);
}}

/* Help window section styling */
frame > box {{
    background-color: alpha(#ffffff, 0.02);
    border-radius: {border_radius}px;
    padding: 10px;
    border: 1px solid alpha(#ffffff, 0.05);
}}

frame > box > label {{
    color: alpha(#ffffff, 0.85);
}}

/* Pin icon styling */
.pin-icon {{
    transition: all 0.2s ease;
    min-width: 20px;
    min-height: 20px;
}}

.pin-icon.pinned {{
    color: {accent_color};
}}

.pin-icon.unpinned {{
    color: alpha(#ffffff, 0.25);
}}

/* Settings window styling */
.settings-section {{
    border: 1px solid alpha(#ffffff, 0.1);
    border-radius: {border_radius}px;
    padding: 10px;
    margin: 5px;
}}

.settings-section > label {{
    color: alpha(#ffffff, 0.9);
    font-weight: bold;
    margin-bottom: 5px;
}}

.settings-section frame {{
    background-color: alpha(#ffffff, 0.02);
}}

/* Main window widget styling (not settings dialog) - Use higher specificity */
.main-window button,
.main-window .text-button {{
    border-radius: {border_radius}px;
    padding: 6px 12px;
}}

.main-window button:focus {{
    outline: none;
    box-shadow: 0 0 0 2px alpha({selection_color}, 0.5);
}}

.main-window entry,
.main-window .entry {{
    border-radius: {border_radius}px;
    padding: 6px 10px;
}}

.main-window entry:focus {{
    outline: none;
    box-shadow: 0 0 0 2px alpha({selection_color}, 0.5);
}}

.main-window switch {{
    border-radius: {border_radius + 10}px;
}}

.main-window switch slider {{
    border-radius: {border_radius}px;
    min-height: {border_radius * 2 if border_radius > 0 else 20}px;
}}

.main-window spinbutton {{
    border-radius: {border_radius}px;
}}

/* Scrollbar styling */
scrollbar slider {{
    border-radius: {border_radius}px;
}}

/* List box and row focus/selection styling - use high specificity */
.main-window list,
.main-window listbox {{
    border-radius: 0;
}}

.main-window list row,
.main-window listbox row {{
    border-radius: 0 {border_radius}px {border_radius}px 0;
    outline: none;
}}

.main-window list row:focus,
.main-window listbox row:focus {{
    outline: none;
    box-shadow: inset 0 0 0 2px alpha({selection_color}, 0.4);
    border-radius: 0 {border_radius}px {border_radius}px 0;
}}

/* Ensure selected row has rounded corners */
.main-window list row:selected,
.main-window listbox row:selected {{
    border-radius: 0 {border_radius}px {border_radius}px 0;
}}
"""


# Default CSS (for backwards compatibility)
APP_CSS = get_app_css()
log.debug(f"Using configuration directory: {CONFIG_DIR}")
log.debug(f"Using configuration file: {CONFIG_FILE_PATH}")
log.debug(f"History file path set to: {HISTORY_FILE_PATH}")
log.debug(f"Paste simulation Wayland: {PASTE_SIMULATION_CMD_WAYLAND}")
log.debug(f"Paste simulation X11: {PASTE_SIMULATION_CMD_X11}")
log.debug(f"Paste simulation delay: {PASTE_SIMULATION_DELAY_MS}ms")
