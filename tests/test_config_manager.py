"""Tests for clipse_gui.config_manager.ConfigManager."""

import configparser
import os

import pytest

from clipse_gui.config_manager import ConfigManager


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

DEFAULTS: dict = {
    "general": {
        "max_items": "200",
        "font_size": "1.0",
        "dark_mode": "true",
        "theme": "default",
    },
    "behaviour": {
        "hover_to_select": "false",
        "compact_mode": "off",
    },
}


def make_manager(tmp_path, filename: str = "config.ini", defaults: dict | None = None) -> ConfigManager:
    """Return a ConfigManager pointing at a path inside *tmp_path*."""
    path = str(tmp_path / filename)
    return ConfigManager(config_path=path, default_settings=defaults if defaults is not None else DEFAULTS)


def write_ini(path: str, content: str) -> None:
    """Write raw INI text to *path*, creating parent dirs as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


# ---------------------------------------------------------------------------
# File creation / loading
# ---------------------------------------------------------------------------


class TestFileCreation:
    def test_creates_file_when_missing(self, tmp_path):
        cm = make_manager(tmp_path)
        assert os.path.exists(cm.config_path)

    def test_created_file_contains_header_comment(self, tmp_path):
        cm = make_manager(tmp_path)
        text = open(cm.config_path).read()
        assert "# Clipse GUI Configuration File" in text

    def test_created_file_contains_default_values(self, tmp_path):
        cm = make_manager(tmp_path)
        text = open(cm.config_path).read()
        assert "max_items" in text
        assert "200" in text

    def test_no_load_error_when_created_fresh(self, tmp_path):
        cm = make_manager(tmp_path)
        assert cm.load_error_message is None


class TestLoadingExistingConfig:
    def test_user_value_overrides_default(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(
            path,
            "[general]\nmax_items = 99\nfont_size = 1.0\ndark_mode = true\ntheme = default\n"
            "[behaviour]\nhover_to_select = false\ncompact_mode = off\n",
        )
        cm = ConfigManager(config_path=path, default_settings=DEFAULTS)
        assert cm.getint("general", "max_items") == 99

    def test_missing_key_falls_back_to_default(self, tmp_path):
        path = str(tmp_path / "config.ini")
        # Only 'theme' present; 'max_items' absent
        write_ini(path, "[general]\ntheme = custom\n")
        cm = ConfigManager(config_path=path, default_settings=DEFAULTS)
        assert cm.getint("general", "max_items") == 200

    def test_no_load_error_on_valid_file(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(
            path,
            "[general]\nmax_items = 50\nfont_size = 1.2\ndark_mode = false\ntheme = light\n"
            "[behaviour]\nhover_to_select = true\ncompact_mode = on\n",
        )
        cm = ConfigManager(config_path=path, default_settings=DEFAULTS)
        assert cm.load_error_message is None

    def test_extra_user_section_is_preserved(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(path, "[custom]\nmy_key = hello\n")
        cm = ConfigManager(config_path=path, default_settings=DEFAULTS)
        assert cm.get("custom", "my_key") == "hello"


class TestCorruptConfig:
    def test_sets_load_error_message_on_parse_error(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(path, "this is not valid ini %%% [[[")
        cm = ConfigManager(config_path=path, default_settings=DEFAULTS)
        assert cm.load_error_message is not None

    def test_still_uses_defaults_after_parse_error(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(path, "%%% totally broken")
        cm = ConfigManager(config_path=path, default_settings=DEFAULTS)
        assert cm.getint("general", "max_items") == 200


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


class TestGet:
    def test_returns_value_from_config(self, tmp_path):
        cm = make_manager(tmp_path)
        assert cm.get("general", "theme") == "default"

    def test_returns_fallback_for_missing_section(self, tmp_path):
        cm = make_manager(tmp_path)
        assert cm.get("nonexistent", "key", fallback="fb") == "fb"

    def test_returns_empty_string_fallback_by_default(self, tmp_path):
        cm = make_manager(tmp_path)
        assert cm.get("nonexistent", "key") == ""

    def test_returns_fallback_for_missing_key_in_existing_section(self, tmp_path):
        cm = make_manager(tmp_path)
        assert cm.get("general", "no_such_key", fallback="x") == "x"


# ---------------------------------------------------------------------------
# getint()
# ---------------------------------------------------------------------------


class TestGetInt:
    def test_returns_int_for_valid_value(self, tmp_path):
        cm = make_manager(tmp_path)
        result = cm.getint("general", "max_items")
        assert result == 200
        assert isinstance(result, int)

    def test_returns_fallback_for_missing_section(self, tmp_path):
        cm = make_manager(tmp_path)
        assert cm.getint("ghost", "key", fallback=7) == 7

    def test_falls_back_to_defaults_dict_on_invalid_value(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(path, "[general]\nmax_items = abc\nfont_size = 1.0\ndark_mode = true\ntheme = default\n")
        cm = ConfigManager(config_path=path, default_settings=DEFAULTS)
        # Defaults dict says 200; that should be returned
        assert cm.getint("general", "max_items") == 200

    def test_falls_back_to_fallback_param_when_no_default(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(path, "[general]\nmax_items = abc\nfont_size = 1.0\ndark_mode = true\ntheme = default\n")
        defaults_no_max = {
            "general": {"font_size": "1.0", "dark_mode": "true", "theme": "default"},
            "behaviour": DEFAULTS["behaviour"],
        }
        cm = ConfigManager(config_path=path, default_settings=defaults_no_max)
        assert cm.getint("general", "max_items", fallback=42) == 42


# ---------------------------------------------------------------------------
# getfloat()
# ---------------------------------------------------------------------------


class TestGetFloat:
    def test_returns_float_for_valid_value(self, tmp_path):
        cm = make_manager(tmp_path)
        result = cm.getfloat("general", "font_size")
        assert result == pytest.approx(1.0)
        assert isinstance(result, float)

    def test_returns_fallback_for_missing_section(self, tmp_path):
        cm = make_manager(tmp_path)
        assert cm.getfloat("ghost", "key", fallback=3.14) == pytest.approx(3.14)

    def test_falls_back_to_defaults_dict_on_invalid_value(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(path, "[general]\nmax_items = 200\nfont_size = not_a_float\ndark_mode = true\ntheme = default\n")
        cm = ConfigManager(config_path=path, default_settings=DEFAULTS)
        assert cm.getfloat("general", "font_size") == pytest.approx(1.0)

    def test_falls_back_to_fallback_param_when_no_default(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(path, "[general]\nmax_items = 200\nfont_size = bad\ndark_mode = true\ntheme = default\n")
        defaults_no_font = {
            "general": {"max_items": "200", "dark_mode": "true", "theme": "default"},
            "behaviour": DEFAULTS["behaviour"],
        }
        cm = ConfigManager(config_path=path, default_settings=defaults_no_font)
        assert cm.getfloat("general", "font_size", fallback=9.9) == pytest.approx(9.9)


# ---------------------------------------------------------------------------
# getboolean()
# ---------------------------------------------------------------------------


class TestGetBoolean:
    @pytest.mark.parametrize("raw,expected", [
        ("true", True),
        ("True", True),
        ("yes", True),
        ("on", True),
        ("1", True),
        ("false", False),
        ("False", False),
        ("no", False),
        ("off", False),
        ("0", False),
    ])
    def test_parses_boolean_strings(self, tmp_path, raw: str, expected: bool):
        path = str(tmp_path / "config.ini")
        write_ini(
            path,
            f"[general]\nmax_items = 200\nfont_size = 1.0\ndark_mode = {raw}\ntheme = default\n"
            "[behaviour]\nhover_to_select = false\ncompact_mode = off\n",
        )
        cm = ConfigManager(config_path=path, default_settings=DEFAULTS)
        assert cm.getboolean("general", "dark_mode") is expected

    def test_returns_bool_type(self, tmp_path):
        cm = make_manager(tmp_path)
        result = cm.getboolean("general", "dark_mode")
        assert isinstance(result, bool)

    def test_returns_fallback_for_missing_section(self, tmp_path):
        cm = make_manager(tmp_path)
        assert cm.getboolean("ghost", "key", fallback=True) is True

    def test_falls_back_to_defaults_dict_on_invalid_value(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(
            path,
            "[general]\nmax_items = 200\nfont_size = 1.0\ndark_mode = maybe\ntheme = default\n",
        )
        cm = ConfigManager(config_path=path, default_settings=DEFAULTS)
        # Defaults dict says "true", so should return True
        assert cm.getboolean("general", "dark_mode") is True

    def test_falls_back_to_fallback_param_when_no_default(self, tmp_path):
        path = str(tmp_path / "config.ini")
        write_ini(path, "[general]\nmax_items = 200\nfont_size = 1.0\ndark_mode = maybe\ntheme = default\n")
        defaults_no_dark = {
            "general": {"max_items": "200", "font_size": "1.0", "theme": "default"},
            "behaviour": DEFAULTS["behaviour"],
        }
        cm = ConfigManager(config_path=path, default_settings=defaults_no_dark)
        assert cm.getboolean("general", "dark_mode", fallback=False) is False

    def test_default_bool_value_in_defaults_dict(self, tmp_path):
        """Defaults dict may store native Python bools, not just strings."""
        defaults_with_bool = {
            "general": {
                "max_items": "200",
                "font_size": "1.0",
                "dark_mode": True,  # native bool
                "theme": "default",
            },
            "behaviour": DEFAULTS["behaviour"],
        }
        path = str(tmp_path / "config.ini")
        write_ini(path, "[general]\nmax_items = 200\nfont_size = 1.0\ndark_mode = invalid\ntheme = default\n")
        cm = ConfigManager(config_path=path, default_settings=defaults_with_bool)
        assert cm.getboolean("general", "dark_mode") is True


# ---------------------------------------------------------------------------
# Save / directory creation
# ---------------------------------------------------------------------------


class TestSave:
    def test_creates_parent_directories_on_first_save(self, tmp_path):
        nested_path = str(tmp_path / "a" / "b" / "c" / "config.ini")
        ConfigManager(config_path=nested_path, default_settings=DEFAULTS)
        assert os.path.exists(nested_path)

    def test_saved_file_is_valid_ini(self, tmp_path):
        cm = make_manager(tmp_path)
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(cm.config_path, encoding="utf-8")
        # All default sections must be present
        for section in DEFAULTS:
            assert parser.has_section(section)

    def test_saved_file_roundtrips_values(self, tmp_path):
        cm = make_manager(tmp_path)
        # Re-read the saved file with a brand-new manager
        cm2 = ConfigManager(config_path=cm.config_path, default_settings=DEFAULTS)
        assert cm2.get("general", "theme") == "default"
        assert cm2.getint("general", "max_items") == 200
