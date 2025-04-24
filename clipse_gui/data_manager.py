import json
import os
import threading
from pathlib import Path
from gi.repository import GLib
import logging

from .constants import HISTORY_FILE_PATH

log = logging.getLogger(__name__)


class DataManager:
    """Handles loading and saving clipboard history data."""

    def __init__(self, update_callback=None):
        self.file_path = HISTORY_FILE_PATH
        self._save_lock = threading.Lock()
        self.update_callback = update_callback
        self._last_mtime = None
        self._last_size = None
        log.debug(f"DataManager initialized with history file: {self.file_path}")

    def load_history(self):
        """Loads history from the JSON file."""
        items = []
        if os.path.exists(self.file_path):
            try:
                current_size = os.path.getsize(self.file_path)
                if current_size == 0:
                    log.warning(
                        f"History file {self.file_path} is empty. Starting fresh."
                    )
                    return []

                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    loaded_items = data.get("clipboardHistory", [])
                    valid_items = []
                    for item in loaded_items:
                        if (
                            isinstance(item, dict)
                            and "value" in item
                            and "recorded" in item
                        ):
                            item["pinned"] = bool(item.get("pinned", False))
                            if item.get("filePath") and not isinstance(
                                item.get("filePath"), str
                            ):
                                item["filePath"] = None
                            valid_items.append(item)
                        else:
                            log.warning(f"Skipping invalid item during load: {item}")
                    items = valid_items
                log.debug(f"Loaded {len(items)} items from {self.file_path}")
            except json.JSONDecodeError as e:
                log.error(f"Failed to decode JSON from {self.file_path}: {e}")
            except FileNotFoundError:
                log.error(
                    f"History file not found during load (race condition?): {self.file_path}"
                )
            except Exception as e:
                log.error(f"Error loading history file {self.file_path}: {e}")
        else:
            log.info(f"History file not found: {self.file_path}. Starting fresh.")

        try:
            items.sort(key=lambda x: x.get("recorded", ""), reverse=True)
        except Exception as e:
            log.error(f"Error sorting history items: {e}")

        return items

    def save_history(self, items, callback_on_error=None):
        """Saves history to the JSON file in a background thread."""
        items_copy = list(items)
        thread = threading.Thread(
            target=self._save_thread_target,
            args=(items_copy, callback_on_error),
            daemon=True,
        )
        thread.start()

    def _save_thread_target(self, items_to_save, callback_on_error):
        """Actual saving logic executed in a separate thread."""
        with self._save_lock:
            temp_path = None
            try:
                Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)

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
                try:
                    stat_res = os.stat(self.file_path)
                    self._last_mtime = stat_res.st_mtime
                    self._last_size = stat_res.st_size
                except OSError:
                    pass
            except Exception as e:
                log.error(f"Error saving history to {self.file_path}: {e}")
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError as rm_e:
                        log.error(
                            f"Failed to remove temporary save file {temp_path}: {rm_e}"
                        )
                if callback_on_error:
                    GLib.idle_add(callback_on_error, f"Error saving: {e}")

    def _start_history_watcher(self, callback, interval_ms=300):
        """Starts a periodic file watcher to sync clipboard history."""
        try:
            if os.path.exists(self.file_path):
                stat_res = os.stat(self.file_path)
                self._last_mtime = stat_res.st_mtime
                self._last_size = stat_res.st_size
            else:
                self._last_mtime = None
                self._last_size = None
        except OSError as e:
            log.error(
                f"Error getting initial state for history watcher {self.file_path}: {e}"
            )
            self._last_mtime = None
            self._last_size = None

        def check_for_changes():
            try:
                if not os.path.exists(self.file_path):
                    if self._last_mtime is not None or self._last_size is not None:
                        log.warning(f"History file {self.file_path} disappeared.")
                        self._last_mtime = None
                        self._last_size = None
                        GLib.idle_add(callback, [])
                    return True

                stat_res = os.stat(self.file_path)
                current_mtime = stat_res.st_mtime
                current_size = stat_res.st_size

                changed = False
                if self._last_mtime is None or self._last_size is None:
                    changed = True
                elif (
                    current_mtime != self._last_mtime or current_size != self._last_size
                ):
                    changed = True

                if changed:
                    log.info(
                        f"History file change detected ({self.file_path}). Reloading..."
                    )
                    self._last_mtime = current_mtime
                    self._last_size = current_size
                    loaded_items = self.load_history()
                    GLib.idle_add(callback, loaded_items)

            except FileNotFoundError:
                if self._last_mtime is not None or self._last_size is not None:
                    log.warning(
                        f"History file {self.file_path} not found during check."
                    )
                    self._last_mtime = None
                    self._last_size = None
                    GLib.idle_add(callback, [])
            except Exception as e:
                log.error(f"Error while watching history file {self.file_path}: {e}")

            return True

        log.debug(
            f"Starting history watcher for {self.file_path} every {interval_ms}ms"
        )
        GLib.timeout_add(interval_ms, check_for_changes)
