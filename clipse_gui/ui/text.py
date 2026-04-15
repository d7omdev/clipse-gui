"""Text utilities: markup escaping, search highlighting, and content formatting."""

import json

from gi.repository import GLib


def escape_markup(text):
    """Escape special characters for Pango markup."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def highlight_search_term(text, search_term):
    """Highlight search term matches in text using Pango markup."""
    if not search_term or not search_term.strip():
        return escape_markup(text)

    search_lower = search_term.lower()
    text_lower = text.lower()

    result = []
    last_end = 0

    while True:
        idx = text_lower.find(search_lower, last_end)
        if idx == -1:
            break

        # Add text before match
        if idx > last_end:
            result.append(escape_markup(text[last_end:idx]))

        # Add highlighted match with inline background color
        match = text[idx:idx + len(search_term)]
        result.append(f'<span bgcolor="#ffcc00" fgcolor="#000000">{escape_markup(match)}</span>')

        last_end = idx + len(search_term)

    # Add remaining text
    if last_end < len(text):
        result.append(escape_markup(text[last_end:]))

    return "".join(result)


def _format_text_content(text_view):
    """Formats the text content in the TextView, with special handling for JSON."""
    buffer = text_view.get_buffer()
    start, end = buffer.get_bounds()
    text = buffer.get_text(start, end, False)

    if not text.strip():
        return

    formatted_text = None

    # Try to format as JSON first
    try:
        # Remove any leading/trailing whitespace and check if it looks like JSON
        stripped_text = text.strip()
        if (stripped_text.startswith("{") and stripped_text.endswith("}")) or (
            stripped_text.startswith("[") and stripped_text.endswith("]")
        ):
            # Try to parse and format as JSON
            parsed_json = json.loads(stripped_text)
            formatted_text = json.dumps(
                parsed_json, indent=2, ensure_ascii=False, sort_keys=True
            )
    except (json.JSONDecodeError, ValueError):
        # Not valid JSON, try other formatting
        pass

    # If not JSON, try to format as other structured text
    if formatted_text is None:
        # Basic text formatting - normalize whitespace and line breaks
        lines = text.split("\n")
        formatted_lines = []

        for line in lines:
            # Remove excessive whitespace but preserve intentional indentation
            stripped = line.rstrip()
            if stripped:
                # Preserve leading whitespace for indentation
                leading_spaces = len(line) - len(line.lstrip())
                formatted_lines.append(" " * leading_spaces + stripped)
            else:
                formatted_lines.append("")

        # Remove excessive blank lines (more than 2 consecutive)
        result_lines = []
        blank_count = 0
        for line in formatted_lines:
            if line.strip() == "":
                blank_count += 1
                if blank_count <= 2:
                    result_lines.append(line)
            else:
                blank_count = 0
                result_lines.append(line)

        formatted_text = "\n".join(result_lines)

    # Update the buffer with formatted text
    if formatted_text and formatted_text != text:
        buffer.set_text(formatted_text)
        # Show a brief status message
        GLib.timeout_add(100, lambda: _flash_format_status(text_view, "Text formatted"))
    else:
        GLib.timeout_add(
            100, lambda: _flash_format_status(text_view, "No formatting applied")
        )


def _flash_format_status(text_view, message):
    """Shows a brief status message by temporarily changing the tooltip."""
    original_tooltip = text_view.get_tooltip_text()
    text_view.set_tooltip_text(message)

    def restore_tooltip():
        text_view.set_tooltip_text(original_tooltip)
        return False

    GLib.timeout_add(2000, restore_tooltip)
    return False
