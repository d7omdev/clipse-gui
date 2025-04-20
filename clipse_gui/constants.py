import os
from typing import Type, Union, Literal
from .config_manager import ConfigManager
import logging

log = logging.getLogger(__name__)

APP_NAME: Literal["Clipse GUI"] = "Clipse GUI"
APPLICATION_ID: Literal["org.d7om.ClipseGUI"] = "org.d7om.ClipseGUI"
CONFIG_DIR: str = os.path.expanduser("~/.config/clipse-gui")
CONFIG_FILENAME: Literal["settings.ini"] = "settings.ini"
CONFIG_FILE_PATH: str = os.path.join(CONFIG_DIR, CONFIG_FILENAME)

DEFAULT_SETTINGS = {
    "General": {
        "clipse_dir": "~/.config/clipse",
        "history_filename": "clipboard_history.json",
        "enter_to_paste": "False",
        "compact_mode": "False",
        "save_debounce_ms": "300",
        "search_debounce_ms": "250",
    },
    "Commands": {
        "copy_tool_cmd": "wl-copy",
        "x11_copy_tool_cmd": "xclip -i -selection clipboard",
        "paste_tool_cmd": "wl-paste --no-newline",
        "x11_paste_tool_cmd": "xclip -o -selection clipboard",
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

config = ConfigManager(CONFIG_FILE_PATH, DEFAULT_SETTINGS)


def _get_config_value(
    get_func,
    section: str,
    key: str,
    default_val: Union[str, int, float, bool],
    value_type: Type[Union[str, int, float, bool]] = str,
) -> Union[str, int, float, bool]:
    try:
        value = get_func(section, key, fallback=default_val)

        if value_type is int:
            return int(value)
        elif value_type is float:
            return float(value)
        elif value_type is bool:
            return value.lower() in ("true", "1", "t", "y", "yes")
        else:
            return str(value)
    except Exception:
        return default_val


CLIPSE_DIR: str = str(
    _get_config_value(
        config.get,
        "General",
        "clipse_dir",
        DEFAULT_SETTINGS["General"]["clipse_dir"],
        str,
    )
)
CLIPSE_DIR = os.path.expanduser(CLIPSE_DIR)

HISTORY_FILENAME: str = str(
    _get_config_value(
        config.get,
        "General",
        "history_filename",
        DEFAULT_SETTINGS["General"]["history_filename"],
        str,
    )
)

HISTORY_FILE_PATH: str = os.path.join(CLIPSE_DIR, HISTORY_FILENAME)

ENTER_TO_PASTE: bool = bool(
    _get_config_value(
        config.get,
        "General",
        "enter_to_paste",
        DEFAULT_SETTINGS["General"]["enter_to_paste"],
        bool,
    )
)

COMPACT_MODE: bool = bool(
    _get_config_value(
        config.get,
        "General",
        "compact_mode",
        DEFAULT_SETTINGS["General"]["compact_mode"],
        bool,
    )
)

SAVE_DEBOUNCE_MS: int = int(
    _get_config_value(
        config.get,
        "General",
        "save_debounce_ms",
        DEFAULT_SETTINGS["General"]["save_debounce_ms"],
        int,
    )
)

SEARCH_DEBOUNCE_MS: int = int(
    _get_config_value(
        config.get,
        "General",
        "search_debounce_ms",
        DEFAULT_SETTINGS["General"]["search_debounce_ms"],
        int,
    )
)

COPY_TOOL_CMD: str = str(
    _get_config_value(
        config.get,
        "Commands",
        "copy_tool_cmd",
        DEFAULT_SETTINGS["Commands"]["copy_tool_cmd"],
        str,
    )
)

X11_COPY_TOOL_CMD: str = str(
    _get_config_value(
        config.get,
        "Commands",
        "x11_copy_tool_cmd",
        DEFAULT_SETTINGS["Commands"]["x11_copy_tool_cmd"],
        str,
    )
)

PASTE_TOOL_CMD: str = str(
    _get_config_value(
        config.get,
        "Commands",
        "paste_tool_cmd",
        DEFAULT_SETTINGS["Commands"]["paste_tool_cmd"],
        str,
    )
)

X11_PASTE_TOOL_CMD: str = str(
    _get_config_value(
        config.get,
        "Commands",
        "x11_paste_tool_cmd",
        DEFAULT_SETTINGS["Commands"]["x11_paste_tool_cmd"],
        str,
    )
)

DEFAULT_WINDOW_WIDTH: int = int(
    _get_config_value(
        config.get,
        "UI",
        "default_window_width",
        DEFAULT_SETTINGS["UI"]["default_window_width"],
        int,
    )
)

DEFAULT_WINDOW_HEIGHT: int = int(
    _get_config_value(
        config.get,
        "UI",
        "default_window_height",
        DEFAULT_SETTINGS["UI"]["default_window_height"],
        int,
    )
)

DEFAULT_PREVIEW_TEXT_WIDTH: int = int(
    _get_config_value(
        config.get,
        "UI",
        "default_preview_text_width",
        DEFAULT_SETTINGS["UI"]["default_preview_text_width"],
        int,
    )
)

DEFAULT_PREVIEW_TEXT_HEIGHT: int = int(
    _get_config_value(
        config.get,
        "UI",
        "default_preview_text_height",
        DEFAULT_SETTINGS["UI"]["default_preview_text_height"],
        int,
    )
)

DEFAULT_PREVIEW_IMG_WIDTH: int = int(
    _get_config_value(
        config.get,
        "UI",
        "default_preview_img_width",
        DEFAULT_SETTINGS["UI"]["default_preview_img_width"],
        int,
    )
)

DEFAULT_PREVIEW_IMG_HEIGHT: int = int(
    _get_config_value(
        config.get,
        "UI",
        "default_preview_img_height",
        DEFAULT_SETTINGS["UI"]["default_preview_img_height"],
        int,
    )
)

DEFAULT_HELP_WIDTH: int = int(
    _get_config_value(
        config.get,
        "UI",
        "default_help_width",
        DEFAULT_SETTINGS["UI"]["default_help_width"],
        int,
    )
)

DEFAULT_HELP_HEIGHT: int = int(
    _get_config_value(
        config.get,
        "UI",
        "default_help_height",
        DEFAULT_SETTINGS["UI"]["default_help_height"],
        int,
    )
)

LIST_ITEM_IMAGE_WIDTH: int = int(
    _get_config_value(
        config.get,
        "UI",
        "list_item_image_width",
        DEFAULT_SETTINGS["UI"]["list_item_image_width"],
        int,
    )
)

LIST_ITEM_IMAGE_HEIGHT: int = int(
    _get_config_value(
        config.get,
        "UI",
        "list_item_image_height",
        DEFAULT_SETTINGS["UI"]["list_item_image_height"],
        int,
    )
)

INITIAL_LOAD_COUNT: int = int(
    _get_config_value(
        config.get,
        "Performance",
        "initial_load_count",
        DEFAULT_SETTINGS["Performance"]["initial_load_count"],
        int,
    )
)

LOAD_BATCH_SIZE: int = int(
    _get_config_value(
        config.get,
        "Performance",
        "load_batch_size",
        DEFAULT_SETTINGS["Performance"]["load_batch_size"],
        int,
    )
)

LOAD_THRESHOLD_FACTOR: float = float(
    _get_config_value(
        config.get,
        "Performance",
        "load_threshold_factor",
        DEFAULT_SETTINGS["Performance"]["load_threshold_factor"],
        float,
    )
)

IMAGE_CACHE_MAX_SIZE: int = int(
    _get_config_value(
        config.get,
        "Performance",
        "image_cache_max_size",
        DEFAULT_SETTINGS["Performance"]["image_cache_max_size"],
        int,
    )
)

APP_CSS: str = """
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

log.debug(f"Using configuration directory: {CONFIG_DIR}")
log.debug(f"Using configuration file: {CONFIG_FILE_PATH}")
log.debug(f"History file path set to: {HISTORY_FILE_PATH}")
log.debug(f"Paste command set to: {PASTE_TOOL_CMD}")
