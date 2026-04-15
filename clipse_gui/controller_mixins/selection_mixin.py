"""Multi-select mode and per-item selection toggles."""

import logging

log = logging.getLogger(__name__)


class SelectionMixin:

    def toggle_selection_mode(self):
        """Toggles selection mode on/off."""
        self.selection_mode = not self.selection_mode

        if self.selection_mode:
            # Entering selection mode
            self.main_box.get_style_context().add_class("selection-mode")
            # Show visual indicator
            self.selection_mode_banner.show()
            log.info("Entered selection mode")
            self.flash_status("Selection mode: ON (Space to select, v to exit)")
        else:
            # Exiting selection mode - clear selections
            self.deselect_all_items()
            self.main_box.get_style_context().remove_class("selection-mode")
            # Hide visual indicator
            self.selection_mode_banner.hide()
            log.info("Exited selection mode")
            self.flash_status("Selection mode: OFF")

        self.update_status_label()

    def toggle_item_selection(self):
        """Toggles the selection state of the currently focused item."""
        if not self.selection_mode:
            log.warning("Cannot toggle item selection: not in selection mode")
            return

        selected_row = self.list_box.get_selected_row()
        if not selected_row or not hasattr(selected_row, "item_index"):
            return

        original_index = selected_row.item_index
        context = selected_row.get_style_context()

        if original_index in self.selected_indices:
            # Deselect
            self.selected_indices.remove(original_index)
            context.remove_class("selected-row")
            log.info(
                f"Deselected item at index {original_index}, classes: {context.list_classes()}"
            )
        else:
            # Select
            self.selected_indices.add(original_index)
            context.add_class("selected-row")
            log.info(
                f"Selected item at index {original_index}, classes: {context.list_classes()}"
            )

        self.update_status_label()

    def select_all_items(self):
        """Selects all currently visible items."""
        if not self.selection_mode:
            # Auto-enter selection mode if not already in it
            self.toggle_selection_mode()

        self.selected_indices.clear()

        for row in self.list_box.get_children():
            if hasattr(row, "item_index"):
                original_index = row.item_index
                self.selected_indices.add(original_index)
                context = row.get_style_context()
                context.add_class("selected-row")

        count = len(self.selected_indices)
        log.info(f"Selected all {count} visible items")
        self.flash_status(f"Selected {count} items")
        self.update_status_label()

    def deselect_all_items(self):
        """Clears all selections."""
        for row in self.list_box.get_children():
            if hasattr(row, "item_index"):
                context = row.get_style_context()
                context.remove_class("selected-row")

        count = len(self.selected_indices)
        self.selected_indices.clear()
        log.info(f"Deselected all items (was {count})")
        if count > 0:
            self.flash_status("All items deselected")
        self.update_status_label()
