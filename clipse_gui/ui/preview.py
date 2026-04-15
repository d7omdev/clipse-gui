"""Preview window for clipboard items and in-preview search bar."""

import os

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango

from ..constants import (
    DEFAULT_PREVIEW_IMG_HEIGHT,
    DEFAULT_PREVIEW_IMG_WIDTH,
    DEFAULT_PREVIEW_TEXT_HEIGHT,
    DEFAULT_PREVIEW_TEXT_WIDTH,
)
from .text import _format_text_content


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
