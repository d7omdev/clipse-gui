import logging
import subprocess
import os
import shlex
import threading
from functools import partial
import mimetypes
from .constants import (
    APP_CSS,
    ENTER_TO_PASTE,
    IMAGE_CACHE_MAX_SIZE,
    INITIAL_LOAD_COUNT,
    LOAD_BATCH_SIZE,
    LOAD_THRESHOLD_FACTOR,
    COPY_TOOL_CMD,
    PASTE_SIMULATION_CMD_WAYLAND,
    PASTE_SIMULATION_CMD_X11,
    PASTE_SIMULATION_DELAY_MS,
    SAVE_DEBOUNCE_MS,
    SEARCH_DEBOUNCE_MS,
    X11_COPY_TOOL_CMD,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    config,
)
from .data_manager import DataManager
from .image_handler import ImageHandler
from .ui_components import create_list_row_widget, show_help_window, show_preview_window
from .ui_builder import build_main_window_content
from .utils import fuzzy_search

from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

log = logging.getLogger(__name__)


class ClipboardHistoryController:
    """
    Manages the application logic, state, and interactions for the main window.
    """

    def __init__(self, application_window: Gtk.ApplicationWindow):
        self.window = application_window
        self.items = []
        self.filtered_items = []
        self.show_only_pinned = False
        self.zoom_level = 1.0
        self.search_term = ""
        self.compact_mode = config.getboolean("General", "compact_mode", fallback=False)

        self._loading_more = False
        self._save_timer_id = None
        self._search_timer_id = None
        self._vadjustment_handler_id = None
        self._is_wayland = "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower()
        log.debug(f"Detected session type: {'Wayland' if self._is_wayland else 'X11'}")

        self.data_manager = DataManager(update_callback=self._on_history_updated)
        self.image_handler = ImageHandler(IMAGE_CACHE_MAX_SIZE or 50)

        ui_elements = build_main_window_content()
        self.main_box = ui_elements["main_box"]
        self.search_entry = ui_elements["search_entry"]
        self.pin_filter_button = ui_elements["pin_filter_button"]
        self.compact_mode_button = ui_elements["compact_mode_button"]
        self.scrolled_window = ui_elements["scrolled_window"]
        self.list_box = ui_elements["list_box"]
        self.status_label = ui_elements["status_label"]
        self.vadj = self.scrolled_window.get_vadjustment()

        # Set initial compact mode button state
        self.compact_mode_button.set_active(self.compact_mode)

        # Hide search entry if in compact mode after window is realized
        if self.compact_mode:

            def hide_search_entry():
                self.search_entry.hide()
                return False

            GLib.idle_add(hide_search_entry)

        self.window.add(self.main_box)

        self._connect_signals()

        self.status_label.set_text("Loading history...")
        threading.Thread(target=self._load_initial_data, daemon=True).start()

        self._apply_css()
        self.update_zoom()
        self.update_compact_mode()

    def _connect_signals(self):
        """Connects GTK signals to their handler methods."""
        log.debug("Connecting signals.")
        self.window.connect("key-press-event", self.on_key_press)
        self.window.connect("destroy", self.on_window_destroy)

        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("focus-out-event", self.on_search_focus_out)
        self.pin_filter_button.connect("toggled", self.on_pin_filter_toggled)
        self.compact_mode_button.connect("toggled", self.on_compact_mode_toggled)
        self.list_box.connect("row-activated", self.on_row_activated)
        self.list_box.connect("size-allocate", self.on_list_box_size_allocate)

        if self.vadj:
            self._vadjustment_handler_id = self.vadj.connect(
                "value-changed", self.on_vadjustment_changed
            )
        else:
            log.warning("Could not get vertical adjustment for lazy loading.")

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

    # --- Data Loading and Sync ---

    def _on_history_updated(self, loaded_items):
        """Callback function called when the file watcher detects a change."""
        log.debug("Received history update signal from DataManager.")
        self.items = loaded_items
        self.update_filtered_items()

    def _load_initial_data(self):
        """Loads history in background thread."""
        loaded_items = self.data_manager.load_history()
        GLib.idle_add(self._finish_initial_load, loaded_items)
        self.data_manager._start_history_watcher(self._on_history_updated)

    def _finish_initial_load(self, loaded_items):
        """Updates UI after initial data load."""
        self.items = loaded_items
        self.update_filtered_items()
        if not self.items:
            self.status_label.set_text("No history items found. Press ? for help.")
        else:
            GLib.idle_add(self._focus_first_item)
        return False

    def _focus_first_item(self):
        """Selects and focuses the first item in the list."""
        if len(self.list_box.get_children()) > 0:
            first_row = self.list_box.get_row_at_index(0)
            if first_row:
                self.list_box.select_row(first_row)
                first_row.grab_focus()
        return False

    # --- Data Filtering and Saving ---

    def update_filtered_items(self):
        """Filters master list based on search and pin status, then updates UI."""

        self.filtered_items = fuzzy_search(
            items=self.items,
            search_term=self.search_term,
            value_key="value",
            path_key="filePath",
            pinned_key="pinned",
            show_only_pinned=self.show_only_pinned,
        )
        self.populate_list_view()
        self.update_status_label()
        GLib.idle_add(self.check_load_more)

    def schedule_save_history(self):
        """Schedules saving the history after a debounce delay."""
        if self._save_timer_id:
            GLib.source_remove(self._save_timer_id)
        self._save_timer_id = GLib.timeout_add(
            int(SAVE_DEBOUNCE_MS or 300), self._trigger_save
        )

    def _trigger_save(self):
        """Calls the DataManager to save history."""
        log.debug("Triggering history save.")
        self.data_manager.save_history(self.items, self._handle_save_error)
        self._save_timer_id = None
        return False

    def _handle_save_error(self, error_message):
        """Callback for DataManager save errors."""
        self.flash_status(error_message)

    # --- UI Population and Updates ---

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
        load_count = min(INITIAL_LOAD_COUNT or 30, len(self.filtered_items))
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

        self.list_box.freeze_child_notify()
        for i in range(start_idx, end_idx):
            if i < len(self.filtered_items):
                item_info = self.filtered_items[i]
                item_info["filtered_index"] = i
                row = create_list_row_widget(
                    item_info, self.image_handler, self._update_row_image_widget
                )
                if row:
                    row.item_index = item_info["original_index"]
                    file_path = item_info["item"].get("filePath")
                    row.is_image = bool(file_path and isinstance(file_path, str))
                    row.item_value = item_info["item"].get("value")
                    row.item_pinned = item_info["item"].get("pinned", False)
                    self.list_box.add(row)
            else:
                log.warning(f"Attempted to create row for out-of-bounds index {i}")
        self.list_box.thaw_child_notify()

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
                placeholder.set_label(error_message or "[Load Error]")
                image_container.add(placeholder)
                placeholder.show()
        except Exception as e:
            log.error(f"Error updating row image widget: {e}")

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
                    widget = row.get_child()
                    if isinstance(widget, Gtk.Box):
                        hbox = widget.get_children()[0]
                        if isinstance(hbox, Gtk.Box):
                            children = hbox.get_children()
                            if children:
                                pin_icon = children[-1]
                                if isinstance(pin_icon, Gtk.Image):
                                    icon_name = (
                                        "starred-symbolic"
                                        if is_pinned
                                        else "non-starred-symbolic"
                                    )
                                    pin_icon.set_from_icon_name(
                                        icon_name,
                                        Gtk.IconSize.BUTTON,
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
        self.zoom_level = max(0.5, min(self.zoom_level, 3.0))
        zoom_css = f"* {{ font-size: {round(self.zoom_level * 100)}%; }}".encode()
        try:
            if not hasattr(self, "style_provider"):
                self._apply_css()
            base_css = APP_CSS.encode() if isinstance(APP_CSS, str) else APP_CSS
            self.style_provider.load_from_data(base_css + b"\n" + zoom_css)
            log.debug(f"Zoom updated to {self.zoom_level:.2f}")
        except GLib.Error as e:
            log.error(f"Error loading CSS for zoom: {e}")
        except Exception as e:
            log.error(f"Unexpected error updating zoom CSS: {e}")

    # --- Lazy Loading ---

    def on_vadjustment_changed(self, adjustment):
        """Callback when the scrollbar position changes, triggers lazy load if needed."""
        if self._loading_more:
            return
        current_value = adjustment.get_value()
        upper = adjustment.get_upper()
        page_size = adjustment.get_page_size()
        if (
            upper > page_size
            and current_value >= (upper - page_size) * LOAD_THRESHOLD_FACTOR
            and len(self.list_box.get_children()) < len(self.filtered_items)
        ):
            self.check_load_more()

    def on_list_box_size_allocate(self, list_box, allocation):
        """Callback when list box size changes, check if viewport needs filling."""
        GLib.idle_add(self.check_load_more)

    def check_load_more(self):
        """Checks if more items should be loaded based on scroll position or viewport fill."""
        if self._loading_more:
            return False
        if not self.list_box.get_realized() or not self.vadj:
            return False

        current_row_count = len(self.list_box.get_children())
        total_filtered_count = len(self.filtered_items)

        if current_row_count < total_filtered_count:
            needs_load = False
            upper = self.vadj.get_upper() or 0
            page_size = self.vadj.get_page_size() or 0
            threshold_factor = LOAD_THRESHOLD_FACTOR or 1.0

            if upper <= page_size + 5:
                needs_load = True
            elif (
                upper > page_size
                and self.vadj.get_value() >= (upper - page_size) * threshold_factor
            ):
                needs_load = True

            if needs_load:
                self._loading_more = True
                start_idx = current_row_count
                end_idx = min(start_idx + (LOAD_BATCH_SIZE or 20), total_filtered_count)
                log.debug(f"Scheduling load more: rows {start_idx} to {end_idx - 1}")
                GLib.idle_add(self._do_load_more, start_idx, end_idx)
                return False

        return False

    def _do_load_more(self, start_idx, end_idx):
        """Performs the actual row creation for lazy loading."""
        log.debug(f"Executing load more: rows {start_idx} to {end_idx - 1}")
        self._create_rows_range(start_idx, end_idx)
        self.list_box.show_all()
        self._loading_more = False
        GLib.idle_add(self.check_load_more)
        return False

    # --- Actions ---

    def toggle_pin_selected(self):
        """Toggles the pin status of the currently selected item."""
        selected_row = self.list_box.get_selected_row()
        if selected_row and hasattr(selected_row, "item_index"):
            original_index = selected_row.item_index
            if 0 <= original_index < len(self.items):
                item = self.items[original_index]
                new_pin_state = not item.get("pinned", False)
                item["pinned"] = new_pin_state
                self.update_row_pin_status(original_index)
                self.schedule_save_history()
                self.flash_status("Item pinned" if new_pin_state else "Item unpinned")
                if self.show_only_pinned and not new_pin_state:
                    self._remove_row_from_view(selected_row)
            else:
                log.error(f"Invalid original_index {original_index} for toggle pin.")
                self.flash_status("Error: Item index invalid.")
        else:
            log.warning("Toggle pin called with no valid row selected.")

    def remove_selected_item(self):
        """Removes the currently selected item from history and view."""
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

                # Update original indices for subsequent items/rows
                for fi in self.filtered_items:
                    if fi["original_index"] > original_index_to_remove:
                        fi["original_index"] -= 1
                current_rows = self.list_box.get_children()
                for i in range(removed_filtered_index, len(current_rows)):
                    row = current_rows[i]
                    if (
                        hasattr(row, "item_index")
                        and row.item_index > original_index_to_remove
                    ):
                        row.item_index -= 1

                self.flash_status(f"Item removed: '{item_value_preview}...'.")
                self.update_status_label()
                self._select_nearby_row(
                    removed_filtered_index
                )  # Reselect after removal
            else:
                log.error(
                    f"Invalid original_index {original_index_to_remove} for remove."
                )
                self.flash_status("Error: Item index invalid for removal.")
        else:
            log.warning("Remove item called with no valid row selected.")

    def _remove_row_from_view(self, row_to_remove):
        """Helper to remove a row from the ListBox and update filtered list."""
        removed_filtered_index = -1
        original_index_removed = getattr(row_to_remove, "item_index", -1)
        children = self.list_box.get_children()
        try:
            removed_filtered_index = children.index(row_to_remove)
        except ValueError:
            log.warning(
                f"Row with original index {original_index_removed} not found in list_box children."
            )
            for idx, child in enumerate(children):  # Fallback find
                if getattr(child, "item_index", -1) == original_index_removed:
                    removed_filtered_index = idx
                    row_to_remove = child
                    break
            if removed_filtered_index == -1:
                return -1

        self.list_box.remove(row_to_remove)
        self.filtered_items = [
            fi
            for fi in self.filtered_items
            if fi["original_index"] != original_index_removed
        ]
        return removed_filtered_index

    def _select_nearby_row(self, index_before_removal):
        """Selects a row near the index of a previously removed row."""
        if index_before_removal != -1:
            new_count = len(self.list_box.get_children())
            if new_count > 0:
                select_idx = min(index_before_removal, new_count - 1)
                new_row = self.list_box.get_row_at_index(select_idx)
                if new_row:
                    self.list_box.select_row(new_row)
                    new_row.grab_focus()
                else:
                    self.list_box.grab_focus()
            else:
                self.search_entry.grab_focus()

    def _run_paste_command(self, cmd_args, input_data=None, is_binary=False):
        """Helper to run the paste command subprocess."""
        try:
            log.info(f"Running paste command: {cmd_args}")
            process = subprocess.Popen(
                cmd_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout_output, stderr_output = None, None
            try:
                input_bytes = (
                    input_data
                    if is_binary
                    else input_data.encode("utf-8")
                    if input_data is not None
                    else None
                )
                stdout_output, stderr_output = process.communicate(
                    input=input_bytes, timeout=5
                )
            except subprocess.TimeoutExpired:
                log.error(f"Paste command timed out: {cmd_args}")
                process.kill()
                stdout_output, stderr_output = process.communicate()
                self.flash_status("Error: Paste command timed out")
                return False
            except OSError as e:
                log.error(f"OSError during paste command communicate: {e}")
                if process.stderr:
                    stderr_output = process.stderr.read()
                self.flash_status(f"Error communicating with paste command: {e}")
                return False
            except Exception as e:
                log.error(f"Unexpected error during paste command communicate: {e}")
                if process.stderr:
                    stderr_output = process.stderr.read()
                self.flash_status(f"Error running paste command: {e}")
                return False

            if process.returncode != 0:
                stderr_text = (
                    stderr_output.decode("utf-8", errors="ignore").strip()
                    if stderr_output
                    else "No stderr output"
                )
                log.error(
                    f"Paste command failed with code {process.returncode}: {stderr_text}"
                )
                self.flash_status(f"Paste command error: {stderr_text[:100]}")
                return False
            else:
                log.info("Paste command successful.")
                return True
        except FileNotFoundError:
            log.error(f"Paste command not found: {cmd_args[0]}")
            self.flash_status(f"Error: Command '{cmd_args[0]}' not found.")
            return False
        except Exception as e:
            log.error(f"Error invoking paste command {cmd_args}: {e}")
            self.flash_status(f"Error starting paste command: {str(e)}")
            return False

    def _get_copy_command(self):
        """Gets the appropriate command for copying TO the clipboard."""
        if self._is_wayland:
            return str(COPY_TOOL_CMD)
        else:
            return str(X11_COPY_TOOL_CMD or COPY_TOOL_CMD)

    def copy_text_to_clipboard(self, text_value):
        """Use the configured command to place text into the clipboard."""
        copy_cmd = self._get_copy_command()
        if not copy_cmd:
            self.flash_status("Error: No copy command configured.")
            return False
        try:
            cmd_args = shlex.split(copy_cmd)
        except Exception as e:
            log.error(f"Could not parse COPY_TOOL_CMD ('{COPY_TOOL_CMD}'): {e}")
            self.flash_status("Error: Invalid copy command in config")
            return False
        try:
            process = subprocess.Popen(
                cmd_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if process.stdin:
                process.stdin.write(text_value.encode("utf-8"))
                process.stdin.close()
            else:
                log.error("Process stdin is None. Cannot write to clipboard.")
                self.flash_status("Error: Unable to write to clipboard")
                return False

            return True
        except subprocess.TimeoutExpired:
            log.error(f"Copy command timed out: {copy_cmd}")
            self.flash_status("Error: Copy command timed out")
            return False
        except FileNotFoundError:
            log.error(f"Copy command not found: {cmd_args[0]}")
            self.flash_status(f"Error: Copy command '{cmd_args[0]}' not found.")
            return False
        except Exception as e:
            log.error(f"Error copying text to clipboard: {e}")
            self.flash_status(f"Error copying text: {str(e)[:100]}")
            return False

    def copy_image_to_clipboard(self, image_path):
        """Use the configured command to place an image into the clipboard."""
        copy_cmd_base = self._get_copy_command()
        if not copy_cmd_base:
            self.flash_status("Error: No copy command configured.")
            return False

        try:
            if not os.path.isfile(image_path):
                log.error(f"Image file does not exist: {image_path}")
                self.flash_status("Error: Image file not found")
                return False

            mimetype, _ = mimetypes.guess_type(image_path)
            if not mimetype or not mimetype.startswith("image/"):
                image_ext = os.path.splitext(image_path)[1].lower()
                mimetype = (
                    f"image/{image_ext.lstrip('.')}" if image_ext else "image/png"
                )
                log.warning(
                    f"Could not guess mimetype for {image_path}, using {mimetype}"
                )

            try:
                base_cmd_args = shlex.split(copy_cmd_base)
            except Exception as e:
                log.error(f"Could not parse copy command ('{copy_cmd_base}'): {e}")
                self.flash_status(
                    f"Error: Invalid copy command: {copy_cmd_base[:50]}..."
                )
                return False

            cmd_args = base_cmd_args
            if "wl-copy" in os.path.basename(base_cmd_args[0]):
                cmd_args = base_cmd_args + ["--type", mimetype]

            with open(image_path, "rb") as img_file:
                try:
                    process = subprocess.Popen(
                        cmd_args,
                        stdin=img_file,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    stdout_data, stderr_data = process.communicate(timeout=10)

                    if process.returncode != 0:
                        err_msg = (
                            stderr_data.decode("utf-8", errors="ignore").strip()
                            or stdout_data.decode("utf-8", errors="ignore").strip()
                        )
                        log.error(
                            f"Image copy command failed (code {process.returncode}): {err_msg}"
                        )
                        self.flash_status(f"Image copy failed: {err_msg[:100]}")
                        return False

                    # self.flash_status("Image copied to clipboard")
                    log.info("Image copied successfully.")
                    return True

                except subprocess.TimeoutExpired:
                    log.error(f"Image copy command timed out: {cmd_args}")
                    self.flash_status("Error: Image copy timed out")
                    return False
                except FileNotFoundError:
                    log.error(f"Copy command not found: {cmd_args[0]}")
                    self.flash_status(f"Error: Copy command '{cmd_args[0]}' not found.")
                    return False
                except Exception as e:
                    log.error(f"Error copying image to clipboard: {e}")
                    self.flash_status(f"Error copying image: {str(e)[:100]}")
                    return False

        except Exception as e:
            log.error(f"Unexpected error preparing image copy: {e}", exc_info=True)
            self.flash_status(f"Error copying image: {str(e)[:100]}")
            return False

    def copy_selected_item_to_clipboard(self, with_paste_simulation=False):
        """Copies the selected item to the system clipboard and closes the window."""
        selected_row = self.list_box.get_selected_row()
        exit_timeout = 150
        if not selected_row:
            log.warning("Copy called with no row selected.")
            return

        original_index = getattr(selected_row, "item_index", -1)
        is_image = getattr(selected_row, "file_path") not in [None, "null"]
        item_value = getattr(selected_row, "item_value", None)

        if original_index == -1:
            log.error("Selected row missing valid item_index attribute.")
            self.flash_status("Error: Invalid selected item data.")
            return

        try:
            if not (0 <= original_index < len(self.items)):
                log.error(
                    f"Item with original index {original_index} no longer exists in master list."
                )
                self.flash_status("Error: Selected item no longer exists.")
                return

            item = self.items[original_index]

            def close_window_callback(window):
                if window and window.get_realized():
                    log.info("Closing window after successful copy.")
                    window.get_application().quit()
                return False

            copy_successful = False
            if is_image:
                image_path = item.get("filePath")
                if image_path and os.path.exists(image_path):
                    copy_successful = self.copy_image_to_clipboard(image_path)
                else:
                    log.error(
                        f"Image path invalid or file missing for item {original_index}: {image_path}"
                    )
                    self.flash_status("Image path invalid or file missing")
            else:
                text_to_copy = item.get("value")
                if text_to_copy is not None:
                    copy_successful = self.copy_text_to_clipboard(item_value)
                else:
                    log.error(f"Text item {original_index} has None value in data.")
                    self.flash_status("Cannot copy null text value.")

            if copy_successful:
                if ENTER_TO_PASTE or with_paste_simulation:
                    log.debug("Hiding window and scheduling paste simulation.")
                    self.window.hide()
                    GLib.timeout_add(
                        PASTE_SIMULATION_DELAY_MS or 150,
                        self._trigger_paste_simulation_and_quit,
                    )
                else:
                    GLib.timeout_add(100, self._quit_application)
            else:
                log.error("Copy operation failed.")
                self.flash_status("Error: Copy operation failed.")
                GLib.timeout_add(exit_timeout, close_window_callback, self.window)

        except Exception as e:
            log.error(f"Unexpected error during copy selection: {e}", exc_info=True)
            self.flash_status(f"Error copying: {str(e)}")

    def _trigger_paste_simulation_and_quit(self):
        """Called after a delay to run paste simulation and then quit."""
        log.debug("Attempting paste simulation...")
        paste_success = self.paste_from_clipboard_simulated()
        if paste_success:
            log.info("Paste simulation command successful.")
        else:
            log.warning("Paste simulation command failed or skipped.")
            # Optional: Show the window again if paste fails?
            # self.window.show()
            # self.flash_status("Paste failed. Check logs/dependencies (xdotool/wtype).")

        # Quit the application shortly after attempting paste
        GLib.timeout_add(50, self._quit_application)
        return False  # Prevent timer from repeating

    def _quit_application(self):
        """Safely quits the GTK application."""
        log.info("Quitting application.")
        app = self.window.get_application()
        if app:
            app.quit()
        return False  # Prevent timer from repeating

    def paste_from_clipboard_simulated(self):
        """Pastes FROM the clipboard by simulating key presses (Ctrl+V)."""
        if self._is_wayland:
            cmd_str = str(PASTE_SIMULATION_CMD_WAYLAND)
            tool_name = "wtype"
        else:
            cmd_str = str(PASTE_SIMULATION_CMD_X11)
            tool_name = "xdotool"

        if not cmd_str:
            log.error(
                f"Paste simulation command not configured for {'Wayland' if self._is_wayland else 'X11'}."
            )
            self.flash_status("Error: Paste simulation command not configured.")
            return False

        try:
            cmd_args = shlex.split(cmd_str)
        except Exception as e:
            log.error(f"Could not parse paste simulation command ('{cmd_str}'): {e}")
            self.flash_status(f"Error: Invalid Paste command: {cmd_str[:50]}...")
            return False

        log.debug(f"Executing paste simulation command: {cmd_args}")
        try:
            # Use run for simplicity, capture output for errors
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=5,  # Timeout for the simulation command
                check=False,  # Don't raise exception on non-zero exit code, check manually
            )

            if result.returncode != 0:
                error_output = result.stderr.strip() or result.stdout.strip()
                error_msg = f"Paste simulation ({tool_name}) failed (code {result.returncode}): {error_output}"
                log.error(error_msg)
                # Don't flash here, happens after window is hidden
                # self.flash_status(f"{tool_name} error: {error_output[:100]}")
                return False

            log.info(f"Paste simulation ({tool_name}) command successful.")
            return True

        except FileNotFoundError:
            error_msg = f"Paste simulation command not found: '{cmd_args[0]}'. Is '{tool_name}' installed?"
            log.error(error_msg)
            # self.flash_status(error_msg)
            return False
        except subprocess.TimeoutExpired:
            error_msg = f"Paste simulation command timed out: '{cmd_str}'"
            log.error(error_msg)
            # self.flash_status(error_msg)
            return False
        except Exception as e:
            error_msg = f"Error running paste simulation command '{cmd_str}': {e}"
            log.error(error_msg)
            # self.flash_status(error_msg[:150])
            return False

    def show_item_preview(self):
        """Shows the preview window for the selected item."""
        selected_row = self.list_box.get_selected_row()
        if not selected_row:
            return

        original_index = getattr(selected_row, "item_index", -1)
        # Correctly check if file_path exists and is not None/null string
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

    def on_preview_key_press(self, preview_window, event):
        """Handles key presses within the preview window."""
        keyval = event.keyval
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK

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
                    if hasattr(widget, 'get_children'):
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
                        if hasattr(widget, 'get_children'):
                            for child in widget.get_children():
                                result = find_search_entry(child)
                                if result:
                                    return result
                        return None
                    
                    search_entry = find_search_entry(search_bar)
                    if search_entry:
                        from .ui_components import _toggle_search_bar
                        _toggle_search_bar(search_bar, search_entry, textview)
                return True
            if ctrl and keyval == Gdk.KEY_b:
                # Format text with Ctrl+B
                from .ui_components import _format_text_content
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

    # --- Main Window Event Handlers ---

    def on_window_destroy(self, widget):
        log.info("Main window closed.")

    def on_key_press(self, widget, event):
        """Handles key presses on the main window."""
        keyval = event.keyval
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK

        if self.search_entry.has_focus():
            if keyval == Gdk.KEY_Escape:
                if self.search_entry.get_text():
                    self.search_entry.set_text("")
                else:
                    app = self.window.get_application()
                    if app:
                        app.quit()
                    else:
                        log.warning("Application instance is None. Cannot quit.")
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
            self.search_entry.show()
            self.search_entry.grab_focus()
            self.search_entry.select_region(0, -1)
            return True
        if keyval == Gdk.KEY_space:
            if selected_row:
                self.show_item_preview()
                return True
        if keyval == Gdk.KEY_p:
            if selected_row:
                self.toggle_pin_selected()
                return True
        if keyval in [Gdk.KEY_x, Gdk.KEY_Delete]:
            if selected_row:
                self.remove_selected_item()
                return True
        if keyval == Gdk.KEY_question or (shift and keyval == Gdk.KEY_slash):
            show_help_window(self.window, self.on_help_window_close)
            return True
        if keyval == Gdk.KEY_Tab:
            self.pin_filter_button.set_active(not self.pin_filter_button.get_active())
            self.list_box.grab_focus()
            return True
        if keyval == Gdk.KEY_Escape:
            if self.search_entry.get_text():
                self.search_entry.set_text("")
                self.list_box.grab_focus()
            else:
                app = self.window.get_application()
                if app:
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

    def on_search_changed(self, entry):
        """Handles changes in the search entry, debounced."""
        new_search_term = entry.get_text()
        if new_search_term != self.search_term:
            self.search_term = new_search_term
            if self._search_timer_id:
                GLib.source_remove(self._search_timer_id)
            self._search_timer_id = GLib.timeout_add(
                int(SEARCH_DEBOUNCE_MS or 250), self._trigger_filter_update
            )

    def _trigger_filter_update(self):
        """Updates filtering after search debounce timeout."""
        log.debug(f"Triggering filter update for search: '{self.search_term}'")
        self.update_filtered_items()
        self._search_timer_id = None
        return False

    def on_pin_filter_toggled(self, button):
        """Handles toggling the 'Pinned Only' filter button."""
        is_active = button.get_active()
        if is_active != self.show_only_pinned:
            self.show_only_pinned = is_active
            log.debug(f"Pin filter toggled: {'ON' if self.show_only_pinned else 'OFF'}")
            self.update_filtered_items()
            if len(self.list_box.get_children()) > 0:
                GLib.idle_add(self._focus_first_item)

    def on_compact_mode_toggled(self, button):
        """Handles compact mode toggle button state changes."""
        self.compact_mode = button.get_active()
        self.update_compact_mode()
        # Save the setting
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "compact_mode", str(self.compact_mode))
        config._save_config()

    def update_compact_mode(self):
        """Updates the UI based on compact mode state."""
        if self.compact_mode:
            self.main_box.get_style_context().add_class("compact-mode")
            # Adjust window size for compact mode
            self.window.resize(
                int(DEFAULT_WINDOW_WIDTH * 0.9), int(DEFAULT_WINDOW_HEIGHT * 0.9)
            )
            # Hide search entry in compact mode
            self.search_entry.hide()
        else:
            self.main_box.get_style_context().remove_class("compact-mode")
            # Restore default window size
            self.window.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
            # Show search entry in normal mode
            self.search_entry.show()

    # --- Scrolling Helpers ---

    def scroll_to_bottom(self):
        """Scrolls the list view to the bottom."""
        if not self.vadj:
            return

        def _do_scroll():
            if self.vadj:
                upper = self.vadj.get_upper()
                page_size = self.vadj.get_page_size()
                self.vadj.set_value(max(0, upper - page_size))
            return False

        GLib.idle_add(_do_scroll)

    def scroll_to_top(self):
        """Scrolls the list view to the top."""
        if not self.vadj:
            return

        def _do_scroll():
            if self.vadj:
                self.vadj.set_value(self.vadj.get_lower())
            return False

        GLib.idle_add(_do_scroll)

    def on_search_focus_out(self, entry, event):
        """Handles when search entry loses focus."""
        if self.compact_mode:
            self.search_entry.hide()
        return False
