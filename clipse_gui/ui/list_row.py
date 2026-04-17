"""List row widget creation for clipboard items (text, image, URL, SVG, data URI)."""

import os

from gi.repository import Gdk, Gtk, Pango

from ..constants import (
    LIST_ITEM_IMAGE_HEIGHT,
    LIST_ITEM_IMAGE_WIDTH,
    PREVIEW_RICH_CONTENT,
)
from ..utils import format_date
from .detection import _is_data_uri, _is_image_url, _is_svg_content, _is_url
from .icons import create_pin_icon
from .text import highlight_search_term


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

    # Detect special content types for text items
    text_value = item.get("value", "")
    row.is_url_image = False
    row.is_svg_content = False
    row.is_data_uri = False
    row.is_url = False
    row.image_url = None
    row.website_url = None
    if not row.is_image:
        if _is_image_url(text_value):
            row.is_url_image = True
            row.image_url = text_value.strip()
        elif _is_svg_content(text_value):
            row.is_svg_content = True
        elif _is_data_uri(text_value):
            row.is_data_uri = True
        elif _is_url(text_value):
            row.is_url = True
            row.website_url = text_value.strip()

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
    elif (row.is_url_image or row.is_data_uri) and PREVIEW_RICH_CONTENT:
        # Remote image URL or base64 data URI — show thumbnail
        thumb_w = int(LIST_ITEM_IMAGE_WIDTH * (0.3 if is_compact else 0.8))
        thumb_h = int(LIST_ITEM_IMAGE_HEIGHT * (0.3 if is_compact else 0.8))
        image_container = Gtk.Frame()
        image_container.set_shadow_type(Gtk.ShadowType.NONE)
        image_container.set_size_request(thumb_w, thumb_h)
        placeholder = Gtk.Label(label="…")
        placeholder.set_halign(Gtk.Align.CENTER)
        placeholder.set_valign(Gtk.Align.CENTER)
        image_container.add(placeholder)
        content_box.pack_start(image_container, False, False, 0)

        if row.is_data_uri:
            image_handler.load_data_uri_async(
                text_value.strip(), image_container, placeholder,
                LIST_ITEM_IMAGE_WIDTH, LIST_ITEM_IMAGE_HEIGHT, update_image_callback,
            )
        else:
            image_handler.load_remote_image_async(
                row.image_url, image_container, placeholder,
                LIST_ITEM_IMAGE_WIDTH, LIST_ITEM_IMAGE_HEIGHT, update_image_callback,
            )

        badge = Gtk.Label(label="[image url]" if row.is_url_image else "[base64]")
        badge.get_style_context().add_class("url-badge")
        badge.set_halign(Gtk.Align.START)
        content_box.pack_start(badge, False, False, 0)
    elif row.is_svg_content and PREVIEW_RICH_CONTENT:
        # Inline SVG — render as thumbnail
        thumb_w = int(LIST_ITEM_IMAGE_WIDTH * (0.3 if is_compact else 0.8))
        thumb_h = int(LIST_ITEM_IMAGE_HEIGHT * (0.3 if is_compact else 0.8))
        image_container = Gtk.Frame()
        image_container.set_shadow_type(Gtk.ShadowType.NONE)
        image_container.set_size_request(thumb_w, thumb_h)
        placeholder = Gtk.Label(label="…")
        placeholder.set_halign(Gtk.Align.CENTER)
        placeholder.set_valign(Gtk.Align.CENTER)
        image_container.add(placeholder)
        content_box.pack_start(image_container, False, False, 0)

        image_handler.load_svg_async(
            text_value.strip(), image_container, placeholder,
            LIST_ITEM_IMAGE_WIDTH, LIST_ITEM_IMAGE_HEIGHT, update_image_callback,
        )

        badge = Gtk.Label(label="[svg]")
        badge.get_style_context().add_class("url-badge")
        badge.set_halign(Gtk.Align.START)
        content_box.pack_start(badge, False, False, 0)
    elif row.is_url:
        # Regular URL — link icon + URL text
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        icon = Gtk.Image.new_from_icon_name("external-link-symbolic", Gtk.IconSize.MENU)
        icon.get_style_context().add_class("url-link")
        row_box.pack_start(icon, False, False, 0)
        max_chars = 50 if is_compact else 80
        display_url = text_value.strip()
        if len(display_url) > max_chars:
            display_url = display_url[:max_chars - 1] + "…"
        lbl = Gtk.Label(label=display_url)
        lbl.set_xalign(0)
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        lbl.get_style_context().add_class("url-link")
        row_box.pack_start(lbl, True, True, 0)
        content_box.pack_start(row_box, False, False, 0)
    else:
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
