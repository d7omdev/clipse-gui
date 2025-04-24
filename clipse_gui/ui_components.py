import os
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
)

# --- List Row Creation ---


def create_list_row_widget(item_info, image_handler, update_image_callback):
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

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    vbox.set_margin_top(5)
    vbox.set_margin_bottom(5)
    vbox.set_margin_start(5)
    vbox.set_margin_end(5)

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

    if row.is_image:
        image_path = item.get("filePath")
        image_container = Gtk.Frame()
        image_container.set_size_request(LIST_ITEM_IMAGE_WIDTH, LIST_ITEM_IMAGE_HEIGHT)
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
        title_label.set_max_width_chars(30)
        title_label.set_halign(Gtk.Align.START)
        content_box.pack_start(title_label, False, False, 0)
    else:  # Text Item
        text_value = item.get("value", "")
        display_text = "\n".join(text_value.splitlines()[:5])
        if len(text_value.splitlines()) > 5 or len(display_text) > 200:
            cutoff = 200
            last_space = display_text[:cutoff].rfind(" ")
            if last_space > cutoff * 0.8:
                cutoff = last_space
            display_text = display_text[:cutoff] + "..."

        label = Gtk.Label(label=display_text)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD)
        label.set_xalign(0)
        label.set_max_width_chars(60)
        content_box.pack_start(label, True, True, 0)

    hbox.pack_start(content_box, True, True, 0)

    pin_icon = Gtk.Image.new_from_icon_name(
        "starred" if row.item_pinned else "non-starred-symbolic", Gtk.IconSize.MENU
    )
    pin_icon.set_tooltip_text("Pinned" if row.item_pinned else "Not Pinned")
    hbox.pack_end(pin_icon, False, False, 0)

    vbox.pack_start(hbox, True, True, 0)

    timestamp = format_date(item.get("recorded", ""))
    time_label = Gtk.Label(label=timestamp)
    time_label.set_halign(Gtk.Align.START)
    time_label.get_style_context().add_class("timestamp")
    vbox.pack_start(time_label, False, False, 0)

    row.add(vbox)
    return row


# --- Help Window ---


def show_help_window(parent_window, close_cb):
    """Creates and shows the keyboard shortcuts help window."""
    help_window = Gtk.Window(title="Keyboard Shortcuts")
    help_window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
    help_window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
    help_window.set_transient_for(parent_window)
    help_window.set_default_size(DEFAULT_HELP_WIDTH, DEFAULT_HELP_HEIGHT)
    help_window.set_border_width(10)

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    content_box.set_margin_start(10)
    content_box.set_margin_end(10)
    header = Gtk.Label()
    header.set_markup("<b>Keyboard Shortcuts</b>")
    header.set_halign(Gtk.Align.CENTER)
    content_box.pack_start(header, False, False, 10)

    mappings = [
        ("Slash / f", "Focus search field"),
        ("Esc", "Clear search / Close Preview / Close Help / Quit App (main)"),
        ("↑ / k", "Navigate Up"),
        ("↓ / j", "Navigate Down"),
        ("PgUp", "Scroll Page Up"),
        ("PgDn", "Scroll Page Down"),
        ("Home", "Go to Top"),
        ("End", "Go to Bottom (of loaded items)"),
        ("Enter", "Copy selected item to clipboard"),
        ("Space", "Show full item preview"),
        ("p", "Toggle pin status for selected item"),
        ("x / Del", "Delete selected item"),
        ("Tab", "Toggle 'Pinned Only' filter"),
        ("Ctrl +", "Zoom In main list"),
        ("Ctrl -", "Zoom Out main list"),
        ("Ctrl 0", "Reset Zoom main list"),
        ("?", "Show this help window"),
        ("Ctrl+Q", "Quit application"),
    ]

    grid = Gtk.Grid()
    grid.set_column_spacing(20)
    grid.set_row_spacing(8)
    grid.set_margin_bottom(10)
    for i, (key, desc) in enumerate(mappings):
        key_label = Gtk.Label(label=key)
        key_label.set_halign(Gtk.Align.START)
        key_label.get_style_context().add_class("key-shortcut")
        desc_label = Gtk.Label(label=desc)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_line_wrap(True)
        grid.attach(key_label, 0, i, 1, 1)
        grid.attach(desc_label, 1, i, 1, 1)

    content_box.pack_start(grid, False, False, 0)
    scrolled.add(content_box)
    close_btn = Gtk.Button(label="Close")
    close_btn.set_margin_top(10)
    close_btn.connect("clicked", lambda b: help_window.destroy())
    main_box.pack_start(scrolled, True, True, 0)
    main_box.pack_end(close_btn, False, False, 0)

    help_window.add(main_box)
    help_window.connect(
        "key-press-event",
        lambda w, e: close_cb(w) if e.keyval == Gdk.KEY_Escape else None,
    )
    help_window.show_all()
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
        zoom_out = Gtk.Button.new_from_icon_name(
            "zoom-out-symbolic", Gtk.IconSize.BUTTON
        )
        zoom_out.connect(
            "clicked", lambda b: change_text_size_cb(preview_text_view, -1)
        )
        zoom_in = Gtk.Button.new_from_icon_name("zoom-in-symbolic", Gtk.IconSize.BUTTON)
        zoom_in.connect("clicked", lambda b: change_text_size_cb(preview_text_view, 1))
        zoom_reset = Gtk.Button.new_from_icon_name(
            "zoom-original-symbolic", Gtk.IconSize.BUTTON
        )
        zoom_reset.connect("clicked", lambda b: reset_text_size_cb(preview_text_view))
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
