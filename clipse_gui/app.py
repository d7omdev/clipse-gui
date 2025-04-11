# clipse_gui/app.py
import gi
import os
import sys
import threading
import time
import logging
import traceback
from functools import partial

gi.require_version("Gtk", "3.0")
from gi.repository import (
    Gtk,
    Gdk,
    GdkPixbuf,
    GLib,
    Pango,
    Gio,
)

# Import from local package
from .constants import (
    APP_NAME,
    HISTORY_FILE_PATH,
    APP_CSS,
    APPLICATION_ID,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    IMAGE_CACHE_MAX_SIZE,
    SAVE_DEBOUNCE_MS,
    SEARCH_DEBOUNCE_MS,
    INITIAL_LOAD_COUNT,
    LOAD_BATCH_SIZE,
    LOAD_THRESHOLD_FACTOR,
    LIST_ITEM_IMAGE_WIDTH,
    LIST_ITEM_IMAGE_HEIGHT,
)
from .data_manager import DataManager
from .image_handler import ImageHandler
from .ui_components import create_list_row_widget, show_help_window, show_preview_window

log = logging.getLogger(__name__)


# --- Main Application Logic/View Controller ---
class ClipboardHistoryController:
    def __init__(self, application_window: Gtk.ApplicationWindow):
        """
        Initializes the controller managing the content of the main window.

        Args:
            application_window: The main Gtk.ApplicationWindow this controller manages.
        """
        self.window = application_window
        self.items = []
        self.filtered_items = []
        self.show_only_pinned = False
        self.zoom_level = 1.0
        self.search_term = ""

        # --- State Flags ---
        self._loading_more = False
        self._save_timer_id = None
        self._search_timer_id = None
        self._vadjustment_handler_id = None

        # --- Initialize Managers ---
        self.data_manager = DataManager(HISTORY_FILE_PATH)
        self.image_handler = ImageHandler(IMAGE_CACHE_MAX_SIZE)

        # --- Build UI Content ---
        self.main_box = self._build_ui_content()

        self.window.add(self.main_box)

        self.window.connect("key-press-event", self.on_key_press)
        self.window.connect("destroy", self.on_window_destroy)

        # --- Load Initial Data ---
        self.status_label.set_text("Loading history...")
        threading.Thread(target=self._load_initial_data, daemon=True).start()

        self._apply_css()
        self.update_zoom()

    def _build_ui_content(self) -> Gtk.Box:
        """Creates the main vertical box containing all UI elements."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)

        # --- Header ---
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        header_box.pack_start(self.search_entry, True, True, 0)

        self.pin_filter_button = Gtk.ToggleButton(label="Pinned Only")
        self.pin_filter_button.set_active(self.show_only_pinned)
        self.pin_filter_button.connect("toggled", self.on_pin_filter_toggled)
        header_box.pack_start(self.pin_filter_button, False, False, 0)
        main_box.pack_start(header_box, False, False, 5)

        # --- List View ---
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_box.pack_start(self.scrolled_window, True, True, 0)

        self.vadj = self.scrolled_window.get_vadjustment()
        if self.vadj:
            self._vadjustment_handler_id = self.vadj.connect(
                "value-changed", self.on_vadjustment_changed
            )
        else:
            log.warning("Could not get vertical adjustment for lazy loading.")

        self.viewport = Gtk.Viewport()
        self.scrolled_window.add(self.viewport)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-activated", self.on_row_activated)
        self.list_box.connect("size-allocate", self.on_list_box_size_allocate)
        self.viewport.add(self.list_box)

        # --- Status Bar ---
        self.status_label = Gtk.Label(label="Initializing...")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.get_style_context().add_class("status-label")

        main_box.pack_end(self.status_label, False, False, 0)

        return main_box

    def _apply_css(self):
        """Applies the application-wide CSS."""
        screen = Gdk.Screen.get_default()
        if not screen:
            log.error("Cannot get default GdkScreen to apply CSS")
            return

        if not hasattr(self, "style_provider"):
            log.debug("Creating and adding application CSS provider.")
            self.style_provider = Gtk.CssProvider()
            try:
                self.style_provider.load_from_data(APP_CSS.encode())
                Gtk.StyleContext.add_provider_for_screen(
                    screen,
                    self.style_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )
            except GLib.Error as e:
                log.error(f"Failed to load or add CSS provider: {e}")
            except Exception as e:
                log.error(f"Unexpected error applying CSS: {e}")
        else:
            log.debug("CSS provider already exists.")

    def _load_initial_data(self):
        """Loads history in background thread."""
        loaded_items = self.data_manager.load_history()
        GLib.idle_add(self._finish_initial_load, loaded_items)

    def _finish_initial_load(self, loaded_items):
        """Updates UI after initial data load."""
        self.items = loaded_items
        self.update_filtered_items()
        if not self.items:
            self.status_label.set_text("No history items found. Press ? for help.")
        return False

    # --- Data Handling ---
    def update_filtered_items(self):
        """Filters master list based on search and pin status."""
        self.filtered_items = []
        search_term_lower = self.search_term.lower()

        for index, item in enumerate(self.items):
            is_pinned = item.get("pinned", False)

            if self.show_only_pinned and not is_pinned:
                continue

            if search_term_lower:
                item_value = item.get("value", "").lower()
                if search_term_lower not in item_value:
                    if not (
                        item.get("filePath")
                        and search_term_lower in item.get("filePath", "").lower()
                    ):
                        continue

            self.filtered_items.append({"original_index": index, "item": item})

        # Populate the list view with the filtered items
        self.populate_list_view()
        self.update_status_label()
        GLib.idle_add(self.check_load_more)

    def schedule_save_history(self):
        """Schedules saving the history after a debounce delay."""
        if self._save_timer_id:
            GLib.source_remove(self._save_timer_id)
        self._save_timer_id = GLib.timeout_add(SAVE_DEBOUNCE_MS, self._trigger_save)

    def _trigger_save(self):
        """Calls the DataManager to save history."""
        log.debug("Triggering history save.")
        # Pass the error handling callback
        self.data_manager.save_history(self.items, self._handle_save_error)
        self._save_timer_id = None
        return False

    def _handle_save_error(self, error_message):
        """Callback for DataManager save errors."""
        self.flash_status(error_message)

    # --- UI Population and Updates---
    def populate_list_view(self):
        """Clears and populates the list view with the initial batch of filtered items."""
        if not self.list_box:
            return

        if self.vadj and self._vadjustment_handler_id:
            try:
                self.vadj.disconnect(self._vadjustment_handler_id)
            except TypeError:
                pass
            self._vadjustment_handler_id = None

        self.list_box.freeze_child_notify()
        for child in self.list_box.get_children():
            self.list_box.remove(child)
        self.list_box.thaw_child_notify()

        self._loading_more = False

        load_count = min(INITIAL_LOAD_COUNT, len(self.filtered_items))
        log.debug(f"Populating initial {load_count} rows.")
        if load_count > 0:
            self._create_rows_range(0, load_count)
            self.list_box.show_all()

        if self.vadj and not self._vadjustment_handler_id:
            self._vadjustment_handler_id = self.vadj.connect(
                "value-changed", self.on_vadjustment_changed
            )

    def _create_rows_range(self, start_idx, end_idx):
        """Creates and adds rows for a given range of filtered items."""
        end_idx = min(end_idx, len(self.filtered_items))
        log.debug(f"Creating rows from filtered index {start_idx} to {end_idx - 1}")

        for i in range(start_idx, end_idx):
            if i < len(self.filtered_items):
                item_info = self.filtered_items[i]
                item_info["filtered_index"] = i
                row = create_list_row_widget(
                    item_info, self.image_handler, self._update_row_image_widget
                )
                if row:
                    self.list_box.add(row)
            else:
                log.warning(f"Attempted to create row for out-of-bounds index {i}")

    def _update_row_image_widget(
        self, image_container, placeholder, pixbuf, error_message
    ):
        """Callback passed to ImageHandler to update the UI for a specific row's image."""
        if not image_container or not image_container.get_realized():
            return
        if placeholder and not placeholder.get_realized():
            placeholder = None

        try:
            current_child = image_container.get_child()
            if current_child:
                image_container.remove(current_child)

            if pixbuf:
                image = Gtk.Image.new_from_pixbuf(pixbuf)
                image.set_halign(Gtk.Align.CENTER)
                image.set_valign(Gtk.Align.CENTER)
                image_container.add(image)
                image.show()
            elif placeholder:
                placeholder.set_label(error_message or "[Error]")
                image_container.add(placeholder)
                placeholder.show()
        except Exception as e:
            log.error(f"Error updating row image widget: {e}")

    # --- Status Label, Pin Status, Zoom ---
    def update_status_label(self):
        """Updates the status bar text."""
        count = len(self.filtered_items)
        total = len(self.items)
        status_parts = []
        if self.show_only_pinned:
            status_parts.append(f"Showing {count} pinned items")
        elif self.search_term:
            status_parts.append(f"Found {count} items ({total} total)")
        else:
            status_parts.append(f"{total} items")

        status_parts.append("Press ? for help")
        final_status = " • ".join(status_parts)

        if self.status_label.get_text() != final_status:
            self.status_label.set_text(final_status)

    def flash_status(self, message, duration=2500):
        """Temporarily displays a message in the status bar."""
        current_status = self.status_label.get_text()
        log.info(f"Status Flash: {message}")
        self.status_label.set_text(message)

        def revert_status(original_text):
            if self.status_label.get_text() == message:
                self.update_status_label()
            return False

        GLib.timeout_add(duration, partial(revert_status, current_status))

    def update_row_pin_status(self, original_index):
        """Updates the visual state of a row when its pin status changes."""
        is_pinned = self.items[original_index].get("pinned", False)
        for row in self.list_box.get_children():
            if hasattr(row, "item_index") and row.item_index == original_index:
                row.item_pinned = is_pinned
                try:
                    vbox = row.get_child()
                    hbox = vbox.get_children()[0]
                    pin_icon = hbox.get_children()[-1]
                    if isinstance(pin_icon, Gtk.Image):
                        pin_icon.set_from_icon_name(
                            "starred" if is_pinned else "non-starred-symbolic",
                            Gtk.IconSize.MENU,
                        )
                        pin_icon.set_tooltip_text(
                            "Pinned" if is_pinned else "Not Pinned"
                        )
                except (AttributeError, IndexError, TypeError) as e:
                    log.warning(
                        f"Could not update pin icon for row {original_index}: {e}"
                    )

                context = row.get_style_context()
                if is_pinned:
                    context.add_class("pinned-row")
                else:
                    context.remove_class("pinned-row")
                break

    def update_zoom(self):
        """Applies the current zoom level to the application CSS."""
        zoom_css = f"* {{ font-size: {round(self.zoom_level * 100)}%; }}".encode()
        try:
            if not hasattr(self, "style_provider"):
                self._apply_css()
            self.style_provider.load_from_data(APP_CSS.encode() + b"\n" + zoom_css)
            log.debug(f"Zoom updated to {self.zoom_level:.2f}")
        except GLib.Error as e:
            log.error(f"Error loading CSS for zoom: {e}")
        except Exception as e:
            log.error(f"Unexpected error updating zoom CSS: {e}")

    # --- Lazy Loading ---
    def on_vadjustment_changed(self, adjustment):
        """Callback when the scrollbar position changes."""
        if self._loading_more:
            return
        current_value = adjustment.get_value()
        upper = adjustment.get_upper()
        page_size = adjustment.get_page_size()
        if (
            upper > page_size
            and current_value >= (upper - page_size) * LOAD_THRESHOLD_FACTOR
        ):
            self.check_load_more()

    def on_list_box_size_allocate(self, list_box, allocation):
        """Callback when list box size changes, check if viewport needs filling."""
        GLib.idle_add(self.check_load_more)

    def check_load_more(self):
        """Checks if more items should be loaded."""
        if self._loading_more:
            return False
        if not self.list_box.get_realized():
            return False

        current_row_count = len(self.list_box.get_children())
        total_filtered_count = len(self.filtered_items)

        if current_row_count < total_filtered_count:
            needs_load = False
            if self.vadj:
                upper = self.vadj.get_upper()
                page_size = self.vadj.get_page_size()
                # Condition 1: Viewport not full
                if upper <= page_size + 5:
                    needs_load = True
                # Condition 2: Scrolled near bottom
                elif (
                    self.vadj.get_value() >= (upper - page_size) * LOAD_THRESHOLD_FACTOR
                ):
                    needs_load = True

            if needs_load:
                self._loading_more = True
                start_idx = current_row_count
                end_idx = min(start_idx + LOAD_BATCH_SIZE, total_filtered_count)
                log.debug(f"Scheduling load more: {start_idx} to {end_idx - 1}")
                GLib.idle_add(self._do_load_more, start_idx, end_idx)
                return False

        return False

    def _do_load_more(self, start_idx, end_idx):
        """Performs the actual row creation for lazy loading."""
        log.debug(f"Executing load more: {start_idx} to {end_idx - 1}")
        self._create_rows_range(start_idx, end_idx)
        self.list_box.show_all()
        self._loading_more = False
        GLib.idle_add(self.check_load_more)
        return False

    # --- Actions  ---
    def toggle_pin_selected(self):
        """Toggles the pin status of the currently selected item."""
        selected_row = self.list_box.get_selected_row()
        if selected_row and hasattr(selected_row, "item_index"):
            original_index = selected_row.item_index
            if 0 <= original_index < len(self.items):
                item = self.items[original_index]
                item["pinned"] = not item.get("pinned", False)
                self.update_row_pin_status(original_index)
                self.schedule_save_history()
                self.flash_status("Item pinned" if item["pinned"] else "Item unpinned")
                if self.show_only_pinned and not item["pinned"]:
                    self._remove_row_from_view(selected_row)
            else:
                self.flash_status("Error: Item index invalid.")
        else:
            log.warning("Toggle pin called with no valid row selected.")

    def remove_selected_item(self):
        """Removes the currently selected item."""
        selected_row = self.list_box.get_selected_row()
        if selected_row and hasattr(selected_row, "item_index"):
            original_index_to_remove = selected_row.item_index
            if 0 <= original_index_to_remove < len(self.items):
                item_value_preview = str(
                    self.items[original_index_to_remove].get("value", "")
                )[:30]
                log.info(f"Removing item at original index {original_index_to_remove}")
                del self.items[original_index_to_remove]
                self.schedule_save_history()
                removed_filtered_index = self._remove_row_from_view(selected_row)
                for fi in self.filtered_items:
                    if fi["original_index"] > original_index_to_remove:
                        fi["original_index"] -= 1
                for row in self.list_box.get_children():
                    if (
                        hasattr(row, "item_index")
                        and row.item_index > original_index_to_remove
                    ):
                        row.item_index -= 1
                self.flash_status(f"Item removed: '{item_value_preview}...'.")
                self.update_status_label()
                if removed_filtered_index != -1:
                    new_count = len(self.list_box.get_children())
                    if new_count > 0:
                        select_idx = min(removed_filtered_index, new_count - 1)
                        self.list_box.select_row(
                            self.list_box.get_row_at_index(select_idx)
                        )

            else:
                self.flash_status("Error: Item index invalid for removal.")
        else:
            log.warning("Remove item called with no valid row selected.")

    def _remove_row_from_view(self, row_to_remove):
        """Helper to remove a row and update filtered list/indices."""
        removed_filtered_index = -1
        original_index_removed = getattr(row_to_remove, "item_index", -1)
        children = self.list_box.get_children()
        try:
            removed_filtered_index = children.index(row_to_remove)
        except ValueError:
            return -1
        self.list_box.remove(row_to_remove)
        self.filtered_items = [
            fi
            for fi in self.filtered_items
            if fi["original_index"] != original_index_removed
        ]
        for idx in range(removed_filtered_index, len(self.list_box.get_children())):
            row = self.list_box.get_row_at_index(idx)
            if hasattr(row, "filtered_index"):
                row.filtered_index = idx
        return removed_filtered_index

    def copy_selected_item_to_clipboard(self):
        """Copies the selected item's content to the system clipboard."""
        selected_row = self.list_box.get_selected_row()
        if not selected_row:
            return
        try:
            original_index = selected_row.item_index
            if not (0 <= original_index < len(self.items)):
                self.flash_status("Error: Selected item no longer exists.")
                return
            item = self.items[original_index]
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            if selected_row.is_image:
                image_path = item.get("filePath")
                if image_path and os.path.exists(image_path):
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
                        clipboard.set_image(pixbuf)
                        clipboard.store()
                        self.flash_status("Image copied to clipboard")
                        GLib.timeout_add(100, self.window.destroy)
                    except Exception as e:
                        log.error(f"Failed to copy image data: {e}")
                        self.flash_status(f"Error copying image: {e}")
                else:
                    self.flash_status("Image path invalid or file missing")
            else:
                text_value = selected_row.item_value
                clipboard.set_text(text_value, -1)
                clipboard.store()
                self.flash_status("Text copied to clipboard")
                GLib.timeout_add(100, self.window.destroy)
        except Exception as e:
            log.error(f"Unexpected error during copy: {e}")
            self.flash_status(f"Error copying: {str(e)}")

    def show_item_preview(self):
        """Shows the preview window for the selected item."""
        selected_row = self.list_box.get_selected_row()
        if not selected_row:
            return
        try:
            original_index = selected_row.item_index
            if not (0 <= original_index < len(self.items)):
                self.flash_status("Error: Selected item no longer exists.")
                return
            item = self.items[original_index]
            show_preview_window(
                self.window,
                item,
                selected_row.is_image,
                self.change_preview_text_size,
                self.reset_preview_text_size,
                self.on_preview_key_press,
            )
        except Exception as e:
            log.error(f"Error creating preview window: {e}")
            traceback.print_exc()
            self.flash_status(f"Error showing preview: {str(e)}")

    # --- Preview Window Callbacks ---
    def change_preview_text_size(self, text_view, delta):
        """Callback to change font size in the preview TextView."""
        try:
            pango_context = text_view.get_pango_context()
            font_desc = pango_context.get_font_description() if pango_context else None
            if not font_desc:
                return

            if not hasattr(text_view, "base_font_size"):
                base_size = font_desc.get_size() / Pango.SCALE
                text_view.base_font_size = base_size if base_size > 0 else 10.0

            current_size_pts = font_desc.get_size() / Pango.SCALE
            new_size_pts = max(4.0, current_size_pts + delta)
            font_desc.set_size(int(new_size_pts * Pango.SCALE))
            text_view.override_font(font_desc)
        except Exception as e:
            log.error(f"Error changing preview text size: {e}")

    def reset_preview_text_size(self, text_view):
        """Callback to reset font size in the preview TextView."""
        try:
            if hasattr(text_view, "base_font_size") and text_view.base_font_size > 0:
                pango_context = text_view.get_pango_context()
                font_desc = (
                    pango_context.get_font_description() if pango_context else None
                )
                if font_desc:
                    font_desc.set_size(int(text_view.base_font_size * Pango.SCALE))
                    text_view.override_font(font_desc)
                else:
                    text_view.override_font(None)
            else:
                text_view.override_font(None)
        except Exception as e:
            log.error(f"Error resetting preview text size: {e}")

    def on_preview_key_press(self, preview_window, event):
        """Handles key presses within the preview window."""
        keyval = event.keyval
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        if keyval == Gdk.KEY_Escape:
            preview_window.destroy()
            return True
        if keyval == Gdk.KEY_c and ctrl:
            widget_to_search = preview_window.get_child()
            textview = None
            if isinstance(widget_to_search, Gtk.Box):
                for child in widget_to_search.get_children():
                    if isinstance(child, Gtk.ScrolledWindow) and isinstance(
                        child.get_child(), Gtk.TextView
                    ):
                        textview = child.get_child()
                        break
            if textview:
                buffer = textview.get_buffer()
                if buffer.get_has_selection():
                    buffer.copy_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD))
                else:
                    buffer.select_range(buffer.get_start_iter(), buffer.get_end_iter())
                    buffer.copy_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD))
                    buffer.delete_selection(False, False)
                self.flash_status("Text copied from preview", duration=1500)
                return True
        return False

    # --- Event Handlers ---
    def on_window_destroy(self, widget):
        """Cleanup actions when the main window is closed."""
        log.info("Main window closed.")

    def on_key_press(self, widget, event):
        """Handles key presses on the main window."""
        keyval = event.keyval
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK

        if self.search_entry.has_focus():
            if keyval == Gdk.KEY_Escape:
                if self.search_entry.get_text():
                    self.search_entry.set_text("")
                else:
                    self.list_box.grab_focus()
                return True
            if keyval in [Gdk.KEY_Up, Gdk.KEY_Down]:
                if len(self.list_box.get_children()) > 0:
                    self.list_box.grab_focus()
                    return False
            return False

        # List Box Focus / General Keys
        selected_row = self.list_box.get_selected_row()
        if keyval == Gdk.KEY_k:
            return self.list_box.emit(
                "move-cursor", Gtk.MovementStep.DISPLAY_LINES, -1, False
            )
        if keyval == Gdk.KEY_j:
            return self.list_box.emit(
                "move-cursor", Gtk.MovementStep.DISPLAY_LINES, 1, False
            )
        if keyval == Gdk.KEY_Home:
            if len(self.list_box.get_children()) > 0:
                self.list_box.select_row(self.list_box.get_row_at_index(0))
                self.scroll_to_top()
            return True
        if keyval == Gdk.KEY_End:
            last_idx = len(self.list_box.get_children()) - 1
            if last_idx >= 0:
                self.list_box.select_row(self.list_box.get_row_at_index(last_idx))
                self.scroll_to_bottom()
            return True
        if keyval == Gdk.KEY_slash:
            self.search_entry.grab_focus()
            return True
        if keyval == Gdk.KEY_space:
            self.show_item_preview()
            return True
        if keyval == Gdk.KEY_p:
            self.toggle_pin_selected()
            return True
        if keyval in [Gdk.KEY_x, Gdk.KEY_Delete]:
            self.remove_selected_item()
            return True
        if keyval == Gdk.KEY_question:
            show_help_window(self.window)
            return True
        if keyval == Gdk.KEY_Tab:
            self.pin_filter_button.set_active(not self.pin_filter_button.get_active())
            return True
        if keyval == Gdk.KEY_Escape:
            self.window.destroy()
            return True
        if ctrl and keyval in [Gdk.KEY_plus, Gdk.KEY_equal]:
            self.zoom_level = min(3.0, self.zoom_level * 1.1)
            self.update_zoom()
            return True
        if ctrl and keyval == Gdk.KEY_minus:
            self.zoom_level = max(0.5, self.zoom_level / 1.1)
            self.update_zoom()
            return True
        if ctrl and keyval == Gdk.KEY_0:
            self.zoom_level = 1.0
            self.update_zoom()
            return True
        if ctrl and keyval == Gdk.KEY_q:
            self.window.get_application().quit()
            return True

        return False

    def on_row_activated(self, list_box, row):
        """Handles double-click or Enter on a list row."""
        log.debug(f"Row activated: original_index={getattr(row, 'item_index', 'N/A')}")
        self.copy_selected_item_to_clipboard()

    def on_search_changed(self, entry):
        """Handles changes in the search entry, debounced."""
        self.search_term = entry.get_text()
        if self._search_timer_id:
            GLib.source_remove(self._search_timer_id)
        self._search_timer_id = GLib.timeout_add(
            SEARCH_DEBOUNCE_MS, self._trigger_filter_update
        )

    def _trigger_filter_update(self):
        """Updates filtering after search debounce timeout."""
        log.debug(f"Triggering filter update for search: '{self.search_term}'")
        self.update_filtered_items()
        self._search_timer_id = None
        return False

    def on_pin_filter_toggled(self, button):
        """Handles toggling the 'Pinned Only' filter button."""
        self.show_only_pinned = button.get_active()
        log.debug(f"Pin filter toggled: {'ON' if self.show_only_pinned else 'OFF'}")
        self.update_filtered_items()

    # --- Scrolling Helpers ---
    def scroll_to_bottom(self):
        if not self.vadj:
            return
        GLib.idle_add(
            lambda: self.vadj.set_value(
                self.vadj.get_upper() - self.vadj.get_page_size()
            )
            or False
        )

    def scroll_to_top(self):
        if not self.vadj:
            return
        GLib.idle_add(lambda: self.vadj.set_value(self.vadj.get_lower()) or False)


# --- Gtk.Application Subclass ---
class ClipseGuiApplication(Gtk.Application):
    """The main GTK Application."""

    def __init__(self):
        super().__init__(
            application_id=APPLICATION_ID, flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.window = None
        self.controller = None

    def do_startup(self):
        """Called once when the application starts."""
        Gtk.Application.do_startup(self)
        log.info(f"Application {APPLICATION_ID} starting up.")

    def do_activate(self):
        """Called when the application is launched (or reactivated)."""
        if not self.window:
            log.info("Activating application - creating main window.")
            self.window = Gtk.ApplicationWindow(application=self, title=APP_NAME)
            self.window.set_default_size(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

            self.controller = ClipboardHistoryController(self.window)

            self.window.show_all()
        else:
            log.info("Application already active - presenting existing window.")
            self.window.present()
