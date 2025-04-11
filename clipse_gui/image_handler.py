import threading
import os
from collections import OrderedDict
from functools import lru_cache
from gi.repository import GdkPixbuf, GLib
import logging

log = logging.getLogger(__name__)


class ImageHandler:
    """Handles background loading and caching of image thumbnails."""

    def __init__(self, cache_max_size=50):
        self.cache_max_size = cache_max_size
        self.image_cache = OrderedDict()  # Manual LRU cache for loaded Pixbufs

    @lru_cache(maxsize=128)  # Cache the scaling function results directly
    def _load_pixbuf_scaled(self, image_path, width, height):
        """Internal function to load and scale pixbuf, cached by lru_cache."""
        try:
            # Maintain aspect ratio during scaling
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(
                image_path, width, height, True
            )
        except GLib.Error as e:
            # Don't log common errors like file not found frequently
            if not e.matches(
                GdkPixbuf.PixbufError, GdkPixbuf.PixbufError.FAILED
            ) and not e.matches(GLib.FileError, GLib.FileError.NOENT):
                log.warning(
                    f"Failed to load/scale image {os.path.basename(image_path)}: {e.message}"
                )
            return None
        except Exception as e:
            log.error(f"Unexpected error loading/scaling image {image_path}: {e}")
            return None

    def load_image_async(
        self,
        image_path,
        target_widget,
        placeholder_widget,
        width,
        height,
        update_callback,
    ):
        """Loads an image in the background and updates the UI via callback."""
        if not image_path or image_path == "null":
            GLib.idle_add(
                update_callback,
                target_widget,
                placeholder_widget,
                None,
                "[Invalid Path]",
            )
            return

        thread = threading.Thread(
            target=self._load_image_thread,
            args=(
                image_path,
                target_widget,
                placeholder_widget,
                width,
                height,
                update_callback,
            ),
            daemon=True,
        )
        thread.start()

    def _load_image_thread(
        self,
        image_path,
        target_widget,
        placeholder_widget,
        width,
        height,
        update_callback,
    ):
        """Background thread logic for loading image and checking cache."""
        error_message = None
        try:
            cache_key = f"{image_path}-{width}x{height}"

            # Check manual LRU cache
            if cache_key in self.image_cache:
                pixbuf = self.image_cache[cache_key]
                self.image_cache.move_to_end(cache_key)  # Update LRU order
            else:
                # Call the lru_cached internal function
                pixbuf = self._load_pixbuf_scaled(image_path, width, height)
                if pixbuf:
                    self.image_cache[cache_key] = pixbuf
                    # Enforce cache size limit
                    if len(self.image_cache) > self.cache_max_size:
                        self.image_cache.popitem(last=False)
                else:
                    error_message = "[Load Error]"

            # Schedule UI update in the main thread
            GLib.idle_add(
                update_callback,
                target_widget,
                placeholder_widget,
                pixbuf,
                error_message,
            )

        except Exception as e:
            log.error(f"Error in image loading thread for {image_path}: {e}")
            # Schedule UI update with error in the main thread
            GLib.idle_add(
                update_callback,
                target_widget,
                placeholder_widget,
                None,
                "[Thread Error]",
            )

    def clear_cache(self):
        """Clears the image cache."""
        self.image_cache.clear()
        self._load_pixbuf_scaled.cache_clear()  # Clear lru_cache too
        log.info("Image cache cleared.")
