import os
import json
import logging
from gi.repository import Gtk, Gdk, Pango, GdkPixbuf, GLib

from .utils import format_date
from .constants import (
    LIST_ITEM_IMAGE_WIDTH,
    LIST_ITEM_IMAGE_HEIGHT,
    DEFAULT_PREVIEW_TEXT_WIDTH,
    DEFAULT_PREVIEW_TEXT_HEIGHT,
    DEFAULT_PREVIEW_IMG_WIDTH,
    DEFAULT_PREVIEW_IMG_HEIGHT,
    DEFAULT_HELP_WIDTH,
    DEFAULT_HELP_HEIGHT,
    PROTECT_PINNED_ITEMS,
    COMPACT_MODE,
    HOVER_TO_SELECT,
    ENTER_TO_PASTE,
    HIGHLIGHT_SEARCH,
    BORDER_RADIUS,
    ACCENT_COLOR,
    SELECTION_COLOR,
    VISUAL_MODE_COLOR,
    MINIMIZE_TO_TRAY,
    TRAY_ITEMS_COUNT,
    TRAY_PASTE_ON_SELECT,
    config,
)

log = logging.getLogger(__name__)

# SVG icon data for pushpin (rotated 25 degrees to the right for a natural look)
PIN_SVG_BASE = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <g transform="rotate({angle} 12 12)">
        <path d="M16,12V4H17V2H7V4H8V12L6,14V16H11.2V22H12.8V16H18V14L16,12Z"
              fill="currentColor" stroke="currentColor" stroke-width="0.5"/>
    </g>
</svg>
"""


def create_pin_icon(is_pinned, angle=25):
    """Creates a pin icon from SVG data with color based on pinned state."""
    try:
        # Replace currentColor with actual color
        color = "#ffcc00" if is_pinned else "rgba(255,255,255,0.25)"
        svg_data = PIN_SVG_BASE.replace("currentColor", color).replace(
            "{angle}", str(angle)
        )

        # Load SVG into pixbuf
        loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
        loader.write(svg_data.encode("utf-8"))
        loader.close()
        pixbuf = loader.get_pixbuf()

        # Create image from pixbuf
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        image.get_style_context().add_class("pin-icon")
        if is_pinned:
            image.get_style_context().add_class("pinned")
        else:
            image.get_style_context().add_class("unpinned")

        return image
    except Exception as e:
        log.error(f"Error creating pin icon: {e}")
        # Fallback to label
        label = Gtk.Label(label="📌")
        return label


def animate_pin_shake(container, is_pinned):
    """Animates a gentle rotation wiggle effect by recreating the icon at different angles."""
    # Gentle rotation sequence: base angle ± small rotations
    base_angle = 25
    rotation_sequence = [
        base_angle + 8,  # Rotate right
        base_angle - 8,  # Rotate left
        base_angle + 5,  # Rotate right (less)
        base_angle - 5,  # Rotate left (less)
        base_angle,  # Back to normal
    ]

    def apply_wiggle(index):
        if index < len(rotation_sequence):
            # Remove old icon
            children = container.get_children()
            if children:
                old_icon = children[-1]
                container.remove(old_icon)

            # Create new icon with rotated angle
            new_icon = create_pin_icon(is_pinned, rotation_sequence[index])
            new_icon.set_tooltip_text("Pinned" if is_pinned else "Not Pinned")
            new_icon.set_valign(Gtk.Align.START)  # Keep top alignment
            new_icon.set_margin_top(2)  # Keep top margin
            new_icon.show()
            container.pack_end(new_icon, False, False, 0)

            GLib.timeout_add(70, apply_wiggle, index + 1)
        return False

    apply_wiggle(0)


def escape_markup(text):
    """Escape special characters for Pango markup."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def highlight_search_term(text, search_term):
    """Highlight search term matches in text using Pango markup."""
    if not search_term or not search_term.strip():
        return escape_markup(text)
    
    search_lower = search_term.lower()
    text_lower = text.lower()
    
    result = []
    last_end = 0
    
    while True:
        idx = text_lower.find(search_lower, last_end)
        if idx == -1:
            break
        
        # Add text before match
        if idx > last_end:
            result.append(escape_markup(text[last_end:idx]))
        
        # Add highlighted match with inline background color
        match = text[idx:idx + len(search_term)]
        result.append(f'<span bgcolor="#ffcc00" fgcolor="#000000">{escape_markup(match)}</span>')
        
        last_end = idx + len(search_term)
    
    # Add remaining text
    if last_end < len(text):
        result.append(escape_markup(text[last_end:]))
    
    return "".join(result)


def create_list_row_widget(
    item_info,
    image_handler,
    update_image_callback,
    compact_mode=False,
    hover_to_select=False,
    single_click_callback=None,
    search_term="",
    highlight_search=False,
):
    """Creates a Gtk.ListBoxRow widget for a clipboard item."""
    original_index = item_info["original_index"]
    item = item_info["item"]
    filtered_index = item_info["filtered_index"]
    row = Gtk.ListBoxRow()
    row.item_index = original_index
    row.filtered_index = filtered_index
    row.item_value = item.get("value", "")
    row.item_pinned = item.get("pinned", False)
    row.file_path = item.get("filePath", "")
    row.is_image = item.get("filePath") not in [None, "null", ""]
    style_context = row.get_style_context()
    if row.item_pinned:
        style_context.add_class("pinned-row")
    style_context.add_class("list-row")

    # Use the passed compact mode parameter
    is_compact = compact_mode

    # Adjust sizes based on compact mode
    if is_compact:
        row.set_size_request(-1, 28)  # Compact but readable height
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.set_margin_top(1)
        vbox.set_margin_bottom(1)
        vbox.set_margin_start(1)
        vbox.set_margin_end(1)
    else:
        row.set_size_request(-1, 35)  # Reduced default height
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_top(2)
        vbox.set_margin_bottom(2)
        vbox.set_margin_start(3)
        vbox.set_margin_end(3)

    vbox.set_homogeneous(False)
    vbox.set_property("expand", False)

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)

    if row.is_image:
        image_path = item.get("filePath")
        image_container = Gtk.Frame()
        # Adjust image size based on compact mode
        if is_compact:
            image_container.set_size_request(
                int(LIST_ITEM_IMAGE_WIDTH * 0.3), int(LIST_ITEM_IMAGE_HEIGHT * 0.3)
            )
        else:
            image_container.set_size_request(
                int(LIST_ITEM_IMAGE_WIDTH * 0.8), int(LIST_ITEM_IMAGE_HEIGHT * 0.8)
            )
        image_container.set_shadow_type(Gtk.ShadowType.NONE)
        placeholder = Gtk.Label(label="[Loading image...]")
        placeholder.set_halign(Gtk.Align.CENTER)
        placeholder.set_valign(Gtk.Align.CENTER)
        image_container.add(placeholder)
        content_box.pack_start(image_container, False, False, 0)

        # Request image loading via the handler
        image_handler.load_image_async(
            image_path,
            image_container,
            placeholder,
            LIST_ITEM_IMAGE_WIDTH,
            LIST_ITEM_IMAGE_HEIGHT,
            update_image_callback,
        )

        title_label = Gtk.Label(label=os.path.basename(item.get("value", "Image")))
        title_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        title_label.set_max_width_chars(20)  # Reduced from 25
        title_label.set_halign(Gtk.Align.START)
        content_box.pack_start(title_label, False, False, 0)
    else:
        text_value = item.get("value", "")
        # Limit to 1 line in compact mode, 3 lines otherwise
        max_lines = 1 if is_compact else 3
        display_text = "\n".join(text_value.splitlines()[:max_lines])
        if len(text_value.splitlines()) > max_lines or len(display_text) > (
            80 if is_compact else 150
        ):
            cutoff = 80 if is_compact else 150
            last_space = display_text[:cutoff].rfind(" ")
            if last_space > cutoff * 0.8:
                cutoff = last_space
            display_text = display_text[:cutoff] + "..."

        label = Gtk.Label()
        # Apply search highlighting if enabled
        if highlight_search and search_term:
            marked_up = highlight_search_term(display_text, search_term)
            label.set_markup(marked_up)
        else:
            label.set_text(display_text)
        
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD)
        label.set_xalign(0)
        label.set_max_width_chars(
            35 if is_compact else 50
        )  # Reduced width in compact mode
        label.set_ellipsize(Pango.EllipsizeMode.END)

        # Adjust label size based on compact mode
        if is_compact:
            label.set_size_request(-1, 22)  # Compact but readable height
        else:
            label.set_size_request(-1, 30)

        content_box.pack_start(label, False, False, 0)

    # Ensure content box doesn't expand
    content_box.set_property("expand", False)

    hbox.pack_start(content_box, False, True, 0)

    # Use custom SVG pin icon
    pin_icon = create_pin_icon(row.item_pinned)
    pin_icon.set_tooltip_text("Pinned" if row.item_pinned else "Not Pinned")
    pin_icon.set_valign(Gtk.Align.START)  # Align to top
    pin_icon.set_margin_top(2)  # Small margin from the very top
    hbox.pack_end(pin_icon, False, False, 0)

    vbox.pack_start(hbox, False, False, 0)

    timestamp = format_date(item.get("recorded", ""))
    time_label = Gtk.Label(label=timestamp)
    time_label.set_halign(Gtk.Align.START)
    time_label.get_style_context().add_class("timestamp")
    vbox.pack_start(time_label, False, False, 0)

    row.add(vbox)

    # Add hover-to-select functionality if enabled
    if hover_to_select:
        # Add an EventBox to capture mouse events reliably
        event_box = Gtk.EventBox()
        event_box.set_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
        event_box.set_visible_window(False)  # Make it transparent

        # Move the vbox content into the event box
        row.remove(vbox)
        event_box.add(vbox)
        row.add(event_box)

        def on_enter_notify(widget, event):
            # Get the ListBoxRow parent
            listbox_row = widget.get_parent()  # EventBox -> ListBoxRow
            if listbox_row and isinstance(listbox_row, Gtk.ListBoxRow):
                listbox = listbox_row.get_parent()  # ListBoxRow -> ListBox
                if listbox and hasattr(listbox, "select_row"):
                    listbox.select_row(listbox_row)
            return False

        event_box.connect("enter-notify-event", on_enter_notify)

    # Add single-click support if callback provided
    if single_click_callback:

        def on_button_press(widget, event):
            # Single-click (left button) triggers paste
            if event.button == 1:  # Left mouse button
                # Check if it's a single click (not double-click)
                # Double-click is handled by row-activated signal
                if event.type == Gdk.EventType.BUTTON_PRESS:
                    single_click_callback(row)
                    return True  # Stop propagation
            return False

        row.connect("button-press-event", on_button_press)

    return row


# --- Help Window ---


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


def _create_section_frame(title):
    """Helper to create a framed section with a label."""
    frame = Gtk.Frame()
    frame.set_shadow_type(Gtk.ShadowType.NONE)

    label = Gtk.Label()
    label.set_markup(f"<b>{title}</b>")
    label.set_halign(Gtk.Align.START)
    frame.set_label_widget(label)

    frame.get_style_context().add_class("settings-section")

    return frame


def _create_setting_row(label_text, widget, tooltip=None):
    """Helper to create a setting row with label and widget."""
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    box.set_margin_start(10)
    box.set_margin_end(10)
    box.set_margin_top(5)
    box.set_margin_bottom(5)

    label = Gtk.Label(label=label_text)
    label.set_halign(Gtk.Align.START)
    label.set_hexpand(True)
    if tooltip:
        label.set_tooltip_text(tooltip)

    widget.set_halign(Gtk.Align.END)
    if tooltip:
        widget.set_tooltip_text(tooltip)

    box.pack_start(label, True, True, 0)
    box.pack_start(widget, False, False, 0)

    return box


def show_settings_window(parent_window, close_cb, restart_app_cb=None, 
                         update_style_cb=None, style_defaults=None):
    """Creates and shows the enhanced settings window with sections."""
    settings_window = Gtk.Window(title="Settings")
    settings_window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
    settings_window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
    settings_window.set_transient_for(parent_window)
    settings_window.set_default_size(500, 550)
    settings_window.set_border_width(15)

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

    # Header
    header = Gtk.Label()
    header.set_markup("<big><b>Settings</b></big>")
    header.set_halign(Gtk.Align.CENTER)
    header.set_margin_bottom(10)
    main_box.pack_start(header, False, False, 0)

    # Create notebook for tabs
    notebook = Gtk.Notebook()
    notebook.set_vexpand(True)

    # ============ GENERAL TAB ============
    general_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
    general_tab.set_margin_top(10)
    general_tab.set_margin_bottom(10)
    general_tab.set_margin_start(10)
    general_tab.set_margin_end(10)

    # General Section
    general_frame = _create_section_frame("General")
    general_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    general_box.set_margin_top(10)
    general_box.set_margin_bottom(10)

    # Compact Mode setting
    compact_switch = Gtk.Switch()
    compact_switch.set_active(COMPACT_MODE)
    compact_box = _create_setting_row(
        "Compact mode:",
        compact_switch,
        "Use a more compact layout with smaller margins",
    )

    # Hover to Select setting
    hover_switch = Gtk.Switch()
    hover_switch.set_active(HOVER_TO_SELECT)
    hover_box = _create_setting_row(
        "Hover to select:",
        hover_switch,
        "Select items by hovering over them with the mouse",
    )

    # Enter to Paste setting
    enter_paste_switch = Gtk.Switch()
    enter_paste_switch.set_active(ENTER_TO_PASTE)
    enter_paste_box = _create_setting_row(
        "Enter to paste:",
        enter_paste_switch,
        "Press Enter to paste the selected item and close the window",
    )

    # Highlight Search setting
    highlight_search_switch = Gtk.Switch()
    highlight_search_switch.set_active(HIGHLIGHT_SEARCH)
    highlight_search_box = _create_setting_row(
        "Highlight search:",
        highlight_search_switch,
        "Highlight matching search terms in the results list",
    )

    general_box.pack_start(compact_box, False, False, 0)
    general_box.pack_start(hover_box, False, False, 0)
    general_box.pack_start(enter_paste_box, False, False, 0)
    general_box.pack_start(highlight_search_box, False, False, 0)
    general_frame.add(general_box)
    general_tab.pack_start(general_frame, False, False, 0)

    # ============ CLIPBOARD SECTION ============
    clipboard_frame = _create_section_frame("Clipboard")
    clipboard_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    clipboard_box.set_margin_top(10)
    clipboard_box.set_margin_bottom(10)

    # Protect Pinned Items setting
    protect_switch = Gtk.Switch()
    protect_switch.set_active(PROTECT_PINNED_ITEMS)
    protect_box = _create_setting_row(
        "Protect pinned items:",
        protect_switch,
        "Prevent pinned items from being deleted when clearing history",
    )

    clipboard_box.pack_start(protect_box, False, False, 0)
    clipboard_frame.add(clipboard_box)
    general_tab.pack_start(clipboard_frame, False, False, 0)

    # ============ SYSTEM TRAY SECTION ============
    tray_frame = _create_section_frame("System Tray")
    tray_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    tray_box.set_margin_top(10)
    tray_box.set_margin_bottom(10)

    # Minimize to Tray setting
    tray_switch = Gtk.Switch()
    tray_switch.set_active(MINIMIZE_TO_TRAY)
    tray_enable_box = _create_setting_row(
        "Minimize to system tray:",
        tray_switch,
        "Keep the app running in the system tray when closing the window",
    )

    # Tray Items Count setting
    tray_items_spin = Gtk.SpinButton.new_with_range(5, 50, 1)
    tray_items_spin.set_value(TRAY_ITEMS_COUNT)
    tray_items_box = _create_setting_row(
        "Number of tray items:",
        tray_items_spin,
        "How many recent items to show in the system tray menu",
    )

    # Tray Paste on Select setting
    tray_paste_switch = Gtk.Switch()
    tray_paste_switch.set_active(TRAY_PASTE_ON_SELECT)
    tray_paste_box = _create_setting_row(
        "Paste on select from tray:",
        tray_paste_switch,
        "Automatically paste the item when selected from the tray menu",
    )

    tray_box.pack_start(tray_enable_box, False, False, 0)
    tray_box.pack_start(tray_items_box, False, False, 0)
    tray_box.pack_start(tray_paste_box, False, False, 0)
    tray_frame.add(tray_box)
    general_tab.pack_start(tray_frame, False, False, 0)

    # Add General tab to notebook
    general_scroll = Gtk.ScrolledWindow()
    general_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    general_scroll.add(general_tab)
    notebook.append_page(general_scroll, Gtk.Label(label="General"))

    # ============ STYLE TAB ============
    style_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
    style_tab.set_margin_top(10)
    style_tab.set_margin_bottom(10)
    style_tab.set_margin_start(10)
    style_tab.set_margin_end(10)

    # Appearance Section
    appearance_frame = _create_section_frame("Appearance")
    appearance_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    appearance_box.set_margin_top(10)
    appearance_box.set_margin_bottom(10)

    # Border Radius
    radius_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    radius_box.set_margin_start(10)
    radius_box.set_margin_end(10)
    radius_label = Gtk.Label(label="Border radius:")
    radius_label.set_halign(Gtk.Align.START)
    radius_label.set_hexpand(True)
    radius_spin = Gtk.SpinButton.new_with_range(0, 20, 1)
    radius_spin.set_value(BORDER_RADIUS)
    radius_box.pack_start(radius_label, True, True, 0)
    radius_box.pack_start(radius_spin, False, False, 0)
    appearance_box.pack_start(radius_box, False, False, 0)

    # Accent Color
    accent_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    accent_box.set_margin_start(10)
    accent_box.set_margin_end(10)
    accent_label = Gtk.Label(label="Accent color (pins):")
    accent_label.set_halign(Gtk.Align.START)
    accent_label.set_hexpand(True)
    accent_button = Gtk.ColorButton()
    accent_rgba = Gdk.RGBA()
    accent_rgba.parse(ACCENT_COLOR)
    accent_button.set_rgba(accent_rgba)
    accent_box.pack_start(accent_label, True, True, 0)
    accent_box.pack_start(accent_button, False, False, 0)
    appearance_box.pack_start(accent_box, False, False, 0)

    # Selection Color
    selection_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    selection_box.set_margin_start(10)
    selection_box.set_margin_end(10)
    selection_label = Gtk.Label(label="Selection color:")
    selection_label.set_halign(Gtk.Align.START)
    selection_label.set_hexpand(True)
    selection_button = Gtk.ColorButton()
    selection_rgba = Gdk.RGBA()
    selection_rgba.parse(SELECTION_COLOR)
    selection_button.set_rgba(selection_rgba)
    selection_box.pack_start(selection_label, True, True, 0)
    selection_box.pack_start(selection_button, False, False, 0)
    appearance_box.pack_start(selection_box, False, False, 0)

    # Visual Mode Color
    visual_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    visual_box.set_margin_start(10)
    visual_box.set_margin_end(10)
    visual_label = Gtk.Label(label="Visual mode color:")
    visual_label.set_halign(Gtk.Align.START)
    visual_label.set_hexpand(True)
    visual_button = Gtk.ColorButton()
    visual_rgba = Gdk.RGBA()
    visual_rgba.parse(VISUAL_MODE_COLOR)
    visual_button.set_rgba(visual_rgba)
    visual_box.pack_start(visual_label, True, True, 0)
    visual_box.pack_start(visual_button, False, False, 0)
    appearance_box.pack_start(visual_box, False, False, 0)

    # Reset button
    reset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    reset_box.set_margin_top(15)
    reset_box.set_margin_start(10)
    reset_box.set_margin_end(10)
    reset_btn = Gtk.Button(label="Reset to Defaults")
    reset_btn.set_tooltip_text("Reset all style settings to default values")
    reset_box.pack_start(reset_btn, True, True, 0)
    appearance_box.pack_start(reset_box, False, False, 0)

    appearance_frame.add(appearance_box)
    style_tab.pack_start(appearance_frame, False, False, 0)

    # Add Style tab to notebook
    style_scroll = Gtk.ScrolledWindow()
    style_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    style_scroll.add(style_tab)
    notebook.append_page(style_scroll, Gtk.Label(label="Style"))

    main_box.pack_start(notebook, True, True, 0)

    # Track changes
    settings_changed = False

    # Buttons
    button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    button_box.set_homogeneous(True)
    button_box.set_margin_top(10)

    # Apply & Restart button (initially disabled)
    apply_btn = Gtk.Button(label="Apply & Restart")
    apply_btn.set_sensitive(False)

    # Close button
    close_btn = Gtk.Button(label="Close")

    def update_button_states():
        """Update the state of buttons based on whether settings have changed."""
        apply_btn.set_sensitive(settings_changed)

    def on_protect_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "protect_pinned_items", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.PROTECT_PINNED_ITEMS = switch.get_active()

    def on_compact_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "compact_mode", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.COMPACT_MODE = switch.get_active()

    def on_hover_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "hover_to_select", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.HOVER_TO_SELECT = switch.get_active()

    def on_enter_paste_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "enter_to_paste", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.ENTER_TO_PASTE = switch.get_active()

    def on_highlight_search_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "highlight_search", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.HIGHLIGHT_SEARCH = switch.get_active()

    def on_tray_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "minimize_to_tray", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.MINIMIZE_TO_TRAY = switch.get_active()
        try:
            app = parent_window.get_application()
            if hasattr(app, "tray_manager") and app.tray_manager:
                app.tray_manager.set_tray_enabled(switch.get_active())
        except Exception as e:
            logging.debug(f"Could not update tray manager dynamically: {e}")

    def on_tray_items_changed(spin):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "tray_items_count", str(int(spin.get_value())))
        config._save_config()
        import clipse_gui.constants as constants

        constants.TRAY_ITEMS_COUNT = int(spin.get_value())

    def on_tray_paste_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "tray_paste_on_select", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.TRAY_PASTE_ON_SELECT = switch.get_active()

    # Style signal handlers
    def on_radius_changed(spin):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        value = int(spin.get_value())
        if not config.config.has_section("Style"):
            config.config.add_section("Style")
        config.config.set("Style", "border_radius", str(value))
        config._save_config()
        import clipse_gui.constants as constants
        constants.BORDER_RADIUS = value
        if update_style_cb:
            update_style_cb(border_radius=value)

    def on_accent_color_changed(button):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        rgba = button.get_rgba()
        color = f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
        if not config.config.has_section("Style"):
            config.config.add_section("Style")
        config.config.set("Style", "accent_color", color)
        config._save_config()
        import clipse_gui.constants as constants
        constants.ACCENT_COLOR = color
        if update_style_cb:
            update_style_cb(accent_color=color)

    def on_selection_color_changed(button):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        rgba = button.get_rgba()
        color = f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
        if not config.config.has_section("Style"):
            config.config.add_section("Style")
        config.config.set("Style", "selection_color", color)
        config._save_config()
        import clipse_gui.constants as constants
        constants.SELECTION_COLOR = color
        if update_style_cb:
            update_style_cb(selection_color=color)

    def on_visual_color_changed(button):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        rgba = button.get_rgba()
        color = f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
        if not config.config.has_section("Style"):
            config.config.add_section("Style")
        config.config.set("Style", "visual_mode_color", color)
        config._save_config()
        import clipse_gui.constants as constants
        constants.VISUAL_MODE_COLOR = color
        if update_style_cb:
            update_style_cb(visual_mode_color=color)

    def on_reset_styles(button):
        if not style_defaults:
            return
        # Reset to defaults
        radius_spin.set_value(style_defaults.get("border_radius", 6))
        
        accent_rgba = Gdk.RGBA()
        accent_rgba.parse(style_defaults.get("accent_color", "#ffcc00"))
        accent_button.set_rgba(accent_rgba)
        
        selection_rgba = Gdk.RGBA()
        selection_rgba.parse(style_defaults.get("selection_color", "#4a90e2"))
        selection_button.set_rgba(selection_rgba)
        
        visual_rgba = Gdk.RGBA()
        visual_rgba.parse(style_defaults.get("visual_mode_color", "#9b59b6"))
        visual_button.set_rgba(visual_rgba)
        
        # Save defaults to config
        if not config.config.has_section("Style"):
            config.config.add_section("Style")
        for key, value in style_defaults.items():
            config.config.set("Style", key, str(value))
        config._save_config()
        
        # Update constants and apply
        import clipse_gui.constants as constants
        constants.BORDER_RADIUS = style_defaults.get("border_radius", 6)
        constants.ACCENT_COLOR = style_defaults.get("accent_color", "#ffcc00")
        constants.SELECTION_COLOR = style_defaults.get("selection_color", "#4a90e2")
        constants.VISUAL_MODE_COLOR = style_defaults.get("visual_mode_color", "#9b59b6")
        
        if update_style_cb:
            update_style_cb(
                border_radius=constants.BORDER_RADIUS,
                accent_color=constants.ACCENT_COLOR,
                selection_color=constants.SELECTION_COLOR,
                visual_mode_color=constants.VISUAL_MODE_COLOR,
            )

    # Connect signals
    protect_switch.connect("state-set", on_protect_switch_toggled)
    compact_switch.connect("state-set", on_compact_switch_toggled)
    hover_switch.connect("state-set", on_hover_switch_toggled)
    enter_paste_switch.connect("state-set", on_enter_paste_switch_toggled)
    highlight_search_switch.connect("state-set", on_highlight_search_switch_toggled)
    tray_switch.connect("state-set", on_tray_switch_toggled)
    tray_items_spin.connect("value-changed", on_tray_items_changed)
    tray_paste_switch.connect("state-set", on_tray_paste_switch_toggled)
    
    # Style signals
    radius_spin.connect("value-changed", on_radius_changed)
    accent_button.connect("color-set", on_accent_color_changed)
    selection_button.connect("color-set", on_selection_color_changed)
    visual_button.connect("color-set", on_visual_color_changed)
    reset_btn.connect("clicked", on_reset_styles)

    def on_apply_clicked(button):
        settings_window.destroy()
        if restart_app_cb:
            restart_app_cb()

    apply_btn.connect("clicked", on_apply_clicked)

    def on_close_clicked(button):
        settings_window.destroy()
        if settings_changed and restart_app_cb:
            dialog = Gtk.MessageDialog(
                transient_for=settings_window,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Settings have been changed. Restart to apply changes?",
            )
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.YES:
                restart_app_cb()

    close_btn.connect("clicked", on_close_clicked)

    button_box.pack_start(apply_btn, True, True, 0)
    button_box.pack_start(close_btn, True, True, 0)
    main_box.pack_end(button_box, False, False, 0)

    settings_window.add(main_box)
    settings_window.connect(
        "key-press-event",
        lambda w, e: close_cb(w) if e.keyval == Gdk.KEY_Escape else None,
    )
    settings_window.show_all()
    close_btn.grab_focus()


# --- Preview Window ---


def show_preview_window(
    parent_window, item, is_image, change_text_size_cb, reset_text_size_cb, key_press_cb
):
    """Creates and shows the item preview window."""
    preview_window = Gtk.Window(title="Preview")
    preview_window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
    preview_window.set_transient_for(parent_window)
    preview_window.set_modal(True)
    preview_window.connect("key-press-event", key_press_cb)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    vbox.set_border_width(5)

    if is_image:
        image_path = item.get("filePath")
        if image_path and os.path.exists(image_path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
                if pixbuf is None:
                    raise GLib.Error(
                        GLib.ErrorDomain.G_FILE,
                        GLib.ErrorEnum.INVALID_ARGUMENT,
                    )

                image = Gtk.Image.new_from_pixbuf(pixbuf)
                image.set_halign(Gtk.Align.CENTER)
                image.set_valign(Gtk.Align.CENTER)

                display = parent_window.get_display()
                # Get GDK window from GTK window
                gdk_window = parent_window.get_window()
                monitor = (
                    display.get_monitor_at_window(gdk_window) if gdk_window else None
                )

                if monitor:
                    geometry = monitor.get_geometry()
                    max_w = geometry.width * 0.8
                    max_h = geometry.height * 0.8
                else:
                    max_w = 1200
                    max_h = 800

                img_w = pixbuf.get_width()
                img_h = pixbuf.get_height()
                # Calculate scaling while maintaining aspect ratio
                if img_w > max_w or img_h > max_h:
                    scale = min(max_w / img_w, max_h / img_h)
                    w = int(img_w * scale)
                    h = int(img_h * scale)
                else:
                    w = img_w
                    h = img_h

                # Create scaled pixbuf
                scaled_pixbuf = pixbuf.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
                image.set_from_pixbuf(scaled_pixbuf)

                preview_window.set_default_size(w, h)
                scrolled = Gtk.ScrolledWindow()
                scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
                scrolled.add(image)
                vbox.pack_start(scrolled, True, True, 0)

            except GLib.Error as e:
                label = Gtk.Label(label=f"Error loading image preview:\n{e.message}")
                label.set_line_wrap(True)
                label.set_halign(Gtk.Align.CENTER)
                label.set_valign(Gtk.Align.CENTER)
                vbox.pack_start(label, True, True, 0)
                preview_window.set_default_size(
                    DEFAULT_PREVIEW_IMG_WIDTH, DEFAULT_PREVIEW_IMG_HEIGHT
                )
    else:  # Text Preview
        text_value = item.get("value", "")
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)

        preview_text_view = Gtk.TextView()
        preview_text_view.get_buffer().set_text(text_value)
        preview_text_view.set_editable(False)
        preview_text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        context = preview_text_view.get_style_context()
        provider = Gtk.CssProvider()
        provider.load_from_data(b"textview { font-family: Monospace; }")
        context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        pango_context = preview_text_view.get_pango_context()
        if pango_context:
            font_desc = pango_context.get_font_description()
            if font_desc:
                base_font_size = font_desc.get_size() / Pango.SCALE
                if base_font_size <= 0:
                    base_font_size = 10
            else:
                base_font_size = 10
        else:
            base_font_size = 10
        preview_text_view.base_font_size = base_font_size

        scrolled_window.add(preview_text_view)
        vbox.pack_start(scrolled_window, True, True, 0)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        action_box.set_halign(Gtk.Align.CENTER)

        # Format button
        format_btn = Gtk.Button()
        format_btn.set_image(
            Gtk.Image.new_from_icon_name(
                "format-text-bold-symbolic",
                Gtk.IconSize.BUTTON,  # type: ignore
            )
        )
        format_btn.set_tooltip_text("Format text (pretty-print JSON) - Ctrl+B")
        format_btn.connect("clicked", lambda b: _format_text_content(preview_text_view))

        # Find button
        find_btn = Gtk.Button()
        find_btn.set_image(
            Gtk.Image.new_from_icon_name("edit-find-symbolic", Gtk.IconSize.BUTTON)  # type: ignore
        )
        find_btn.set_tooltip_text("Find text (Ctrl+F)")

        # Create enhanced search bar (initially hidden)
        search_bar = Gtk.SearchBar()

        # Create search container with entry and buttons
        search_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        search_container.set_margin_left(5)
        search_container.set_margin_right(5)
        search_container.set_margin_top(3)
        search_container.set_margin_bottom(3)

        # Search entry
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search text...")
        search_entry.set_hexpand(True)
        search_container.pack_start(search_entry, True, True, 0)

        # Match counter label
        match_label = Gtk.Label()
        match_label.set_text("0/0")
        match_label.set_margin_left(5)
        match_label.set_margin_right(5)
        search_container.pack_start(match_label, False, False, 0)

        # Previous button
        prev_btn = Gtk.Button()
        prev_btn.set_image(
            Gtk.Image.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)  # type: ignore
        )
        prev_btn.set_tooltip_text("Previous match (Shift+Enter)")
        search_container.pack_start(prev_btn, False, False, 0)

        # Next button
        next_btn = Gtk.Button()
        next_btn.set_image(
            Gtk.Image.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)  # type: ignore
        )
        next_btn.set_tooltip_text("Next match (Enter)")
        search_container.pack_start(next_btn, False, False, 0)

        # Close button
        close_btn = Gtk.Button()
        close_btn.set_image(
            Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)  # type: ignore
        )
        close_btn.set_tooltip_text("Close search (Escape)")
        search_container.pack_start(close_btn, False, False, 0)

        search_bar.add(search_container)
        search_bar.connect_entry(search_entry)

        # Insert search bar after scrolled window
        vbox.pack_start(search_bar, False, False, 0)
        vbox.reorder_child(search_bar, 1)  # Place after scrolled window

        find_btn.connect(
            "clicked",
            lambda b: _toggle_search_bar(
                search_bar,
                search_entry,
                preview_text_view,
                match_label,
                prev_btn,
                next_btn,
                close_btn,
            ),
        )

        # Zoom controls
        zoom_out = Gtk.Button()
        zoom_out.set_image(
            Gtk.Image.new_from_icon_name("zoom-out-symbolic", Gtk.IconSize.BUTTON)  # type: ignore
        )
        zoom_out.connect(
            "clicked", lambda b: change_text_size_cb(preview_text_view, -1)
        )
        zoom_in = Gtk.Button()
        zoom_in.set_image(
            Gtk.Image.new_from_icon_name("zoom-in-symbolic", Gtk.IconSize.BUTTON)  # type: ignore
        )
        zoom_in.connect("clicked", lambda b: change_text_size_cb(preview_text_view, 1))
        zoom_reset = Gtk.Button()
        zoom_reset.set_image(
            Gtk.Image.new_from_icon_name("zoom-original-symbolic", Gtk.IconSize.BUTTON)  # type: ignore
        )
        zoom_reset.connect("clicked", lambda b: reset_text_size_cb(preview_text_view))

        action_box.pack_start(format_btn, False, False, 0)
        action_box.pack_start(find_btn, False, False, 0)
        action_box.pack_start(
            Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 5
        )
        action_box.pack_start(Gtk.Label(label="Zoom:"), False, False, 0)
        action_box.pack_start(zoom_out, False, False, 0)
        action_box.pack_start(zoom_reset, False, False, 0)
        action_box.pack_start(zoom_in, False, False, 0)
        vbox.pack_end(action_box, False, False, 5)

        preview_window.set_default_size(
            DEFAULT_PREVIEW_TEXT_WIDTH, DEFAULT_PREVIEW_TEXT_HEIGHT
        )

    preview_window.add(vbox)
    preview_window.show_all()


def _format_text_content(text_view):
    """Formats the text content in the TextView, with special handling for JSON."""
    buffer = text_view.get_buffer()
    start, end = buffer.get_bounds()
    text = buffer.get_text(start, end, False)

    if not text.strip():
        return

    formatted_text = None

    # Try to format as JSON first
    try:
        # Remove any leading/trailing whitespace and check if it looks like JSON
        stripped_text = text.strip()
        if (stripped_text.startswith("{") and stripped_text.endswith("}")) or (
            stripped_text.startswith("[") and stripped_text.endswith("]")
        ):
            # Try to parse and format as JSON
            parsed_json = json.loads(stripped_text)
            formatted_text = json.dumps(
                parsed_json, indent=2, ensure_ascii=False, sort_keys=True
            )
    except (json.JSONDecodeError, ValueError):
        # Not valid JSON, try other formatting
        pass

    # If not JSON, try to format as other structured text
    if formatted_text is None:
        # Basic text formatting - normalize whitespace and line breaks
        lines = text.split("\n")
        formatted_lines = []

        for line in lines:
            # Remove excessive whitespace but preserve intentional indentation
            stripped = line.rstrip()
            if stripped:
                # Preserve leading whitespace for indentation
                leading_spaces = len(line) - len(line.lstrip())
                formatted_lines.append(" " * leading_spaces + stripped)
            else:
                formatted_lines.append("")

        # Remove excessive blank lines (more than 2 consecutive)
        result_lines = []
        blank_count = 0
        for line in formatted_lines:
            if line.strip() == "":
                blank_count += 1
                if blank_count <= 2:
                    result_lines.append(line)
            else:
                blank_count = 0
                result_lines.append(line)

        formatted_text = "\n".join(result_lines)

    # Update the buffer with formatted text
    if formatted_text and formatted_text != text:
        buffer.set_text(formatted_text)
        # Show a brief status message
        GLib.timeout_add(100, lambda: _flash_format_status(text_view, "Text formatted"))
    else:
        GLib.timeout_add(
            100, lambda: _flash_format_status(text_view, "No formatting applied")
        )


def _flash_format_status(text_view, message):
    """Shows a brief status message by temporarily changing the tooltip."""
    original_tooltip = text_view.get_tooltip_text()
    text_view.set_tooltip_text(message)

    def restore_tooltip():
        text_view.set_tooltip_text(original_tooltip)
        return False

    GLib.timeout_add(2000, restore_tooltip)
    return False


def _toggle_search_bar(
    search_bar,
    search_entry,
    text_view,
    match_label=None,
    prev_btn=None,
    next_btn=None,
    close_btn=None,
):
    """Toggles the enhanced search bar visibility and handles search functionality."""
    if search_bar.get_search_mode():
        # Hide search bar and clear highlights
        search_bar.set_search_mode(False)
        buffer = text_view.get_buffer()
        start, end = buffer.get_bounds()
        buffer.remove_all_tags(start, end)
    else:
        # Show search bar and focus entry
        search_bar.set_search_mode(True)
        search_entry.grab_focus()

        # Set up enhanced search functionality if not already done
        if not hasattr(search_entry, "_search_setup"):
            search_entry._search_setup = True
            search_entry._search_state = {
                "last_search": "",
                "matches": [],
                "current_index": 0,
                "highlight_tag": None,
                "current_tag": None,
            }

            def update_match_label():
                """Update the match counter label."""
                if match_label:
                    matches = search_entry._search_state["matches"]
                    if matches:
                        current = search_entry._search_state["current_index"] + 1
                        total = len(matches)
                        match_label.set_text(f"{current}/{total}")
                    else:
                        match_label.set_text("0/0")

            def perform_search():
                """Perform search and highlight all matches."""
                search_text = search_entry.get_text()
                buffer = text_view.get_buffer()
                start, end = buffer.get_bounds()

                # Clear previous highlights
                buffer.remove_all_tags(start, end)

                if not search_text:
                    search_entry._search_state["matches"] = []
                    update_match_label()
                    return

                content = buffer.get_text(start, end, False)

                # Find all matches (case insensitive)
                matches = []
                search_lower = search_text.lower()
                content_lower = content.lower()
                start_pos = 0

                while True:
                    pos = content_lower.find(search_lower, start_pos)
                    if pos == -1:
                        break
                    matches.append(pos)
                    start_pos = pos + 1

                search_entry._search_state["matches"] = matches

                if matches:
                    # Create highlight tags with different colors
                    if search_entry._search_state["highlight_tag"]:
                        buffer.get_tag_table().remove(
                            search_entry._search_state["highlight_tag"]
                        )
                    if search_entry._search_state["current_tag"]:
                        buffer.get_tag_table().remove(
                            search_entry._search_state["current_tag"]
                        )

                    # All matches - light blue background
                    highlight_tag = buffer.create_tag(
                        None, background="#87CEEB", foreground="black"
                    )
                    search_entry._search_state["highlight_tag"] = highlight_tag

                    # Current match - orange background
                    current_tag = buffer.create_tag(
                        None, background="#FFA500", foreground="black"
                    )
                    search_entry._search_state["current_tag"] = current_tag

                    # Highlight all matches
                    for match_pos in matches:
                        start_iter = buffer.get_iter_at_offset(match_pos)
                        end_iter = buffer.get_iter_at_offset(
                            match_pos + len(search_text)
                        )
                        buffer.apply_tag(highlight_tag, start_iter, end_iter)

                    # Jump to first match if this is a new search
                    if search_entry._search_state["last_search"] != search_text:
                        search_entry._search_state["current_index"] = 0
                        search_entry._search_state["last_search"] = search_text

                    highlight_current_match()

                update_match_label()

            def highlight_current_match():
                """Highlight the current match with a different color."""
                matches = search_entry._search_state["matches"]
                if not matches:
                    return

                current_index = search_entry._search_state["current_index"]
                current_match_pos = matches[current_index]
                search_text = search_entry.get_text()

                # Remove current highlight from all matches
                buffer = text_view.get_buffer()
                start, end = buffer.get_bounds()
                if search_entry._search_state["current_tag"]:
                    buffer.remove_tag(
                        search_entry._search_state["current_tag"], start, end
                    )

                # Highlight current match
                start_iter = buffer.get_iter_at_offset(current_match_pos)
                end_iter = buffer.get_iter_at_offset(
                    current_match_pos + len(search_text)
                )
                buffer.apply_tag(
                    search_entry._search_state["current_tag"], start_iter, end_iter
                )

                # Scroll to current match
                text_view.scroll_to_iter(start_iter, 0.0, False, 0.0, 0.0)
                buffer.place_cursor(start_iter)

                update_match_label()

            def find_next():
                """Go to next match."""
                matches = search_entry._search_state["matches"]
                if matches:
                    search_entry._search_state["current_index"] = (
                        search_entry._search_state["current_index"] + 1
                    ) % len(matches)
                    highlight_current_match()

            def find_previous():
                """Go to previous match."""
                matches = search_entry._search_state["matches"]
                if matches:
                    search_entry._search_state["current_index"] = (
                        search_entry._search_state["current_index"] - 1
                    ) % len(matches)
                    highlight_current_match()

            def close_search():
                """Close the search bar."""
                search_bar.set_search_mode(False)
                buffer = text_view.get_buffer()
                start, end = buffer.get_bounds()
                buffer.remove_all_tags(start, end)

            # Store functions on search_entry for access from button callbacks
            search_entry._find_next = find_next
            search_entry._find_previous = find_previous
            search_entry._close_search = close_search
            search_entry._perform_search = perform_search

            # Connect signals
            search_entry.connect("search-changed", lambda e: perform_search())
            search_entry.connect("activate", lambda e: find_next())

            # Handle keyboard shortcuts
            def on_key_press(widget, event):
                if event.keyval == Gdk.KEY_Escape:
                    close_search()
                    return True
                elif (
                    event.state & Gdk.ModifierType.SHIFT_MASK
                    and event.keyval == Gdk.KEY_Return
                ):
                    find_previous()
                    return True
                return False

            search_entry.connect("key-press-event", on_key_press)

        # Connect button signals every time (in case buttons were recreated)
        if next_btn and hasattr(search_entry, "_find_next"):
            # Disconnect all existing handlers to avoid duplicates
            try:
                if hasattr(next_btn, "_search_handler_ids"):
                    for handler_id in next_btn._search_handler_ids:
                        next_btn.disconnect(handler_id)
            except Exception:
                pass
            handler_id = next_btn.connect(
                "clicked", lambda b: search_entry._find_next()
            )
            next_btn._search_handler_ids = [handler_id]

        if prev_btn and hasattr(search_entry, "_find_previous"):
            try:
                if hasattr(prev_btn, "_search_handler_ids"):
                    for handler_id in prev_btn._search_handler_ids:
                        prev_btn.disconnect(handler_id)
            except Exception:
                pass
            handler_id = prev_btn.connect(
                "clicked", lambda b: search_entry._find_previous()
            )
            prev_btn._search_handler_ids = [handler_id]

        if close_btn and hasattr(search_entry, "_close_search"):
            try:
                if hasattr(close_btn, "_search_handler_ids"):
                    for handler_id in close_btn._search_handler_ids:
                        close_btn.disconnect(handler_id)
            except Exception:
                pass
            handler_id = close_btn.connect(
                "clicked", lambda b: search_entry._close_search()
            )
            close_btn._search_handler_ids = [handler_id]


# Legacy function alias for backward compatibility
toggle_search_bar = _toggle_search_bar
