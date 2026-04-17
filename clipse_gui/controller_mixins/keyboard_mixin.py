"""Main keyboard event handler and row activation callbacks."""

import logging

from gi.repository import Gdk, GLib, Gtk

from ..constants import ENTER_TO_PASTE, OPEN_LINKS_WITH_BROWSER, config
from ..ui_components import show_help_window, show_settings_window

log = logging.getLogger(__name__)

# Keys that insert their character when search entry is focused
_SEARCH_INSERT_KEYS = {
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

_PAGE_STEP = 5


class KeyboardMixin:
    def on_key_press(self, widget, event):
        """Handles key presses on the main window."""
        keyval = event.keyval
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK)

        if self.search_entry.has_focus():
            return self._handle_search_keys(keyval)

        return self._dispatch_key(keyval, ctrl, shift)

    # ── Search-focused key handling ─────────────────────────────

    def _handle_search_keys(self, keyval):
        """Handle keys when search entry is focused."""
        if keyval == Gdk.KEY_Escape:
            return self._handle_search_escape()

        if keyval in (Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Page_Up, Gdk.KEY_Page_Down):
            return self._navigate_from_search(keyval)

        char = _SEARCH_INSERT_KEYS.get(keyval)
        if char:
            self._insert_search_char(char)
            return True

        if keyval in (Gdk.KEY_Tab, Gdk.KEY_Return):
            return True

        return False

    def _handle_search_escape(self):
        """Escape while search focused: exit selection → clear + unfocus."""
        if self.selection_mode:
            self.toggle_selection_mode()
            return True

        if self.search_entry.get_text():
            self.search_entry.set_text("")

        def unfocus():
            if self.list_box:
                first = self.list_box.get_row_at_index(0)
                if first:
                    self.list_box.select_row(first)
                    first.grab_focus()
                else:
                    self.list_box.grab_focus()
            else:
                self.window.grab_focus()
            return False

        GLib.idle_add(unfocus)
        return True

    def _navigate_from_search(self, keyval):
        """Arrow / PageUp / PageDown while search is focused."""
        children = self.list_box.get_children()
        if not children:
            return False

        focus = self.window.get_focus()
        idx = children.index(focus) if focus in children else -1
        last = len(children) - 1

        target = {
            Gdk.KEY_Down: 0 if idx == -1 else idx + 1,
            Gdk.KEY_Up: last if idx == -1 else idx - 1,
            Gdk.KEY_Page_Down: 0 if idx == -1 else min(idx + _PAGE_STEP, last),
            Gdk.KEY_Page_Up: last if idx == -1 else max(idx - _PAGE_STEP, 0),
        }.get(keyval, idx)

        if 0 <= target <= last:
            row = children[target]
            self.list_box.select_row(row)
            row.grab_focus()
            adj = self.scrolled_window.get_vadjustment()
            if adj:
                alloc = row.get_allocation()
                adj.set_value(min(alloc.y, adj.get_upper() - adj.get_page_size()))
            return True

        return False

    def _insert_search_char(self, char):
        """Insert a character into the search entry at the cursor."""
        text = self.search_entry.get_text()
        if hasattr(self.search_entry, "get_position"):
            pos = self.search_entry.get_position()
            self.search_entry.set_text(text[:pos] + char + text[pos:])
            self.search_entry.set_position(pos + 1)
        else:
            self.search_entry.set_text(text + char)

    # ── Main key dispatch ───────────────────────────────────────

    def _dispatch_key(self, keyval, ctrl, shift):
        """Look up (ctrl, shift, keyval) in dispatch table and call handler."""
        dispatch = {
            # Navigation
            (False, False, Gdk.KEY_j): self._nav_down,
            (False, False, Gdk.KEY_k): self._nav_up,
            # Row activation
            (False, False, Gdk.KEY_Return): lambda: self._handle_return(False),
            (False, True, Gdk.KEY_Return): lambda: self._handle_return(
                not ENTER_TO_PASTE
            ),
            # Search focus
            (False, False, Gdk.KEY_slash): self._focus_search,
            (False, False, Gdk.KEY_f): self._focus_search,
            # Selection mode
            (False, False, Gdk.KEY_v): self.toggle_selection_mode,
            (True, False, Gdk.KEY_a): self.select_all_items,
            (True, True, Gdk.KEY_a): self.deselect_all_items,
            # Item actions
            (False, False, Gdk.KEY_space): self._handle_space,
            (False, False, Gdk.KEY_p): self._handle_pin,
            (False, False, Gdk.KEY_x): self._handle_remove_item,
            (False, False, Gdk.KEY_Delete): self._handle_remove_item,
            (True, False, Gdk.KEY_x): self._handle_delete_selected,
            (False, True, Gdk.KEY_Delete): self._handle_delete_selected,
            (True, True, Gdk.KEY_Delete): self._handle_clear_all,
            (True, False, Gdk.KEY_d): self._handle_clear_all,
            # Help / Settings
            (False, False, Gdk.KEY_question): self._show_help,
            (False, True, Gdk.KEY_question): self._show_help,
            (False, True, Gdk.KEY_slash): self._show_help,
            (True, False, Gdk.KEY_comma): self._show_settings,
            # Tab / Escape / Quit
            (False, False, Gdk.KEY_Tab): self._handle_tab,
            (False, False, Gdk.KEY_Escape): self._handle_escape,
            (True, False, Gdk.KEY_q): self._handle_quit,
            # Zoom
            (True, False, Gdk.KEY_plus): self._zoom_in,
            (True, False, Gdk.KEY_equal): self._zoom_in,
            (True, False, Gdk.KEY_minus): self._zoom_out,
            (True, False, Gdk.KEY_0): self._zoom_reset,
        }

        handler = dispatch.get((ctrl, shift, keyval))
        if handler:
            result = handler()
            return result if result is not None else True
        return False

    # ── Handler methods ─────────────────────────────────────────

    def _nav_up(self):
        return self.list_box.emit("move-cursor", Gtk.MovementStep.DISPLAY_LINES, -1)

    def _nav_down(self):
        return self.list_box.emit("move-cursor", Gtk.MovementStep.DISPLAY_LINES, 1)

    def _handle_return(self, with_paste):
        """Enter: activate selected row, or select first, or focus search."""
        selected = self.list_box.get_selected_row()
        if selected:
            self.on_row_activated(self.list_box, with_paste)
        elif self.list_box.get_children():
            first = self.list_box.get_row_at_index(0)
            if first:
                self.list_box.select_row(first)
                first.grab_focus()
                self.on_row_activated(self.list_box)
        else:
            self.search_entry.grab_focus()

    def _focus_search(self):
        """Show and focus the search entry."""
        self.search_entry.set_no_show_all(False)
        self.search_entry.show()

        def _focus():
            self.search_entry.grab_focus()
            self.search_entry.select_region(0, -1)
            return False

        GLib.idle_add(_focus)

    def _handle_space(self):
        """Space: toggle selection, open URL, or show preview."""
        if self.selection_mode:
            self.toggle_item_selection()
            return True
        selected = self.list_box.get_selected_row()
        if selected:
            if OPEN_LINKS_WITH_BROWSER and getattr(selected, "is_url", False):
                url = getattr(selected, "website_url", None) or getattr(
                    selected, "item_value", ""
                )
                if url:
                    self.open_url_with_gtk(url)
                    return True
            self.show_item_preview()
            return True
        return False

    def _handle_pin(self):
        if self.list_box.get_selected_row():
            self.toggle_pin_selected()
            return True
        return False

    def _handle_remove_item(self):
        """x / Delete: remove single item (only outside selection mode)."""
        if self.list_box.get_selected_row() and not self.selection_mode:
            self.remove_selected_item()
            return True
        return False

    def _handle_delete_selected(self):
        """Ctrl+X / Shift+Delete: delete selected items in selection mode."""
        if self.selection_mode and self.selected_indices:
            self.delete_selected_items()
            return True
        return False

    def _handle_clear_all(self):
        self.clear_all_items()

    def _show_help(self):
        show_help_window(self.window, self.on_help_window_close)

    def _show_settings(self):
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

    def _handle_tab(self):
        self.pin_filter_button.set_active(not self.pin_filter_button.get_active())
        self.list_box.grab_focus()

    def _handle_escape(self):
        """Escape: exit selection → clear search → minimize/quit."""
        if self.selection_mode:
            self.toggle_selection_mode()
            return True
        if self.search_entry.get_text():
            self.search_entry.set_text("")
            self.list_box.grab_focus()
            return True

        app = self.window.get_application()
        if app:
            from .. import constants

            if (
                hasattr(app, "tray_manager")
                and app.tray_manager
                and constants.MINIMIZE_TO_TRAY
            ):
                if app.tray_manager.minimize_to_tray():
                    return True
            app.quit()
        else:
            log.warning("Application instance is None. Cannot quit.")

    def _handle_quit(self):
        app = self.window.get_application()
        if app:
            app.quit()
        else:
            log.warning("Application instance is None. Cannot quit.")

    def _zoom_in(self):
        self.zoom_level *= 1.1
        self.update_zoom()

    def _zoom_out(self):
        self.zoom_level /= 1.1
        self.update_zoom()

    def _zoom_reset(self):
        self.zoom_level = 1.0
        self.update_zoom()

    # ── Public callbacks ────────────────────────────────────────

    def on_row_activated(self, row, with_paste_simulation=False):
        """Handles double-click or Enter on a list row."""
        log.debug(f"Row activated: original_index={getattr(row, 'item_index', 'N/A')}")
        self.copy_selected_item_to_clipboard(with_paste_simulation)

    def _on_row_single_click(self, row):
        """Handles single-click on a list row - copies and pastes."""
        log.debug(
            f"Row single-clicked: original_index={getattr(row, 'item_index', 'N/A')}"
        )
        self.list_box.select_row(row)
        self.copy_selected_item_to_clipboard(with_paste_simulation=True)

    def on_compact_mode_toggled(self, button):
        """Handles compact mode toggle button state changes."""
        self.compact_mode = button.get_active()
        self.update_compact_mode()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "compact_mode", str(self.compact_mode))
        config._save_config()
