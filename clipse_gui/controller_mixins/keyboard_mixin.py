"""Main keyboard event handler and row activation callbacks."""

import logging

from gi.repository import Gdk, GLib, Gtk

from ..constants import ENTER_TO_PASTE, OPEN_LINKS_WITH_BROWSER, config
from ..ui_components import show_help_window, show_settings_window

log = logging.getLogger(__name__)


class KeyboardMixin:
    def on_key_press(self, widget, event):
        """Handles key presses on the main window."""
        keyval = event.keyval
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK

        if self.search_entry.has_focus():
            if keyval == Gdk.KEY_Escape:
                # Priority order: exit selection mode -> clear search + unfocus
                if self.selection_mode:
                    self.toggle_selection_mode()
                    return True

                # Clear search text if present
                if self.search_entry.get_text():
                    self.search_entry.set_text("")

                # Unfocus search entry and focus first list item (deferred)
                def unfocus_search():
                    if self.list_box:
                        # Select and focus first row
                        first_row = self.list_box.get_row_at_index(0)
                        if first_row:
                            self.list_box.select_row(first_row)
                            first_row.grab_focus()
                        else:
                            self.list_box.grab_focus()
                    else:
                        self.window.grab_focus()
                    return False
                GLib.idle_add(unfocus_search)
                return True

            if keyval in [Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Page_Up, Gdk.KEY_Page_Down]:
                focusable_elements = self.list_box.get_children()
                if not focusable_elements:
                    return False

                current_focus = self.window.get_focus()
                current_index = (
                    focusable_elements.index(current_focus)
                    if current_focus in focusable_elements
                    else -1
                )

                target_index = current_index
                if keyval == Gdk.KEY_Down:
                    target_index = 0 if current_index == -1 else current_index + 1
                elif keyval == Gdk.KEY_Up:
                    target_index = (
                        len(focusable_elements) - 1
                        if current_index == -1
                        else current_index - 1
                    )
                elif keyval == Gdk.KEY_Page_Down:
                    target_index = (
                        0
                        if current_index == -1
                        else min(current_index + 5, len(focusable_elements) - 1)
                    )
                elif keyval == Gdk.KEY_Page_Up:
                    target_index = (
                        len(focusable_elements) - 1
                        if current_index == -1
                        else max(current_index - 5, 0)
                    )

                if 0 <= target_index < len(focusable_elements):
                    row = focusable_elements[target_index]
                    self.list_box.select_row(row)
                    row.grab_focus()
                    allocation = row.get_allocation()
                    adj = self.scrolled_window.get_vadjustment()
                    if adj:
                        adj.set_value(
                            min(allocation.y, adj.get_upper() - adj.get_page_size())
                        )
                    return True

                return False

            # When search entry has focus, insert bound keys as text instead of
            # triggering their global actions. Let all other keys pass through normally.
            key_to_char = {
                Gdk.KEY_v: "v",
                Gdk.KEY_x: "x",
                Gdk.KEY_p: "p",
                Gdk.KEY_j: "j",
                Gdk.KEY_k: "k",
                Gdk.KEY_f: "f",
                Gdk.KEY_slash: "/",
                Gdk.KEY_question: "?",
                Gdk.KEY_space: " ",
            }

            if keyval in key_to_char:
                # Insert the character into the search entry
                char = key_to_char[keyval]
                current_text = self.search_entry.get_text()
                # Get cursor position (if available) or append to end
                if hasattr(self.search_entry, 'get_position'):
                    pos = self.search_entry.get_position()
                    new_text = current_text[:pos] + char + current_text[pos:]
                    self.search_entry.set_text(new_text)
                    self.search_entry.set_position(pos + 1)
                else:
                    self.search_entry.set_text(current_text + char)
                return True  # Block the global action

            # Block Tab and Return from triggering actions, but don't insert them
            if keyval in (Gdk.KEY_Tab, Gdk.KEY_Return):
                return True

            # Let all other keys pass through normally
            return False

        selected_row = self.list_box.get_selected_row()

        if keyval == Gdk.KEY_Return:
            if selected_row:
                self.on_row_activated(self.list_box, shift and not ENTER_TO_PASTE)
            elif self.list_box.get_children():
                first_row = self.list_box.get_row_at_index(0)
                if first_row:
                    self.list_box.select_row(first_row)
                    first_row.grab_focus()
                    self.on_row_activated(self.list_box)
            else:
                self.search_entry.grab_focus()
            return True

        # Navigation Aliases
        if keyval == Gdk.KEY_k:
            return self.list_box.emit("move-cursor", Gtk.MovementStep.DISPLAY_LINES, -1)
        if keyval == Gdk.KEY_j:
            return self.list_box.emit("move-cursor", Gtk.MovementStep.DISPLAY_LINES, 1)

        # Actions
        if (
            keyval == Gdk.KEY_slash
            or keyval == Gdk.KEY_f
            and not self.search_entry.has_focus()
        ):
            # In compact mode the search entry is set_no_show_all(True). Re-allow show.
            self.search_entry.set_no_show_all(False)
            self.search_entry.show()

            # Defer focus + select: GTK realizes the widget on the next idle tick,
            # grab_focus() before realization is silently dropped.
            def _focus_search():
                self.search_entry.grab_focus()
                self.search_entry.select_region(0, -1)
                return False

            GLib.idle_add(_focus_search)
            return True
        if keyval == Gdk.KEY_v:
            # Toggle selection mode
            self.toggle_selection_mode()
            return True
        if keyval == Gdk.KEY_space:
            if self.selection_mode:
                # In selection mode, space toggles item selection
                self.toggle_item_selection()
                return True
            elif selected_row:
                # If it's a URL and browser-open is enabled, open it
                if OPEN_LINKS_WITH_BROWSER and getattr(selected_row, "is_url", False):
                    url = getattr(selected_row, "website_url", None) or getattr(selected_row, "item_value", "")
                    if url:
                        self.open_url_with_gtk(url)
                        return True
                # Otherwise show preview
                self.show_item_preview()
                return True
        if ctrl and keyval == Gdk.KEY_a:
            if shift:
                # Ctrl+Shift+A: Deselect all
                self.deselect_all_items()
            else:
                # Ctrl+A: Select all
                self.select_all_items()
            return True
        if ctrl and keyval == Gdk.KEY_x:
            # Ctrl+X: Delete selected items
            if self.selection_mode and self.selected_indices:
                self.delete_selected_items()
            return True
        if shift and keyval == Gdk.KEY_Delete:
            # Shift+Delete: Delete selected items
            if self.selection_mode and self.selected_indices:
                self.delete_selected_items()
            return True
        if ctrl and shift and keyval == Gdk.KEY_Delete:
            # Ctrl+Shift+Delete: Clear all non-pinned items
            self.clear_all_items()
            return True
        if ctrl and keyval == Gdk.KEY_d:
            # Ctrl+D: Clear all non-pinned items (alternative)
            self.clear_all_items()
            return True
        if keyval == Gdk.KEY_p:
            if selected_row:
                self.toggle_pin_selected()
                return True
        if keyval in [Gdk.KEY_x, Gdk.KEY_Delete]:
            if selected_row and not self.selection_mode:
                self.remove_selected_item()
                return True
        if keyval == Gdk.KEY_question or (shift and keyval == Gdk.KEY_slash):
            show_help_window(self.window, self.on_help_window_close)
            return True
        if ctrl and keyval == Gdk.KEY_comma:
            style_defaults = {
                "border_radius": 6,
                "accent_color": "#ffcc00",
                "selection_color": "#4a90e2",
                "visual_mode_color": "#9b59b6",
            }
            show_settings_window(
                self.window,
                self.on_settings_window_close,
                self.restart_application,
                update_style_cb=self.update_style_css,
                style_defaults=style_defaults,
            )
            return True
        if keyval == Gdk.KEY_Tab:
            self.pin_filter_button.set_active(not self.pin_filter_button.get_active())
            self.list_box.grab_focus()
            return True
        if keyval == Gdk.KEY_Escape:
            # Priority order: exit selection mode -> clear search -> quit
            if self.selection_mode:
                self.toggle_selection_mode()
                return True
            elif self.search_entry.get_text():
                self.search_entry.set_text("")
                self.list_box.grab_focus()
            else:
                app = self.window.get_application()
                if app:
                    # Try to minimize to tray if enabled, otherwise quit
                    from .. import constants

                    if (
                        hasattr(app, "tray_manager")
                        and app.tray_manager
                        and constants.MINIMIZE_TO_TRAY
                    ):
                        if app.tray_manager.minimize_to_tray():
                            return True  # Successfully minimized to tray
                    app.quit()
                else:
                    log.warning("Application instance is None. Cannot quit.")
            return True
        if ctrl and keyval == Gdk.KEY_q:
            app = self.window.get_application()
            if app:
                app.quit()
            else:
                log.warning("Application instance is None. Cannot quit.")
            return True

        # Zoom
        if ctrl and keyval in [Gdk.KEY_plus, Gdk.KEY_equal]:
            self.zoom_level *= 1.1
            self.update_zoom()
            return True
        if ctrl and keyval == Gdk.KEY_minus:
            self.zoom_level /= 1.1
            self.update_zoom()
            return True
        if ctrl and keyval == Gdk.KEY_0:
            self.zoom_level = 1.0
            self.update_zoom()
            return True

        return False

    def on_row_activated(self, row, with_paste_simulation=False):
        """Handles double-click or Enter on a list row."""
        log.debug(f"Row activated: original_index={getattr(row, 'item_index', 'N/A')}")
        self.copy_selected_item_to_clipboard(with_paste_simulation)

    def _on_row_single_click(self, row):
        """Handles single-click on a list row - copies and pastes."""
        log.debug(f"Row single-clicked: original_index={getattr(row, 'item_index', 'N/A')}")
        # Select the row first
        self.list_box.select_row(row)
        # Trigger copy with paste simulation
        self.copy_selected_item_to_clipboard(with_paste_simulation=True)

    def on_compact_mode_toggled(self, button):
        """Handles compact mode toggle button state changes."""
        self.compact_mode = button.get_active()
        self.update_compact_mode()
        # Save the setting
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "compact_mode", str(self.compact_mode))
        config._save_config()
