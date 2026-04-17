"""Help window with keyboard shortcuts reference."""

from gi.repository import Gdk, Gtk

from ..constants import DEFAULT_HELP_HEIGHT, DEFAULT_HELP_WIDTH


def show_help_window(parent_window, close_cb):
    """Creates and shows the keyboard shortcuts help window."""
    help_window = Gtk.Window(title="Keyboard Shortcuts")
    help_window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
    help_window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
    help_window.set_transient_for(parent_window)
    help_window.set_default_size(DEFAULT_HELP_WIDTH, DEFAULT_HELP_HEIGHT)
    help_window.set_border_width(20)

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)

    # Header
    header = Gtk.Label()
    header.set_markup("<span size='x-large' weight='bold'>Keyboard Shortcuts</span>")
    header.set_halign(Gtk.Align.CENTER)
    header.set_margin_bottom(10)
    main_box.pack_start(header, False, False, 0)

    # Scrolled window for content
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    # Main grid for table-like layout
    main_grid = Gtk.Grid()
    main_grid.set_column_spacing(30)
    main_grid.set_row_spacing(4)
    main_grid.set_margin_start(25)
    main_grid.set_margin_end(25)
    main_grid.set_margin_top(15)
    main_grid.set_margin_bottom(15)

    # Define all shortcuts in order with section headers
    shortcuts_data = [
        # Navigation
        ("NAVIGATION", None, True),
        ("Slash / f", "Focus search field", False),
        ("↑ / k", "Navigate up", False),
        ("↓ / j", "Navigate down", False),
        ("PgUp", "Scroll page up", False),
        ("PgDn", "Scroll page down", False),
        ("Home", "Go to top", False),
        ("End", "Go to bottom (of loaded items)", False),
        ("Tab", "Toggle 'Pinned Only' filter", False),
        ("", None, False),  # Spacer
        # Actions
        ("ACTIONS", None, True),
        ("Enter", "Copy selected item to clipboard", False),
        ("Shift+Enter", "Copy & paste selected item", False),
        ("Space", "Show full preview", False),
        ("p", "Toggle pin status", False),
        ("x / Del", "Delete selected item", False),
        ("", None, False),  # Spacer
        # Multi-Select Mode
        ("MULTI-SELECT MODE", None, True),
        ("v", "Toggle selection mode", False),
        ("Space", "Toggle item selection (in selection mode)", False),
        ("Ctrl+A", "Select all visible items", False),
        ("Ctrl+Shift+A", "Deselect all items", False),
        ("Ctrl+X / Shift+Del", "Delete selected items", False),
        ("Ctrl+Shift+Del / Ctrl+D", "Clear all non-pinned items", False),
        ("", None, False),  # Spacer
        # View
        ("VIEW", None, True),
        ("Ctrl +", "Zoom in", False),
        ("Ctrl -", "Zoom out", False),
        ("Ctrl 0", "Reset zoom", False),
        ("", None, False),  # Spacer
        # Preview Window
        ("PREVIEW WINDOW", None, True),
        ("Ctrl+F", "Find text in preview", False),
        ("Ctrl+B", "Format text (pretty-print JSON)", False),
        ("Ctrl+C", "Copy text from preview", False),
        ("", None, False),  # Spacer
        # General
        ("GENERAL", None, True),
        ("?", "Show this help window", False),
        ("Ctrl+,", "Open settings", False),
        ("Esc", "Clear search / Close window / Exit mode", False),
        ("Ctrl+Q", "Quit application", False),
    ]

    row = 0
    for key, desc, is_header in shortcuts_data:
        if is_header:
            # Section header
            header_label = Gtk.Label()
            header_label.set_markup(
                f"<span weight='bold' size='large' foreground='#4a90e2'>{key}</span>"
            )
            header_label.set_halign(Gtk.Align.START)
            header_label.set_margin_top(10 if row > 0 else 0)
            header_label.set_margin_bottom(8)
            main_grid.attach(header_label, 0, row, 2, 1)
            row += 1
        elif key == "":
            # Spacer row
            spacer = Gtk.Label(label="")
            spacer.set_size_request(-1, 10)
            main_grid.attach(spacer, 0, row, 2, 1)
            row += 1
        else:
            # Regular shortcut row
            key_label = Gtk.Label(label=key)
            key_label.set_halign(Gtk.Align.START)
            key_label.set_margin_end(25)
            key_label.get_style_context().add_class("key-shortcut")

            desc_label = Gtk.Label(label=desc)
            desc_label.set_halign(Gtk.Align.START)
            desc_label.set_line_wrap(False)
            desc_label.set_xalign(0)

            main_grid.attach(key_label, 0, row, 1, 1)
            main_grid.attach(desc_label, 1, row, 1, 1)
            row += 1

    scrolled.add(main_grid)
    main_box.pack_start(scrolled, True, True, 0)

    # Close button
    close_btn = Gtk.Button(label="Close")
    close_btn.set_margin_top(10)
    close_btn.connect("clicked", lambda b: help_window.destroy())
    main_box.pack_end(close_btn, False, False, 0)

    help_window.add(main_box)
    help_window.connect(
        "key-press-event",
        lambda w, e: close_cb(w) if e.keyval == Gdk.KEY_Escape else None,
    )
    help_window.show_all()
    close_btn.grab_focus()
