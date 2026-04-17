"""List view population, row creation, status label, and flash messages."""

import logging
from functools import partial

from gi.repository import GLib, Gtk

from ..constants import HIGHLIGHT_SEARCH, INITIAL_LOAD_COUNT
from ..ui_components import create_list_row_widget

log = logging.getLogger(__name__)


class ListViewMixin:

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
                    item_info,
                    self.image_handler,
                    self._update_row_image_widget,
                    self.compact_mode,
                    self.hover_to_select,
                    self._on_row_single_click,
                    self.search_term,
                    HIGHLIGHT_SEARCH,
                )
                if row:
                    row.item_index = item_info["original_index"]
                    file_path = item_info["item"].get("filePath")
                    row.is_image = bool(file_path and isinstance(file_path, str))
                    row.item_value = item_info["item"].get("value")
                    row.item_pinned = item_info["item"].get("pinned", False)

                    # Apply selection styling if this item is selected
                    if row.item_index in self.selected_indices:
                        context = row.get_style_context()
                        context.add_class("selected-row")

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

        # Show selection count if in selection mode
        if self.selection_mode and self.selected_indices:
            selected_count = len(self.selected_indices)
            status_parts.append(
                f"{selected_count} item{'s' if selected_count != 1 else ''} selected"
            )

        if self.show_only_pinned:
            status_parts.append(f"Showing {count} pinned items")
        elif self.search_term:
            status_parts.append(f"Found {count} items ({total} total)")
        else:
            status_parts.append(f"{total} items")

        if not self.selection_mode:
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
