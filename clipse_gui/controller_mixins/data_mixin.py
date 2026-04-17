"""Data loading, persistence, and history-update callbacks."""

import logging

from gi.repository import GLib

from ..constants import SAVE_DEBOUNCE_MS

log = logging.getLogger(__name__)


class DataMixin:

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
