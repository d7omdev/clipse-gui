"""Back-compat shim. Re-exports public names from the focused `ui/` modules.

New code should import directly from `clipse_gui.ui.<module>`. This shim exists
so existing internal imports (and the runtime `from .ui_components import ...`
calls in the controller) keep working unchanged.
"""

from .ui.detection import _is_data_uri, _is_image_url, _is_svg_content, _is_url
from .ui.help import show_help_window
from .ui.icons import animate_pin_shake, create_pin_icon
from .ui.list_row import create_list_row_widget
from .ui.preview import _toggle_search_bar, show_preview_window
from .ui.settings import _create_section_frame, _create_setting_row, show_settings_window
from .ui.text import (
    _flash_format_status,
    _format_text_content,
    escape_markup,
    highlight_search_term,
)

# Legacy alias preserved from the original module
toggle_search_bar = _toggle_search_bar

__all__ = [
    "_create_section_frame",
    "_create_setting_row",
    "_flash_format_status",
    "_format_text_content",
    "_is_data_uri",
    "_is_image_url",
    "_is_svg_content",
    "_is_url",
    "_toggle_search_bar",
    "animate_pin_shake",
    "create_list_row_widget",
    "create_pin_icon",
    "escape_markup",
    "highlight_search_term",
    "show_help_window",
    "show_preview_window",
    "show_settings_window",
    "toggle_search_bar",
]
