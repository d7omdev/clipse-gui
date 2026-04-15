"""Search input handling, filtering, and pin-filter toggle."""

import logging

from gi.repository import GLib

from ..constants import SEARCH_DEBOUNCE_MS
from ..utils import fuzzy_search

log = logging.getLogger(__name__)


class SearchMixin:

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

    def on_search_focus_out(self, entry, event):
        """Handles when search entry loses focus."""
        if self.compact_mode:
            self.search_entry.hide()
        return False
