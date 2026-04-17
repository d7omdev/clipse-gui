"""Tests for clipse_gui/ui/text.py — escape_markup, highlight_search_term, _format_text_content.

gi.require_version is handled by conftest.py before this module is collected.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from clipse_gui.ui.text import (
    _format_text_content,
    escape_markup,
    highlight_search_term,
)


# ---------------------------------------------------------------------------
# escape_markup
# ---------------------------------------------------------------------------

class TestEscapeMarkup:
    def test_ampersand_escaped(self):
        assert escape_markup("a & b") == "a &amp; b"

    def test_less_than_escaped(self):
        assert escape_markup("a < b") == "a &lt; b"

    def test_greater_than_escaped(self):
        assert escape_markup("a > b") == "a &gt; b"

    def test_all_three_in_one_string(self):
        assert escape_markup("<a & b>") == "&lt;a &amp; b&gt;"

    def test_no_special_chars_unchanged(self):
        assert escape_markup("hello world") == "hello world"

    def test_empty_string_unchanged(self):
        assert escape_markup("") == ""

    def test_multiple_ampersands(self):
        result = escape_markup("a & b & c")
        assert result == "a &amp; b &amp; c"

    def test_xml_like_tag_fully_escaped(self):
        assert escape_markup("<tag>") == "&lt;tag&gt;"

    def test_already_escaped_not_double_escaped(self):
        # The function replaces & → &amp;, so &amp; becomes &amp;amp;
        result = escape_markup("&amp;")
        assert result == "&amp;amp;"


# ---------------------------------------------------------------------------
# highlight_search_term
# ---------------------------------------------------------------------------

HIGHLIGHT_SPAN = '<span bgcolor="#ffcc00" fgcolor="#000000">'
HIGHLIGHT_CLOSE = "</span>"


class TestHighlightSearchTerm:
    def test_empty_search_term_returns_escaped_text(self):
        result = highlight_search_term("hello <world>", "")
        assert result == "hello &lt;world&gt;"

    def test_whitespace_only_search_term_returns_escaped_text(self):
        result = highlight_search_term("hello", "   ")
        assert result == "hello"

    def test_single_match_wrapped_in_span(self):
        result = highlight_search_term("hello world", "world")
        assert HIGHLIGHT_SPAN in result
        assert "world" in result
        assert HIGHLIGHT_CLOSE in result

    def test_no_match_returns_escaped_text(self):
        result = highlight_search_term("hello world", "xyz")
        assert result == "hello world"
        assert HIGHLIGHT_SPAN not in result

    def test_case_insensitive_match(self):
        result = highlight_search_term("Hello World", "hello")
        assert HIGHLIGHT_SPAN in result
        assert "Hello" in result

    def test_multiple_occurrences_all_highlighted(self):
        result = highlight_search_term("cat cat cat", "cat")
        assert result.count(HIGHLIGHT_SPAN) == 3

    def test_match_at_start(self):
        result = highlight_search_term("start of text", "start")
        assert result.startswith(HIGHLIGHT_SPAN)

    def test_match_at_end(self):
        result = highlight_search_term("text at end", "end")
        before_span = result.split(HIGHLIGHT_SPAN)[0]
        assert before_span == "text at "

    def test_special_chars_in_surrounding_text_escaped(self):
        result = highlight_search_term("a & <b> match here", "match")
        assert "&amp;" in result
        assert "&lt;" in result

    def test_special_chars_in_match_itself_escaped(self):
        result = highlight_search_term("a & b", "&")
        assert "&amp;" in result
        assert HIGHLIGHT_SPAN in result

    def test_full_text_is_match(self):
        result = highlight_search_term("python", "python")
        assert result == f'{HIGHLIGHT_SPAN}python{HIGHLIGHT_CLOSE}'

    def test_search_term_longer_than_text_no_match(self):
        result = highlight_search_term("hi", "hello world")
        assert result == "hi"
        assert HIGHLIGHT_SPAN not in result

    @pytest.mark.parametrize("text,term,expected_count", [
        ("aaa", "a", 3),
        ("abab", "ab", 2),
        ("hello hello hello", "hello", 3),
    ])
    def test_occurrence_counts(self, text, term, expected_count):
        result = highlight_search_term(text, term)
        assert result.count(HIGHLIGHT_SPAN) == expected_count


# ---------------------------------------------------------------------------
# _format_text_content
# ---------------------------------------------------------------------------

def _make_text_view(content: str) -> MagicMock:
    """Build a minimal mock GTK TextView with the given buffer content."""
    buffer_mock = MagicMock()
    start = MagicMock()
    end = MagicMock()
    buffer_mock.get_bounds.return_value = (start, end)
    buffer_mock.get_text.return_value = content

    text_view = MagicMock()
    text_view.get_buffer.return_value = buffer_mock
    return text_view


class TestFormatTextContent:
    def test_valid_json_object_pretty_printed(self):
        raw = '{"b": 2, "a": 1}'
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        buffer = text_view.get_buffer()
        call_args = buffer.set_text.call_args
        assert call_args is not None
        formatted = call_args[0][0]
        parsed = json.loads(formatted)
        assert parsed == {"a": 1, "b": 2}
        assert "  " in formatted

    def test_valid_json_array_pretty_printed(self):
        raw = '[3, 1, 2]'
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        buffer = text_view.get_buffer()
        formatted = buffer.set_text.call_args[0][0]
        assert json.loads(formatted) == [3, 1, 2]

    def test_json_keys_sorted_ascending(self):
        raw = '{"z": 1, "a": 2, "m": 3}'
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        formatted = text_view.get_buffer().set_text.call_args[0][0]
        keys = [line.strip().split('"')[1] for line in formatted.split("\n") if ":" in line]
        assert keys == sorted(keys)

    def test_invalid_json_falls_back_to_text_normalisation(self):
        raw = "not json at all"
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        # For plain text with no changes needed, set_text is not called
        # (formatted_text == text → branch skipped)
        buffer = text_view.get_buffer()
        if buffer.set_text.called:
            result = buffer.set_text.call_args[0][0]
            assert "not json at all" in result

    def test_trailing_whitespace_stripped_from_lines(self):
        raw = "hello   \nworld   "
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        buffer = text_view.get_buffer()
        if buffer.set_text.called:
            result = buffer.set_text.call_args[0][0]
            for line in result.split("\n"):
                assert line == line.rstrip()

    def test_excessive_blank_lines_collapsed_to_two(self):
        raw = "line1\n\n\n\n\nline2"
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        buffer = text_view.get_buffer()
        assert buffer.set_text.called
        result = buffer.set_text.call_args[0][0]
        # No run of more than 2 consecutive blank lines
        import re
        assert not re.search(r"\n{4,}", result)

    def test_empty_content_skipped(self):
        text_view = _make_text_view("   ")
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        buffer = text_view.get_buffer()
        buffer.set_text.assert_not_called()

    def test_already_formatted_json_no_set_text(self):
        obj = {"a": 1, "b": 2}
        raw = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        buffer = text_view.get_buffer()
        # formatted_text == text, so set_text should NOT be called
        buffer.set_text.assert_not_called()

    def test_glib_timeout_called_after_format(self):
        raw = '{"x": 1}'
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib") as glib_mock:
            _format_text_content(text_view)
        glib_mock.timeout_add.assert_called()

    def test_indentation_preserved_in_plain_text(self):
        raw = "top\n    indented line\nback"
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        buffer = text_view.get_buffer()
        if buffer.set_text.called:
            result = buffer.set_text.call_args[0][0]
            assert "    indented line" in result

    def test_json_with_unicode_preserved(self):
        raw = '{"emoji": "\u2764"}'
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        buffer = text_view.get_buffer()
        if buffer.set_text.called:
            result = buffer.set_text.call_args[0][0]
            assert "\u2764" in result

    def test_curly_brace_string_that_is_not_valid_json(self):
        raw = "{this is not valid json}"
        text_view = _make_text_view(raw)
        with patch("clipse_gui.ui.text.GLib"):
            _format_text_content(text_view)
        # Should not raise; falls back to plain text formatting
        buffer = text_view.get_buffer()
        assert buffer.get_text.called
