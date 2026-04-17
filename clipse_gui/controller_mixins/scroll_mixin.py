"""Scroll handling and lazy-loading row creation."""

import logging

from gi.repository import GLib

from ..constants import LOAD_BATCH_SIZE, LOAD_THRESHOLD_FACTOR

log = logging.getLogger(__name__)


class ScrollMixin:

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
