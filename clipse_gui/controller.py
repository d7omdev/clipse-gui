"""Main application controller.

Thin assembler that composes domain-specific mixins from `controller_mixins/`.
Holds only `__init__` (state + widget wiring) and `_connect_signals` (event wiring).
All behavior lives in the mixins.
"""

import logging
import os
import threading

from gi.repository import GLib, Gtk

from .constants import HOVER_TO_SELECT, IMAGE_CACHE_MAX_SIZE, config
from .controller_mixins import (
    ClipboardMixin,
    DataMixin,
    ItemOpsMixin,
    KeyboardMixin,
    ListViewMixin,
    MiscMixin,
    PreviewMixin,
    ScrollMixin,
    SearchMixin,
    SelectionMixin,
    StyleMixin,
)
from .data_manager import DataManager
from .image_handler import ImageHandler
from .ui_builder import build_main_window_content

log = logging.getLogger(__name__)


class ClipboardHistoryController(
    DataMixin,
    StyleMixin,
    ListViewMixin,
    SearchMixin,
    ItemOpsMixin,
    SelectionMixin,
    ClipboardMixin,
    PreviewMixin,
    ScrollMixin,
    KeyboardMixin,
    MiscMixin,
):
    """
    Manages the application logic, state, and interactions for the main window.
    """

    def __init__(self, application_window: Gtk.ApplicationWindow):
        self.window = application_window
        self.items = []
        self.filtered_items = []
        self.show_only_pinned = False
        self.zoom_level = 1.0
        self.search_term = ""
        self.compact_mode = config.getboolean("General", "compact_mode", fallback=False)
        self.hover_to_select = HOVER_TO_SELECT
        self.selection_mode = False
        self.selected_indices = set()

        self._loading_more = False
        self._save_timer_id = None
        self._search_timer_id = None
        self._vadjustment_handler_id = None
        self._is_wayland = "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower()
        log.debug(f"Detected session type: {'Wayland' if self._is_wayland else 'X11'}")

        self.data_manager = DataManager(update_callback=self._on_history_updated)
        self.image_handler = ImageHandler(IMAGE_CACHE_MAX_SIZE or 50)

        ui_elements = build_main_window_content()
        self.main_box = ui_elements["main_box"]
        self.main_box.get_style_context().add_class("main-window")
        self.search_entry = ui_elements["search_entry"]
        self.pin_filter_button = ui_elements["pin_filter_button"]
        self.compact_mode_button = ui_elements["compact_mode_button"]
        self.scrolled_window = ui_elements["scrolled_window"]
        self.list_box = ui_elements["list_box"]
        self.status_label = ui_elements["status_label"]
        self.selection_mode_banner = ui_elements["selection_mode_banner"]
        self.vadj = self.scrolled_window.get_vadjustment()

        # Hint overlay removed - not needed

        # Set initial compact mode button state
        self.compact_mode_button.set_active(self.compact_mode)

        # Hide search entry if in compact mode after window is realized
        if self.compact_mode:

            def hide_search_entry():
                self.search_entry.hide()
                return False

            GLib.idle_add(hide_search_entry)

        self.window.add(self.main_box)

        self._connect_signals()

        self.status_label.set_text("Loading history...")
        threading.Thread(target=self._load_initial_data, daemon=True).start()

        self._apply_css()
        self.update_compact_mode(skip_populate=True)

    def _connect_signals(self):
        """Connects GTK signals to their handler methods."""
        log.debug("Connecting signals.")
        self.window.connect("key-press-event", self.on_key_press)
        self.window.connect("destroy", self.on_window_destroy)

        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("focus-out-event", self.on_search_focus_out)
        self.pin_filter_button.connect("toggled", self.on_pin_filter_toggled)
        self.compact_mode_button.connect("toggled", self.on_compact_mode_toggled)
        self.list_box.connect("row-activated", self.on_row_activated)
        self.list_box.connect("size-allocate", self.on_list_box_size_allocate)

        if self.vadj:
            self._vadjustment_handler_id = self.vadj.connect(
                "value-changed", self.on_vadjustment_changed
            )
        else:
            log.warning("Could not get vertical adjustment for lazy loading.")
