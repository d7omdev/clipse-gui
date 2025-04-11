import json
import os
import threading
from pathlib import Path
from gi.repository import GLib
import logging

# Setup logging
log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class DataManager:
    """Handles loading and saving clipboard history data."""

    def __init__(self, file_path):
        self.file_path = file_path
        self._save_lock = threading.Lock()  # Lock for saving operation

    def load_history(self):
        """Loads history from the JSON file."""
        items = []
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    loaded_items = data.get("clipboardHistory", [])
                    # Data validation/cleaning
                    for item in loaded_items:
                        item["pinned"] = bool(item.get("pinned", False))
                        if "value" not in item:
                            item["value"] = ""
                        if "recorded" not in item:
                            item["recorded"] = ""
                    items = loaded_items
                log.info(f"Loaded {len(items)} items from {self.file_path}")
            except json.JSONDecodeError as e:
                log.error(f"Failed to decode JSON from {self.file_path}: {e}")
            except Exception as e:
                log.error(f"Error loading history file {self.file_path}: {e}")
        else:
            log.info(f"History file not found: {self.file_path}. Starting fresh.")

        # Sort by date descending (newest first)
        items.sort(key=lambda x: x.get("recorded", ""), reverse=True)
        return items

    def save_history(self, items, callback_on_error=None):
        """Saves history to the JSON file in a background thread."""
        # Pass a copy to the thread
        items_copy = list(items)
        thread = threading.Thread(
            target=self._save_thread_target,
            args=(items_copy, callback_on_error),
            daemon=True,
        )
        thread.start()

    def _save_thread_target(self, items_to_save, callback_on_error):
        """Actual saving logic executed in a separate thread."""
        # Use a lock to prevent potential race conditions if save is triggered rapidly
        with self._save_lock:
            try:
                # Ensure parent directory exists
                Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)

                # Write to a temporary file first
                temp_path = f"{self.file_path}.temp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {"clipboardHistory": items_to_save},
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )
                    f.flush()
                    os.fsync(f.fileno())

                os.replace(temp_path, self.file_path)
            except Exception as e:
                log.error(f"Error saving history to {self.file_path}: {e}")
                if callback_on_error:
                    GLib.idle_add(callback_on_error, f"Error saving: {e}")
