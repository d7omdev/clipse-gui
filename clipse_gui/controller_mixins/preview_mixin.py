"""Preview window dispatch and in-preview key handling."""

import logging

from gi.repository import Gdk, Gtk, Pango

from ..ui_components import show_preview_window

log = logging.getLogger(__name__)


class PreviewMixin:
    def open_url_with_gtk(self, url):
        """Open a URL using Gtk.show_uri_on_window (respects the user's default browser)."""
        try:
            log.info(f"Opening URL: {url}")
            Gtk.show_uri_on_window(None, url, Gdk.CURRENT_TIME)
            self.flash_status(f"Opening: {url[:60]}…", duration=2000)
        except Exception as e:
            log.error(f"Failed to open URL: {e}")
            self.flash_status(f"Error opening URL: {e}")

    def show_item_preview(self):
        """Shows the preview window for the selected item."""
        selected_row = self.list_box.get_selected_row()
        if not selected_row:
            return

        original_index = getattr(selected_row, "item_index", -1)
        file_path_attr = getattr(selected_row, "file_path", None)
        is_image = file_path_attr is not None and file_path_attr != "null"

        if original_index == -1:
            log.error("Preview called on row with invalid item_index.")
            self.flash_status("Error: Invalid selected item data.")
            return

        try:
            if not (0 <= original_index < len(self.items)):
                log.error(
                    f"Item with original index {original_index} no longer exists for preview."
                )
                self.flash_status("Error: Selected item no longer exists.")
                return

            item = self.items[original_index]

            show_preview_window(
                self.window,
                item,
                is_image,
                self.change_preview_text_size,
                self.reset_preview_text_size,
                self.on_preview_key_press,
            )
        except Exception as e:
            log.error(f"Error creating preview window: {e}", exc_info=True)
            self.flash_status(f"Error showing preview: {str(e)}")

    # --- Preview Window Callbacks ---

    def change_preview_text_size(self, text_view, delta):
        """Callback to change font size in the preview TextView."""
        try:
            pango_context = text_view.get_pango_context()
            font_desc = pango_context.get_font_description() or Pango.FontDescription()
            if (
                not hasattr(text_view, "base_font_size")
                or text_view.base_font_size <= 0
            ):
                base_size_pango = font_desc.get_size()
                text_view.base_font_size = (
                    (base_size_pango / Pango.SCALE) if base_size_pango > 0 else 10.0
                )
            current_size_pts = font_desc.get_size() / Pango.SCALE
            if current_size_pts <= 0:
                current_size_pts = text_view.base_font_size
            new_size_pts = max(4.0, current_size_pts + delta)
            font_desc.set_size(int(new_size_pts * Pango.SCALE))
            text_view.override_font(font_desc)
        except Exception as e:
            log.error(f"Error changing preview text size: {e}")

    def reset_preview_text_size(self, text_view):
        """Callback to reset font size in the preview TextView."""
        try:
            text_view.override_font(None)
            pango_context = text_view.get_pango_context()
            font_desc = pango_context.get_font_description() or Pango.FontDescription()
            if hasattr(text_view, "base_font_size") and text_view.base_font_size > 0:
                font_desc.set_size(int(text_view.base_font_size * Pango.SCALE))
                text_view.override_font(font_desc)
        except Exception as e:
            log.error(f"Error resetting preview text size: {e}")

    def on_help_window_close(self, window):
        """Callback for when the help window is closed."""
        window.destroy()
        if self.window:
            self.window.present()
            if self.list_box:
                self.list_box.grab_focus()
            else:
                self.window.grab_focus()

    def on_settings_window_close(self, window):
        """Callback for when the settings window is closed."""
        window.destroy()
        if self.window:
            self.window.present()
            if self.list_box:
                self.list_box.grab_focus()
            else:
                self.window.grab_focus()

    def on_preview_key_press(self, preview_window, event):
        """Handles key presses within the preview window."""
        keyval = event.keyval
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK

        if keyval == Gdk.KEY_Escape or (ctrl and keyval == Gdk.KEY_w):
            preview_window.destroy()
            if self.window:
                self.window.present()
                if self.list_box:
                    self.list_box.grab_focus()
            return True

        def find_textview(widget):
            if isinstance(widget, Gtk.TextView):
                return widget
            if hasattr(widget, "get_children"):
                for child in widget.get_children():
                    found = find_textview(child)
                    if found:
                        return found
            if hasattr(widget, "get_child"):
                child = widget.get_child()
                if child:
                    return find_textview(child)
            return None

        textview = find_textview(preview_window)

        if textview:
            if ctrl and keyval == Gdk.KEY_f:
                # Find search bar and toggle it
                def find_search_bar(widget):
                    if isinstance(widget, Gtk.SearchBar):
                        return widget
                    if hasattr(widget, "get_children"):
                        for child in widget.get_children():
                            result = find_search_bar(child)
                            if result:
                                return result
                    return None

                search_bar = find_search_bar(preview_window)
                if search_bar:
                    # Find the search entry
                    def find_search_entry(widget):
                        if isinstance(widget, Gtk.SearchEntry):
                            return widget
                        if hasattr(widget, "get_children"):
                            for child in widget.get_children():
                                result = find_search_entry(child)
                                if result:
                                    return result
                        return None

                    def find_buttons_and_label(widget):
                        """Find prev, next, close buttons and match label."""
                        prev_btn = next_btn = close_btn = match_label = None

                        def search_widget(w):
                            nonlocal prev_btn, next_btn, close_btn, match_label
                            if isinstance(w, Gtk.Button):
                                tooltip = w.get_tooltip_text() or ""
                                if "Previous" in tooltip:
                                    prev_btn = w
                                elif "Next" in tooltip:
                                    next_btn = w
                                elif "Close" in tooltip:
                                    close_btn = w
                            elif isinstance(w, Gtk.Label):
                                text = w.get_text()
                                if "/" in text or text in ["0/0", ""]:
                                    match_label = w

                            if hasattr(w, "get_children"):
                                for child in w.get_children():
                                    search_widget(child)

                        search_widget(widget)
                        return prev_btn, next_btn, close_btn, match_label

                    search_entry = find_search_entry(search_bar)
                    if search_entry:
                        from ..ui_components import _toggle_search_bar

                        # Find buttons and label
                        prev_btn, next_btn, close_btn, match_label = (
                            find_buttons_and_label(preview_window)
                        )

                        _toggle_search_bar(
                            search_bar,
                            search_entry,
                            textview,
                            match_label,
                            prev_btn,
                            next_btn,
                            close_btn,
                        )
                return True
            if ctrl and keyval == Gdk.KEY_b:
                # Format text with Ctrl+B
                from ..ui_components import _format_text_content

                _format_text_content(textview)
                return True
            if ctrl and keyval == Gdk.KEY_c:
                buffer = textview.get_buffer()
                clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                if buffer.get_has_selection():
                    buffer.copy_clipboard(clipboard)
                    self.flash_status("Selection copied from preview", duration=1500)
                else:
                    start, end = buffer.get_bounds()
                    buffer.select_range(start, end)
                    buffer.copy_clipboard(clipboard)
                    buffer.delete_selection(False, False)
                    self.flash_status("All text copied from preview", duration=1500)
                return True
            if ctrl and keyval in [Gdk.KEY_plus, Gdk.KEY_equal]:
                self.change_preview_text_size(textview, 1.0)
                return True
            if ctrl and keyval == Gdk.KEY_minus:
                self.change_preview_text_size(textview, -1.0)
                return True
            if ctrl and keyval == Gdk.KEY_0:
                self.reset_preview_text_size(textview)
                return True
        return False
