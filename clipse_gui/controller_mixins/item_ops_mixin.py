"""Item operations: pin toggle, single delete, batch delete, clear all."""

import logging

from gi.repository import Gtk

from ..constants import PROTECT_PINNED_ITEMS
from ..ui_components import animate_pin_shake

log = logging.getLogger(__name__)


class ItemOpsMixin:

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
                            # Animate the rotation wiggle effect
                            animate_pin_shake(hbox, is_pinned)
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
                item = self.items[original_index_to_remove]

                # Check if the item is pinned and protection is enabled
                if PROTECT_PINNED_ITEMS and item.get("pinned", False):
                    self.flash_status("Cannot delete pinned item: protection enabled")
                    return

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

    def delete_selected_items(self):
        """Deletes all selected items with confirmation."""
        if not self.selected_indices:
            self.flash_status("No items selected for deletion")
            return

        # Count pinned vs non-pinned selected items
        pinned_count = 0
        non_pinned_count = 0
        indices_to_delete = []

        for idx in self.selected_indices:
            if 0 <= idx < len(self.items):
                item = self.items[idx]
                if item.get("pinned", False):
                    pinned_count += 1
                    if not PROTECT_PINNED_ITEMS:
                        indices_to_delete.append(idx)
                else:
                    non_pinned_count += 1
                    indices_to_delete.append(idx)

        if not indices_to_delete:
            if PROTECT_PINNED_ITEMS and pinned_count > 0:
                self.flash_status(
                    f"Cannot delete: all {pinned_count} selected items are pinned (protection enabled)"
                )
            else:
                self.flash_status("No items to delete")
            return

        # Build confirmation message
        total_to_delete = len(indices_to_delete)
        protected_count = pinned_count if PROTECT_PINNED_ITEMS else 0

        message = f"Delete {total_to_delete} selected item{'s' if total_to_delete != 1 else ''}?"
        if protected_count > 0:
            message += f"\n\n({protected_count} pinned item{'s' if protected_count != 1 else ''} will be skipped due to protection)"

        # Show confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            destroy_with_parent=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Confirm Deletion",
        )
        dialog.format_secondary_text(message)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        delete_button = dialog.add_button("Delete", Gtk.ResponseType.OK)
        delete_button.get_style_context().add_class("destructive-action")

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            # Sort indices in descending order to delete from end to beginning
            indices_to_delete.sort(reverse=True)

            for idx in indices_to_delete:
                if 0 <= idx < len(self.items):
                    del self.items[idx]

            # Exit selection mode and clear selections
            self.selection_mode = False
            self.selected_indices.clear()
            self.main_box.get_style_context().remove_class("selection-mode")

            # Save and refresh
            self.schedule_save_history()
            self.update_filtered_items()

            self.flash_status(
                f"Deleted {total_to_delete} item{'s' if total_to_delete != 1 else ''}"
            )
            log.info(f"Deleted {total_to_delete} selected items")

    def clear_all_items(self):
        """Clears all non-pinned items with confirmation."""
        if not self.items:
            self.flash_status("No items to clear")
            return

        # Count pinned vs non-pinned items
        pinned_count = sum(1 for item in self.items if item.get("pinned", False))
        non_pinned_count = len(self.items) - pinned_count

        if PROTECT_PINNED_ITEMS and non_pinned_count == 0:
            self.flash_status(
                f"Cannot clear: all {pinned_count} items are pinned (protection enabled)"
            )
            return

        # Determine what will be deleted
        if PROTECT_PINNED_ITEMS:
            items_to_delete = non_pinned_count
            message = f"Delete all {non_pinned_count} non-pinned item{'s' if non_pinned_count != 1 else ''}?"
            if pinned_count > 0:
                message += f"\n\n({pinned_count} pinned item{'s' if pinned_count != 1 else ''} will be kept)"
        else:
            items_to_delete = len(self.items)
            message = f"Delete ALL {items_to_delete} item{'s' if items_to_delete != 1 else ''}?"
            if pinned_count > 0:
                message += f"\n\nWarning: This includes {pinned_count} pinned item{'s' if pinned_count != 1 else ''}!"

        # Show confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            destroy_with_parent=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Clear All Items",
        )
        dialog.format_secondary_text(message)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        clear_button = dialog.add_button("Clear All", Gtk.ResponseType.OK)
        clear_button.get_style_context().add_class("destructive-action")

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            if PROTECT_PINNED_ITEMS:
                # Keep only pinned items
                self.items = [item for item in self.items if item.get("pinned", False)]
            else:
                # Delete everything
                self.items = []

            # Exit selection mode if active
            if self.selection_mode:
                self.selection_mode = False
                self.selected_indices.clear()
                self.main_box.get_style_context().remove_class("selection-mode")

            # Save and refresh
            self.schedule_save_history()
            self.update_filtered_items()

            self.flash_status(
                f"Cleared {items_to_delete} item{'s' if items_to_delete != 1 else ''}"
            )
            log.info(f"Cleared {items_to_delete} items")
