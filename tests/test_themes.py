"""Tests for theme discovery and CSS loading in clipse_gui.constants."""

import pytest

from clipse_gui import constants


@pytest.fixture
def theme_dirs(tmp_path, monkeypatch):
    builtin = tmp_path / "builtin"
    user = tmp_path / "user"
    builtin.mkdir()
    monkeypatch.setattr(constants, "BUILTIN_THEMES_DIR", str(builtin))
    monkeypatch.setattr(constants, "USER_THEMES_DIR", str(user))
    monkeypatch.setattr(constants, "USER_CSS_PATH", str(tmp_path / "custom.css"))
    return builtin, user


class TestListThemes:
    def test_merges_and_dedups_both_dirs(self, theme_dirs):
        builtin, user = theme_dirs
        user.mkdir()
        (builtin / "nord.css").write_text("")
        (builtin / "dracula.css").write_text("")
        (user / "nord.css").write_text("")
        (user / "mine.css").write_text("")
        (user / "notes.txt").write_text("")
        assert constants.list_themes() == ["dracula", "mine", "nord"]

    def test_tolerates_missing_user_dir(self, theme_dirs):
        builtin, user = theme_dirs
        (builtin / "nord.css").write_text("")
        assert not user.exists()
        assert constants.list_themes() == ["nord"]


class TestLoadThemeCss:
    def test_user_file_wins_over_builtin(self, theme_dirs):
        builtin, user = theme_dirs
        user.mkdir()
        (builtin / "nord.css").write_text("builtin")
        (user / "nord.css").write_text("user")
        assert constants.load_theme_css("nord") == "user"

    def test_falls_back_to_builtin(self, theme_dirs):
        builtin, _ = theme_dirs
        (builtin / "nord.css").write_text("builtin")
        assert constants.load_theme_css("nord") == "builtin"

    def test_unknown_name_returns_empty(self, theme_dirs):
        assert constants.load_theme_css("missing") == ""

    def test_empty_name_returns_empty(self, theme_dirs):
        assert constants.load_theme_css("") == ""


class TestLoadUserCss:
    def test_missing_file_returns_empty(self, theme_dirs):
        assert constants.load_user_css() == ""

    def test_reads_file(self, theme_dirs, tmp_path):
        (tmp_path / "custom.css").write_text("* { color: red; }")
        assert constants.load_user_css() == "* { color: red; }"
