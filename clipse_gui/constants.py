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
        "save_debounce_ms": "300",
        "search_debounce_ms": "250",
        "paste_simulation_delay_ms": "150",
        "minimize_to_tray": "True",
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
        "default_help_width": "450",
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
SAVE_DEBOUNCE_MS = config.getint("General", "save_debounce_ms", fallback=300)
SEARCH_DEBOUNCE_MS = config.getint("General", "search_debounce_ms", fallback=250)
PASTE_SIMULATION_DELAY_MS = config.getint(
    "General", "paste_simulation_delay_ms", fallback=150
)
MINIMIZE_TO_TRAY = config.getboolean("General", "minimize_to_tray", fallback=True)

COPY_TOOL_CMD = config.get("Commands", "copy_tool_cmd", fallback="wl-copy")
X11_COPY_TOOL_CMD = config.get(
    "Commands", "x11_copy_tool_cmd", fallback="xclip -i -selection clipboard"
)
PASTE_SIMULATION_CMD_WAYLAND = config.get(
    "Commands", "paste_simulation_cmd_wayland", fallback="wtype -M ctrl -P v -p v -m ctrl"
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
DEFAULT_HELP_WIDTH = config.getint("UI", "default_help_width", fallback=450)
DEFAULT_HELP_HEIGHT = config.getint("UI", "default_help_height", fallback=550)
LIST_ITEM_IMAGE_WIDTH = config.getint("UI", "list_item_image_width", fallback=200)
LIST_ITEM_IMAGE_HEIGHT = config.getint("UI", "list_item_image_height", fallback=100)

INITIAL_LOAD_COUNT = config.getint("Performance", "initial_load_count", fallback=30)
LOAD_BATCH_SIZE = config.getint("Performance", "load_batch_size", fallback=20)
LOAD_THRESHOLD_FACTOR = config.getfloat(
    "Performance", "load_threshold_factor", fallback=0.95
)
IMAGE_CACHE_MAX_SIZE = config.getint("Performance", "image_cache_max_size", fallback=50)

# CSS Styles
APP_CSS = """
listboxrow.pinned-row {
    border-left: 3px solid #ffcc00;
    font-weight: 500;
}
*.selected-row,
row.selected-row,
.selected-row {
    background-color: alpha(#9b59b6, 0.15);
    border-left-width: 2px;
    border-left-style: dashed;
    border-left-color: alpha(#9b59b6, 0.15);
    border-right-width: 2px;
    border-right-style: dashed;
    border-right-color: alpha(#9b59b6, 0.15);
    border-top-width: 1px;
    border-top-style: dashed;
    border-top-color: alpha(#9b59b6, 0.15);
    border-bottom-width: 1px;
    border-bottom-style: dashed;
    border-bottom-color: alpha(#9b59b6, 0.15);
    border-radius: 8px;
    margin-top: 2px;
    margin-bottom: 2px;
}
*.selected-row.pinned-row,
row.selected-row.pinned-row,
.selected-row.pinned-row {
    background-color: alpha(#9b59b6, 0.15);
    border-left-width: 1px;
    border-left-style: dashed;
    border-left-color: alpha(#9b59b6, 0.15);
    border-right-width: 1px;
    border-right-style: dashed;
    border-right-color: alpha(#9b59b6, 0.15);
    border-top-width: 1px;
    border-top-style: dashed;
    border-top-color: alpha(#9b59b6, 0.15);
    border-bottom-width: 1px;
    border-bottom-style: dashed;
    border-bottom-color: alpha(#9b59b6, 0.15);
    border-radius: 8px;
}
.selection-mode listboxrow.list-row {
    transition: background-color 0.15s ease;
}
.selection-mode listboxrow.list-row:hover {
    background-color: alpha(#729fcf, 0.08);
}
listboxrow.list-row {
    padding: 8px 12px;
    transition: background-color 0.2s ease;
    border-bottom: 1px solid #161A16;
    margin-top: 3px;
    margin-bottom: 3px;
}
listboxrow.list-row:selected {
    border-left: 3px solid #4a90e2;
    background-color: alpha(#4a90e2, 0.1);
}
.timestamp {
    font-size: 85%;
    color: #888a85;
    font-style: italic;
    margin-top: 3px;
}
.status-label {
    color: #888a85;
    font-style: italic;
}
.visual-mode-indicator {
    background-color: alpha(#9b59b6, 0.15);
    color: #9b59b6;
    font-weight: bold;
    font-size: 90%;
    padding: 4px 12px;
    border-radius: 3px;
}
.status-bar {
    border-top: 1px solid #ccc;
    padding-top: 5px;
}
textview {
     font-family: Monospace;
}
.key-shortcut {
    font-family: Monospace;
    font-weight: bold;
    background-color: rgba(0,0,0,0.08);
    padding: 3px 6px;
    border-radius: 4px;
}

/* Compact mode styles */
.compact-mode listboxrow.list-row {
    padding: 2px 4px;
    margin-top: 3px;
    margin-bottom: 3px;
}
.compact-mode listboxrow.list-row:selected {
    border-left: 2px solid #4a90e2;
}
.compact-mode .timestamp {
    font-size: 60%;
    margin-top: 0px;
}
.compact-mode .status-label {
    padding-top: 2px;
    margin-top: 2px;
    font-size: 80%;
}
.compact-mode .key-shortcut {
    padding: 1px 3px;
}"""

log.debug(f"Using configuration directory: {CONFIG_DIR}")
log.debug(f"Using configuration file: {CONFIG_FILE_PATH}")
log.debug(f"History file path set to: {HISTORY_FILE_PATH}")
log.debug(f"Paste simulation Wayland: {PASTE_SIMULATION_CMD_WAYLAND}")
log.debug(f"Paste simulation X11: {PASTE_SIMULATION_CMD_X11}")
log.debug(f"Paste simulation delay: {PASTE_SIMULATION_DELAY_MS}ms")
