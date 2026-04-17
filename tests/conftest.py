"""Shared fixtures for clipse-gui tests.

GTK 3 requires gi.require_version() before any gi.repository import.
This conftest runs early enough to satisfy that constraint.
"""

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GLib", "2.0")

from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402
from gi.repository import Gdk  # noqa: E402

from clipse_gui.controller_mixins.keyboard_mixin import KeyboardMixin  # noqa: E402


class FakeController(KeyboardMixin):
    """Minimal stand-in for ClipboardHistoryController.

    Provides every attribute / method that KeyboardMixin touches through
    ``self``.  Every mixin callback (toggle_selection_mode, etc.) is a
    MagicMock so tests can assert call counts without side effects.
    """

    def __init__(self):
        # ── GTK widget stubs ──────────────────────────────────────
        self.search_entry = MagicMock()
        self.search_entry.has_focus.return_value = False
        self.search_entry.get_text.return_value = ""
        self.search_entry.get_position.return_value = 0

        self.list_box = MagicMock()
        self.list_box.get_selected_row.return_value = None
        self.list_box.get_children.return_value = []
        self.list_box.get_row_at_index.return_value = None

        self.scrolled_window = MagicMock()
        self.window = MagicMock()
        self.window.get_focus.return_value = None
        self.window.get_application.return_value = MagicMock()

        self.pin_filter_button = MagicMock()
        self.pin_filter_button.get_active.return_value = False

        # ── State ─────────────────────────────────────────────────
        self.selection_mode = False
        self.selected_indices = set()
        self.zoom_level = 1.0
        self.compact_mode = False

        # ── Mixin callbacks (MagicMocks) ──────────────────────────
        self.toggle_selection_mode = MagicMock()
        self.toggle_item_selection = MagicMock()
        self.select_all_items = MagicMock()
        self.deselect_all_items = MagicMock()
        self.toggle_pin_selected = MagicMock()
        self.remove_selected_item = MagicMock()
        self.delete_selected_items = MagicMock()
        self.clear_all_items = MagicMock()
        self.show_item_preview = MagicMock()
        self.open_url_with_gtk = MagicMock()
        self.copy_selected_item_to_clipboard = MagicMock()
        self.update_zoom = MagicMock()
        self.update_compact_mode = MagicMock()
        self.update_style_css = MagicMock()
        self.on_help_window_close = MagicMock()
        self.on_settings_window_close = MagicMock()
        self.restart_application = MagicMock()


def make_event(keyval, ctrl=False, shift=False):
    """Build a fake Gdk.EventKey-like object."""
    event = MagicMock()
    event.keyval = keyval
    state = 0
    if ctrl:
        state |= Gdk.ModifierType.CONTROL_MASK
    if shift:
        state |= Gdk.ModifierType.SHIFT_MASK
    event.state = state
    return event


@pytest.fixture
def ctrl(request):
    """Provide a fresh FakeController for each test."""
    return FakeController()
