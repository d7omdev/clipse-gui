"""Tests for clipse_gui.cli — argument parsing, logging setup, and ColorFormatter.

main() is intentionally excluded: it launches GTK and calls sys.exit().
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from unittest.mock import patch

import pytest

# cli.py calls gi.require_version at module level; conftest.py has already
# issued those calls, so importing cli here is safe.
from clipse_gui.cli import ColorFormatter, parse_args_from_sys_argv, setup_logging


# ---------------------------------------------------------------------------
# parse_args_from_sys_argv()
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_no_args_returns_debug_false(self):
        with patch.object(sys, "argv", ["clipse-gui"]):
            args, _ = parse_args_from_sys_argv()
        assert args.debug is False

    @pytest.mark.parametrize("flag", ["--debug", "-d"])
    def test_debug_flag_sets_debug_true(self, flag: str):
        with patch.object(sys, "argv", ["clipse-gui", flag]):
            args, _ = parse_args_from_sys_argv()
        assert args.debug is True

    def test_unknown_args_passed_through_in_second_element(self):
        with patch.object(sys, "argv", ["clipse-gui", "--display=:0", "--some-gtk-arg"]):
            args, remainder = parse_args_from_sys_argv()
        assert "--display=:0" in remainder
        assert "--some-gtk-arg" in remainder

    def test_known_args_not_in_remainder(self):
        with patch.object(sys, "argv", ["clipse-gui", "--debug", "--extra"]):
            args, remainder = parse_args_from_sys_argv()
        assert "--debug" not in remainder
        assert "-d" not in remainder

    def test_returns_namespace_and_list(self):
        with patch.object(sys, "argv", ["clipse-gui"]):
            result = parse_args_from_sys_argv()
        namespace, remainder = result
        assert hasattr(namespace, "debug")
        assert isinstance(remainder, list)

    def test_version_flag_exits(self):
        with patch.object(sys, "argv", ["clipse-gui", "--version"]):
            with pytest.raises(SystemExit):
                parse_args_from_sys_argv()


# ---------------------------------------------------------------------------
# setup_logging()
#
# Strategy: patch logging.basicConfig to intercept the handlers list it
# receives. This avoids fighting pytest's own LogCaptureHandler (which
# pre-exists on the root logger and would make basicConfig a no-op).
# ---------------------------------------------------------------------------


def _capture_basicconfig(tmp_path, debug: bool) -> list[logging.Handler]:
    """Call setup_logging and return the handlers list passed to basicConfig."""
    captured: list[logging.Handler] = []

    def fake_basicconfig(**kwargs):
        captured.extend(kwargs.get("handlers", []))

    with patch("clipse_gui.cli.constants.CONFIG_DIR", str(tmp_path)), \
         patch("logging.basicConfig", side_effect=fake_basicconfig):
        setup_logging(debug=debug)

    return captured


class TestSetupLogging:
    def test_default_mode_sends_one_stream_handler(self, tmp_path):
        handlers = _capture_basicconfig(tmp_path, debug=False)
        stream = [h for h in handlers if type(h).__name__ == "StreamHandler"]
        assert len(stream) == 1

    def test_default_mode_stream_handler_level_is_info(self, tmp_path):
        handlers = _capture_basicconfig(tmp_path, debug=False)
        stream = [h for h in handlers if type(h).__name__ == "StreamHandler"]
        assert stream[0].level == logging.INFO

    def test_debug_mode_stream_handler_level_is_debug(self, tmp_path):
        handlers = _capture_basicconfig(tmp_path, debug=True)
        stream = [h for h in handlers if type(h).__name__ == "StreamHandler"]
        assert stream[0].level == logging.DEBUG

    def test_no_file_handler_in_default_mode(self, tmp_path):
        handlers = _capture_basicconfig(tmp_path, debug=False)
        file_handlers = [h for h in handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 0

    def test_file_handler_created_in_debug_mode(self, tmp_path):
        handlers = _capture_basicconfig(tmp_path, debug=True)
        file_handlers = [h for h in handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1

    def test_file_handler_path_uses_config_dir(self, tmp_path):
        handlers = _capture_basicconfig(tmp_path, debug=True)
        file_handlers = [h for h in handlers if isinstance(h, RotatingFileHandler)]
        assert str(tmp_path) in file_handlers[0].baseFilename

    def test_file_handler_level_is_debug(self, tmp_path):
        handlers = _capture_basicconfig(tmp_path, debug=True)
        file_handlers = [h for h in handlers if isinstance(h, RotatingFileHandler)]
        assert file_handlers[0].level == logging.DEBUG

    def test_stream_handler_formatter_is_color_formatter(self, tmp_path):
        handlers = _capture_basicconfig(tmp_path, debug=False)
        stream = [h for h in handlers if type(h).__name__ == "StreamHandler"]
        assert isinstance(stream[0].formatter, ColorFormatter)

    def test_file_handler_uses_plain_formatter(self, tmp_path):
        handlers = _capture_basicconfig(tmp_path, debug=True)
        file_handlers = [h for h in handlers if isinstance(h, RotatingFileHandler)]
        assert not isinstance(file_handlers[0].formatter, ColorFormatter)

    def test_sets_module_level_log_variable(self, tmp_path):
        import clipse_gui.cli as cli_module

        with patch("clipse_gui.cli.constants.CONFIG_DIR", str(tmp_path)), \
             patch("logging.basicConfig"):
            setup_logging(debug=False)

        assert cli_module.log is not None
        assert isinstance(cli_module.log, logging.Logger)

    def test_basicconfig_receives_debug_root_level(self, tmp_path):
        """Root logger level passed to basicConfig must always be DEBUG so
        individual handler levels govern what actually appears."""
        received_level: list[int] = []

        def fake_basicconfig(**kwargs):
            received_level.append(kwargs.get("level", -1))

        with patch("clipse_gui.cli.constants.CONFIG_DIR", str(tmp_path)), \
             patch("logging.basicConfig", side_effect=fake_basicconfig):
            setup_logging(debug=False)

        assert received_level == [logging.DEBUG]


# ---------------------------------------------------------------------------
# ColorFormatter
# ---------------------------------------------------------------------------


class TestColorFormatter:
    """ColorFormatter must inject ANSI color codes into log records."""

    _FMT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def _make_record(self, level: int, message: str = "test") -> logging.LogRecord:
        return logging.LogRecord(
            name="test.logger",
            level=level,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )

    def _formatter(self) -> ColorFormatter:
        return ColorFormatter(self._FMT, datefmt="%Y-%m-%d %H:%M:%S")

    @pytest.mark.parametrize("level,color_fragment", [
        (logging.DEBUG, "\033[1;36m"),
        (logging.INFO, "\033[1;32m"),
        (logging.WARNING, "\033[1;33m"),
        (logging.ERROR, "\033[1;31m"),
        (logging.CRITICAL, "\033[1;41m"),
    ])
    def test_injects_ansi_color_for_each_level(self, level: int, color_fragment: str):
        formatter = self._formatter()
        record = self._make_record(level)
        formatted = formatter.format(record)
        assert color_fragment in formatted

    def test_reset_code_present_in_output(self):
        formatter = self._formatter()
        record = self._make_record(logging.INFO)
        formatted = formatter.format(record)
        assert "\033[0m" in formatted

    def test_levelname_is_colorized_after_format(self):
        formatter = self._formatter()
        record = self._make_record(logging.WARNING)
        formatter.format(record)
        # format() mutates record.levelname in-place to include ANSI prefix
        assert "\033[" in record.levelname

    def test_name_is_colorized_after_format(self):
        formatter = self._formatter()
        record = self._make_record(logging.INFO, "hello")
        formatter.format(record)
        assert "\033[1;34m" in record.name

    def test_message_content_preserved(self):
        formatter = self._formatter()
        record = self._make_record(logging.INFO, "important message")
        formatted = formatter.format(record)
        assert "important message" in formatted

    def test_unknown_level_does_not_raise(self):
        formatter = self._formatter()
        record = self._make_record(logging.INFO)
        record.levelname = "CUSTOM"
        # Should not raise; missing key returns empty string via dict.get
        formatted = formatter.format(record)
        assert "CUSTOM" in formatted
