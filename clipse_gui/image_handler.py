import threading
import os
import tempfile
import urllib.request
import base64
import re
from collections import OrderedDict
from functools import lru_cache
from gi.repository import GdkPixbuf, GLib
import logging

log = logging.getLogger(__name__)

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}


class ImageHandler:
    """Handles background loading and caching of image thumbnails."""

    def __init__(self, cache_max_size=50):
        self.cache_max_size = cache_max_size
        self.image_cache = OrderedDict()  # Manual LRU cache for loaded Pixbufs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @lru_cache(maxsize=128)
    def _load_pixbuf_scaled(self, image_path, width, height):
        """Load and scale a local file; result is lru_cache'd."""
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(
                image_path, width, height, True
            )
        except GLib.Error as e:
            if not e.matches(
                GdkPixbuf.PixbufError.FAILED, GdkPixbuf.PixbufError.FAILED
            ) and not e.matches(GLib.FileError.NOENT, GLib.FileError.NOENT):
                log.warning(
                    f"Failed to load/scale {os.path.basename(image_path)}: {e.message}"
                )
            return None
        except Exception as e:
            log.error(f"Unexpected error loading {image_path}: {e}")
            return None

    def _cache_get(self, key):
        if key in self.image_cache:
            self.image_cache.move_to_end(key)
            return self.image_cache[key]
        return None

    def _cache_put(self, key, pixbuf):
        self.image_cache[key] = pixbuf
        if len(self.image_cache) > self.cache_max_size:
            self.image_cache.popitem(last=False)

    def _scale_pixbuf(self, pixbuf, width, height):
        """Scale pixbuf to fit inside width×height, maintaining aspect ratio.
        Never upscales."""
        orig_w = pixbuf.get_width()
        orig_h = pixbuf.get_height()
        if orig_w <= 0 or orig_h <= 0:
            return pixbuf
        scale = min(width / orig_w, height / orig_h, 1.0)
        new_w = max(1, int(orig_w * scale))
        new_h = max(1, int(orig_h * scale))
        return pixbuf.scale_simple(new_w, new_h, GdkPixbuf.InterpType.BILINEAR)

    def _dispatch(self, target, placeholder, pixbuf, error):
        """Schedule a UI update callback on the main thread."""
        GLib.idle_add(
            self._update_widget, target, placeholder, pixbuf, error
        )

    @staticmethod
    def _update_widget(target_widget, placeholder_widget, pixbuf, error_message):
        """Generic UI callback: swap placeholder for image or error label."""
        try:
            if placeholder_widget and placeholder_widget.get_parent() == target_widget:
                target_widget.remove(placeholder_widget)
            for child in target_widget.get_children():
                target_widget.remove(child)

            if pixbuf:
                img = Gtk.Image.new_from_pixbuf(pixbuf)
                img.set_halign(Gtk.Align.CENTER)
                img.set_valign(Gtk.Align.CENTER)
                target_widget.add(img)
            else:
                lbl = Gtk.Label(label=error_message or "[Error]")
                lbl.set_halign(Gtk.Align.CENTER)
                lbl.set_valign(Gtk.Align.CENTER)
                target_widget.add(lbl)

            target_widget.show_all()
        except Exception as e:
            log.debug(f"_update_widget: widget may have been destroyed ({e})")
        return False  # Don't repeat

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_image_async(
        self, image_path, target_widget, placeholder_widget, width, height, update_callback
    ):
        """Load a local image file in the background."""
        if not image_path or image_path == "null":
            GLib.idle_add(update_callback, target_widget, placeholder_widget, None, "[Invalid Path]")
            return
        thread = threading.Thread(
            target=self._load_image_thread,
            args=(image_path, target_widget, placeholder_widget, width, height, update_callback),
            daemon=True,
        )
        thread.start()

    def _load_image_thread(
        self, image_path, target_widget, placeholder_widget, width, height, update_callback
    ):
        error_message = None
        pixbuf = None
        try:
            cache_key = f"{image_path}-{width}x{height}"
            pixbuf = self._cache_get(cache_key)
            if pixbuf is None:
                pixbuf = self._load_pixbuf_scaled(image_path, width, height)
                if pixbuf:
                    self._cache_put(cache_key, pixbuf)
                else:
                    error_message = "[Load Error]"
        except Exception as e:
            log.error(f"Image thread error for {image_path}: {e}")
            error_message = "[Thread Error]"
        GLib.idle_add(update_callback, target_widget, placeholder_widget, pixbuf, error_message)

    def load_remote_image_async(
        self, url, target_widget, placeholder_widget, width, height, update_callback
    ):
        """Download a remote image URL and load it in the background."""
        if not url or not url.startswith(("http://", "https://")):
            GLib.idle_add(update_callback, target_widget, placeholder_widget, None, "[Invalid URL]")
            return
        thread = threading.Thread(
            target=self._load_remote_image_thread,
            args=(url, target_widget, placeholder_widget, width, height, update_callback),
            daemon=True,
        )
        thread.start()

    def _load_remote_image_thread(
        self, url, target_widget, placeholder_widget, width, height, update_callback
    ):
        pixbuf = None
        error_message = None
        temp_file = None
        try:
            cache_key = f"remote:{url}-{width}x{height}"
            pixbuf = self._cache_get(cache_key)
            if pixbuf is not None:
                GLib.idle_add(update_callback, target_widget, placeholder_widget, pixbuf, None)
                return

            # Determine file suffix from URL
            url_lower = url.lower().split("?")[0]
            for ext in (".png", ".gif", ".bmp", ".webp", ".jpg", ".jpeg", ".svg"):
                if url_lower.endswith(ext):
                    suffix = ext if ext != ".jpeg" else ".jpg"
                    break
            else:
                suffix = ".tmp"

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                temp_file = f.name

            req = urllib.request.Request(url, headers=_REQUEST_HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            with open(temp_file, "wb") as f:
                f.write(data)

            if suffix == ".svg":
                with open(temp_file, "r", errors="ignore") as f:
                    svg_content = f.read()
                self._load_svg_thread(
                    svg_content, target_widget, placeholder_widget, width, height, update_callback
                )
                return

            raw = GdkPixbuf.Pixbuf.new_from_file(temp_file)
            if raw:
                pixbuf = self._scale_pixbuf(raw, width, height)
                self._cache_put(cache_key, pixbuf)
            else:
                error_message = "[Load Error]"

        except urllib.error.HTTPError as e:
            log.warning(f"HTTP {e.code} downloading {url}")
            error_message = f"[HTTP {e.code}]"
        except Exception as e:
            log.warning(f"Failed to download {url}: {e}")
            error_message = "[Download Error]"
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass

        GLib.idle_add(update_callback, target_widget, placeholder_widget, pixbuf, error_message)

    def load_svg_async(
        self, svg_content, target_widget, placeholder_widget, width, height, update_callback
    ):
        """Render SVG markup and load it in the background."""
        if not svg_content or not svg_content.strip():
            GLib.idle_add(update_callback, target_widget, placeholder_widget, None, "[Empty SVG]")
            return
        thread = threading.Thread(
            target=self._load_svg_thread,
            args=(svg_content, target_widget, placeholder_widget, width, height, update_callback),
            daemon=True,
        )
        thread.start()

    def _load_svg_thread(
        self, svg_content, target_widget, placeholder_widget, width, height, update_callback
    ):
        pixbuf = None
        error_message = None
        try:
            cache_key = f"svg:{hash(svg_content)}-{width}x{height}"
            pixbuf = self._cache_get(cache_key)
            if pixbuf is None:
                svg_bytes = svg_content.encode("utf-8") if isinstance(svg_content, str) else svg_content
                loader = GdkPixbuf.PixbufLoader()
                loader.write(svg_bytes)
                loader.close()
                raw = loader.get_pixbuf()
                if raw:
                    pixbuf = self._scale_pixbuf(raw, width, height)
                    self._cache_put(cache_key, pixbuf)
                else:
                    error_message = "[SVG Render Error]"
        except GLib.Error as e:
            log.warning(f"SVG render failed: {e.message}")
            error_message = "[SVG Error]"
        except Exception as e:
            log.error(f"Unexpected SVG error: {e}")
            error_message = "[Render Error]"
        GLib.idle_add(update_callback, target_widget, placeholder_widget, pixbuf, error_message)

    def load_data_uri_async(
        self, data_uri, target_widget, placeholder_widget, width, height, update_callback
    ):
        """Parse a data URI and load the embedded image in the background."""
        if not data_uri or not data_uri.startswith("data:"):
            GLib.idle_add(update_callback, target_widget, placeholder_widget, None, "[Invalid Data URI]")
            return
        thread = threading.Thread(
            target=self._load_data_uri_thread,
            args=(data_uri, target_widget, placeholder_widget, width, height, update_callback),
            daemon=True,
        )
        thread.start()

    def _load_data_uri_thread(
        self, data_uri, target_widget, placeholder_widget, width, height, update_callback
    ):
        pixbuf = None
        error_message = None
        try:
            cache_key = f"datauri:{hash(data_uri)}-{width}x{height}"
            pixbuf = self._cache_get(cache_key)
            if pixbuf is not None:
                GLib.idle_add(update_callback, target_widget, placeholder_widget, pixbuf, None)
                return

            pattern = r"^data:(?P<mime>[^;,]+)?(?:;(?P<enc>base64))?,(?P<data>.+)$"
            m = re.match(pattern, data_uri, re.DOTALL)
            if not m:
                error_message = "[Parse Error]"
            else:
                mime = (m.group("mime") or "").lower()
                enc = m.group("enc")
                raw_data = m.group("data")

                if enc == "base64":
                    image_bytes = base64.b64decode(raw_data)
                else:
                    from urllib.parse import unquote
                    image_bytes = unquote(raw_data).encode("utf-8")

                if "svg" in mime:
                    self._load_svg_thread(
                        image_bytes.decode("utf-8", errors="replace"),
                        target_widget, placeholder_widget, width, height, update_callback,
                    )
                    return

                # Map mime → GdkPixbuf loader type
                type_map = {
                    "image/png": "png", "image/apng": "png",
                    "image/jpeg": "jpeg", "image/jpg": "jpeg",
                    "image/gif": "gif", "image/bmp": "bmp", "image/webp": "webp",
                }
                loader_type = type_map.get(mime)
                loader = (
                    GdkPixbuf.PixbufLoader.new_with_type(loader_type)
                    if loader_type
                    else GdkPixbuf.PixbufLoader()
                )
                loader.write(image_bytes)
                loader.close()
                raw = loader.get_pixbuf()
                if raw:
                    pixbuf = self._scale_pixbuf(raw, width, height)
                    self._cache_put(cache_key, pixbuf)
                else:
                    error_message = "[Load Error]"

        except (base64.binascii.Error, ValueError) as e:
            log.warning(f"Data URI decode error: {e}")
            error_message = "[Decode Error]"
        except GLib.Error as e:
            log.warning(f"Data URI pixbuf error: {e.message}")
            error_message = "[Load Error]"
        except Exception as e:
            log.error(f"Unexpected data URI error: {e}")
            error_message = "[Error]"

        GLib.idle_add(update_callback, target_widget, placeholder_widget, pixbuf, error_message)

    def clear_cache(self):
        """Clear all cached pixbufs."""
        self.image_cache.clear()
        self._load_pixbuf_scaled.cache_clear()
        log.info("Image cache cleared.")


# Needed for the static _update_widget method
from gi.repository import Gtk  # noqa: E402
