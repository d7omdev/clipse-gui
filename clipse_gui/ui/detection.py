"""Content type detectors for clipboard text values (URLs, images, SVG, data URIs)."""

_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff", ".tif")


def _is_image_url(text):
    """True if text is an http(s) URL pointing to a recognised image extension."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip().lower()
    if not (t.startswith("http://") or t.startswith("https://")):
        return False
    return any(t.split("?")[0].endswith(ext) for ext in _IMAGE_EXTENSIONS)


def _is_svg_content(text):
    """True if text appears to be inline SVG markup."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    return t.startswith("<svg") or "<svg" in t[:200]


def _is_data_uri(text):
    """True if text is a base64-encoded image data URI."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    return t.startswith("data:image") and ";base64," in t


def _is_url(text):
    """True if text is any http(s) URL."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip().lower()
    return t.startswith("http://") or t.startswith("https://")
