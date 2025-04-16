import os
from pathlib import Path

APP_NAME = "Clipse GUI"
APPLICATION_ID = "org.d7om.ClipseGUI"
CONFIG_DIR = os.path.expanduser("~/.config/clipse")
HISTORY_FILENAME = "clipboard_history.json"
HISTORY_FILE_PATH = os.path.join(CONFIG_DIR, HISTORY_FILENAME)

# --- UI Defaults ---
DEFAULT_WINDOW_WIDTH = 500
DEFAULT_WINDOW_HEIGHT = 700
DEFAULT_PREVIEW_TEXT_WIDTH = 700
DEFAULT_PREVIEW_TEXT_HEIGHT = 550
DEFAULT_PREVIEW_IMG_WIDTH = 400  # Min size if error
DEFAULT_PREVIEW_IMG_HEIGHT = 200  # Min size if error
DEFAULT_HELP_WIDTH = 450
DEFAULT_HELP_HEIGHT = 550
LIST_ITEM_IMAGE_WIDTH = 200  # Thumbnail width
LIST_ITEM_IMAGE_HEIGHT = 100  # Thumbnail height

# --- Lazy Loading ---
INITIAL_LOAD_COUNT = 30
LOAD_BATCH_SIZE = 20
LOAD_THRESHOLD_FACTOR = 0.95  # Load when scrolled 95% down

# --- Image Cache ---
IMAGE_CACHE_MAX_SIZE = 50

# --- Debounce Timers (ms) ---
SAVE_DEBOUNCE_MS = 500
SEARCH_DEBOUNCE_MS = 250

COMPACT_MODE = True
ENTER_TO_PASTE = True
PASTE_TOOL_CMD = "wl-paste --no-newline"
X11_PASTE_TOOL_CMD = "xclip -o -selection clipboard"


# --- CSS Styling ---
APP_CSS = """
.pinned-row {
    border-left: 3px solid #ffcc00;
    font-weight: 500;
}
.list-row {
    padding: 8px 12px;
    transition: background-color 0.2s ease;
    border-bottom: 1px solid #161A16;
}
.list-row:selected {
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
    border-top: 1px solid #ccc;
    padding-top: 5px;
    margin-top: 5px;
    color: #888a85;
    font-style: italic;
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
    border: 1px solid rgba(0,0,0,0.1);
}
"""
