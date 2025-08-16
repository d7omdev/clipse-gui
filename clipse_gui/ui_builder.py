from gi.repository import Gtk

import logging

from clipse_gui.constants import COMPACT_MODE

log = logging.getLogger(__name__)


def build_main_window_content() -> dict:
    """
    Creates the main UI elements and layout for the application window.

    Returns:
         A dictionary containing references to key widgets:
         {
             "main_box": Gtk.Box (the top-level container),
             "search_entry": Gtk.SearchEntry,
             "pin_filter_button": Gtk.ToggleButton,
             "compact_mode_button": Gtk.ToggleButton,
             "scrolled_window": Gtk.ScrolledWindow,
             "list_box": Gtk.ListBox,
             "status_label": Gtk.Label
         }
    """
    log.debug("Building main window UI content.")
    main_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL, spacing=5 if not COMPACT_MODE else 1
    )

    # Set margins based on compact mode
    margin = 1 if COMPACT_MODE else 10
    main_box.set_margin_top(margin)
    main_box.set_margin_bottom(margin)
    main_box.set_margin_start(margin)
    main_box.set_margin_end(margin)

    # --- Header ---
    header_box = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL, spacing=5 if not COMPACT_MODE else 1
    )
    search_entry = Gtk.SearchEntry(placeholder_text="Search...")
    header_box.pack_start(search_entry, True, True, 0)

    pin_filter_button = Gtk.ToggleButton(label="Pinned Only")
    if not COMPACT_MODE:
        header_box.pack_start(pin_filter_button, False, False, 0)

    compact_mode_button = Gtk.ToggleButton(label="Compact")
    # header_box.pack_start(compact_mode_button, False, False, 0)
    main_box.pack_start(header_box, False, False, 1 if COMPACT_MODE else 3)

    # --- List View ---
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    main_box.pack_start(scrolled_window, True, True, 0)

    # Viewport needed for adjustments with ListBox? Seems common.
    viewport = Gtk.Viewport()
    scrolled_window.add(viewport)

    list_box = Gtk.ListBox()
    list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
    viewport.add(list_box)

    # --- Status Bar ---
    status_label = Gtk.Label(label="Initializing...")
    status_label.set_halign(Gtk.Align.START)
    status_label.get_style_context().add_class("status-label")
    main_box.pack_end(status_label, False, False, 0)

    return {
        "main_box": main_box,
        "header_box": header_box,
        "search_entry": search_entry,
        "pin_filter_button": pin_filter_button,
        "compact_mode_button": compact_mode_button,
        "scrolled_window": scrolled_window,
        "list_box": list_box,
        "status_label": status_label,
    }
