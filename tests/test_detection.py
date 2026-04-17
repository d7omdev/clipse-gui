"""Tests for clipse_gui/ui/detection.py — pure content-type detector functions."""

import pytest

from clipse_gui.ui.detection import _is_data_uri, _is_image_url, _is_svg_content, _is_url


# ---------------------------------------------------------------------------
# _is_image_url
# ---------------------------------------------------------------------------

class TestIsImageUrl:
    @pytest.mark.parametrize("ext", [
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".svg", ".bmp", ".ico", ".tiff", ".tif",
    ])
    def test_http_with_each_extension(self, ext):
        assert _is_image_url(f"http://example.com/image{ext}") is True

    @pytest.mark.parametrize("ext", [
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".svg", ".bmp", ".ico", ".tiff", ".tif",
    ])
    def test_https_with_each_extension(self, ext):
        assert _is_image_url(f"https://example.com/photo{ext}") is True

    def test_query_string_ignored_for_extension(self):
        assert _is_image_url("https://cdn.example.com/img.png?v=2&w=800") is True

    def test_query_string_with_non_image_extension_returns_false(self):
        assert _is_image_url("https://example.com/page.html?img=photo.jpg") is False

    def test_non_image_extension_returns_false(self):
        assert _is_image_url("https://example.com/document.pdf") is False

    def test_html_extension_returns_false(self):
        assert _is_image_url("https://example.com/index.html") is False

    def test_no_extension_returns_false(self):
        assert _is_image_url("https://example.com/image") is False

    def test_ftp_scheme_returns_false(self):
        assert _is_image_url("ftp://example.com/photo.jpg") is False

    def test_bare_domain_returns_false(self):
        assert _is_image_url("example.com/photo.jpg") is False

    def test_none_returns_false(self):
        assert _is_image_url(None) is False

    def test_empty_string_returns_false(self):
        assert _is_image_url("") is False

    def test_integer_returns_false(self):
        assert _is_image_url(123) is False

    def test_whitespace_only_returns_false(self):
        assert _is_image_url("   ") is False

    def test_whitespace_padded_valid_url(self):
        assert _is_image_url("  https://example.com/photo.png  ") is True

    def test_uppercase_extension_treated_as_match(self):
        # strip().lower() normalises — .PNG becomes .png
        assert _is_image_url("https://example.com/image.PNG") is True

    def test_uppercase_scheme_treated_as_match(self):
        assert _is_image_url("HTTPS://example.com/image.png") is True

    def test_deeply_nested_path(self):
        assert _is_image_url("https://cdn.example.com/a/b/c/photo.webp") is True


# ---------------------------------------------------------------------------
# _is_svg_content
# ---------------------------------------------------------------------------

class TestIsSvgContent:
    def test_starts_with_svg_tag(self):
        assert _is_svg_content("<svg xmlns='http://www.w3.org/2000/svg'>...</svg>") is True

    def test_svg_within_first_200_chars(self):
        prefix = "X" * 100
        assert _is_svg_content(prefix + "<svg>") is True

    def test_svg_beyond_200_chars_returns_false(self):
        prefix = "X" * 201
        assert _is_svg_content(prefix + "<svg>") is False

    def test_whitespace_before_svg_tag(self):
        assert _is_svg_content("   <svg>content</svg>") is True

    def test_plain_text_returns_false(self):
        assert _is_svg_content("Hello, world!") is False

    def test_html_not_svg_returns_false(self):
        assert _is_svg_content("<html><body></body></html>") is False

    def test_none_returns_false(self):
        assert _is_svg_content(None) is False

    def test_empty_string_returns_false(self):
        assert _is_svg_content("") is False

    def test_integer_returns_false(self):
        assert _is_svg_content(42) is False

    def test_xml_with_svg_namespace(self):
        assert _is_svg_content('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">') is True


# ---------------------------------------------------------------------------
# _is_data_uri
# ---------------------------------------------------------------------------

class TestIsDataUri:
    def test_valid_png_data_uri(self):
        assert _is_data_uri("data:image/png;base64,iVBORw0KGgo=") is True

    def test_valid_jpeg_data_uri(self):
        assert _is_data_uri("data:image/jpeg;base64,/9j/4AAQSkZJRgAB") is True

    def test_valid_gif_data_uri(self):
        assert _is_data_uri("data:image/gif;base64,R0lGODlh") is True

    def test_valid_webp_data_uri(self):
        assert _is_data_uri("data:image/webp;base64,UklGRg==") is True

    def test_non_image_data_uri_returns_false(self):
        assert _is_data_uri("data:text/plain;base64,SGVsbG8=") is False

    def test_missing_base64_marker_returns_false(self):
        assert _is_data_uri("data:image/png,raw_data") is False

    def test_plain_url_returns_false(self):
        assert _is_data_uri("https://example.com/image.png") is False

    def test_none_returns_false(self):
        assert _is_data_uri(None) is False

    def test_empty_string_returns_false(self):
        assert _is_data_uri("") is False

    def test_integer_returns_false(self):
        assert _is_data_uri(0) is False

    def test_whitespace_padded_valid_uri(self):
        assert _is_data_uri("  data:image/png;base64,abc123  ") is True

    def test_svg_data_uri(self):
        assert _is_data_uri("data:image/svg+xml;base64,PHN2Zz4=") is True


# ---------------------------------------------------------------------------
# _is_url
# ---------------------------------------------------------------------------

class TestIsUrl:
    def test_http_url(self):
        assert _is_url("http://example.com") is True

    def test_https_url(self):
        assert _is_url("https://example.com/path?q=1") is True

    def test_ftp_scheme_returns_false(self):
        assert _is_url("ftp://example.com") is False

    def test_bare_domain_returns_false(self):
        assert _is_url("example.com") is False

    def test_plain_text_returns_false(self):
        assert _is_url("hello world") is False

    def test_none_returns_false(self):
        assert _is_url(None) is False

    def test_empty_string_returns_false(self):
        assert _is_url("") is False

    def test_integer_returns_false(self):
        assert _is_url(99) is False

    def test_whitespace_padded_valid_url(self):
        assert _is_url("  https://example.com  ") is True

    def test_uppercase_scheme_normalised(self):
        assert _is_url("HTTP://example.com") is True

    def test_url_with_port(self):
        assert _is_url("http://localhost:8080/api") is True

    def test_image_url_also_is_url(self):
        assert _is_url("https://cdn.example.com/photo.jpg") is True
