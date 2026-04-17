"""Tests for KeyboardMixin dispatch table and handler methods."""

from unittest.mock import MagicMock, patch

import pytest
from gi.repository import Gdk, Gtk

from tests.conftest import make_event


# ════════════════════════════════════════════════════════════════
#  Dispatch routing — verify the right handler fires for each key
# ════════════════════════════════════════════════════════════════


class TestDispatchRouting:
    """Bare keys, ctrl combos, and shift combos reach the correct handler."""

    # ── Navigation ────────────────────────────────────────────

    def test_j_emits_move_cursor_down(self, ctrl):
        ctrl.on_key_press(None, make_event(Gdk.KEY_j))
        ctrl.list_box.emit.assert_called_once_with(
            "move-cursor", Gtk.MovementStep.DISPLAY_LINES, 1
        )

    def test_k_emits_move_cursor_up(self, ctrl):
        ctrl.on_key_press(None, make_event(Gdk.KEY_k))
        ctrl.list_box.emit.assert_called_once_with(
            "move-cursor", Gtk.MovementStep.DISPLAY_LINES, -1
        )

    # ── Selection mode ────────────────────────────────────────

    def test_v_toggles_selection_mode(self, ctrl):
        ctrl.on_key_press(None, make_event(Gdk.KEY_v))
        ctrl.toggle_selection_mode.assert_called_once()

    def test_ctrl_a_selects_all(self, ctrl):
        ctrl.on_key_press(None, make_event(Gdk.KEY_a, ctrl=True))
        ctrl.select_all_items.assert_called_once()

    def test_ctrl_shift_a_deselects_all(self, ctrl):
        ctrl.on_key_press(None, make_event(Gdk.KEY_a, ctrl=True, shift=True))
        ctrl.deselect_all_items.assert_called_once()

    # ── Delete variants ───────────────────────────────────────

    def test_x_removes_item_when_selected(self, ctrl):
        ctrl.list_box.get_selected_row.return_value = MagicMock()
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_x))
        ctrl.remove_selected_item.assert_called_once()
        assert result is True

    def test_x_noop_in_selection_mode(self, ctrl):
        ctrl.list_box.get_selected_row.return_value = MagicMock()
        ctrl.selection_mode = True
        ctrl.on_key_press(None, make_event(Gdk.KEY_x))
        ctrl.remove_selected_item.assert_not_called()

    def test_delete_removes_item_when_selected(self, ctrl):
        ctrl.list_box.get_selected_row.return_value = MagicMock()
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Delete))
        ctrl.remove_selected_item.assert_called_once()
        assert result is True

    def test_ctrl_x_deletes_selected_in_selection_mode(self, ctrl):
        ctrl.selection_mode = True
        ctrl.selected_indices = {0, 2}
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_x, ctrl=True))
        ctrl.delete_selected_items.assert_called_once()
        assert result is True

    def test_ctrl_x_noop_outside_selection_mode(self, ctrl):
        ctrl.selection_mode = False
        ctrl.on_key_press(None, make_event(Gdk.KEY_x, ctrl=True))
        ctrl.delete_selected_items.assert_not_called()

    def test_shift_delete_deletes_selected(self, ctrl):
        ctrl.selection_mode = True
        ctrl.selected_indices = {1}
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Delete, shift=True))
        ctrl.delete_selected_items.assert_called_once()
        assert result is True

    def test_ctrl_shift_delete_clears_all(self, ctrl):
        result = ctrl.on_key_press(
            None, make_event(Gdk.KEY_Delete, ctrl=True, shift=True)
        )
        ctrl.clear_all_items.assert_called_once()
        assert result is True

    def test_ctrl_d_clears_all(self, ctrl):
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_d, ctrl=True))
        ctrl.clear_all_items.assert_called_once()
        assert result is True

    # ── Pin ───────────────────────────────────────────────────

    def test_p_toggles_pin_when_row_selected(self, ctrl):
        ctrl.list_box.get_selected_row.return_value = MagicMock()
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_p))
        ctrl.toggle_pin_selected.assert_called_once()
        assert result is True

    def test_p_noop_when_no_selection(self, ctrl):
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_p))
        ctrl.toggle_pin_selected.assert_not_called()
        assert result is False

    # ── Tab ───────────────────────────────────────────────────

    def test_tab_toggles_pin_filter(self, ctrl):
        ctrl.pin_filter_button.get_active.return_value = True
        ctrl.on_key_press(None, make_event(Gdk.KEY_Tab))
        ctrl.pin_filter_button.set_active.assert_called_once_with(False)
        ctrl.list_box.grab_focus.assert_called_once()

    # ── Help ──────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "keyval,shift",
        [
            (Gdk.KEY_question, False),
            (Gdk.KEY_question, True),
            (Gdk.KEY_slash, True),
        ],
    )
    @patch("clipse_gui.controller_mixins.keyboard_mixin.show_help_window")
    def test_help_keys(self, mock_help, keyval, shift, ctrl):
        result = ctrl.on_key_press(None, make_event(keyval, shift=shift))
        mock_help.assert_called_once()
        assert result is True

    # ── Settings ──────────────────────────────────────────────

    @patch("clipse_gui.controller_mixins.keyboard_mixin.show_settings_window")
    def test_ctrl_comma_opens_settings(self, mock_settings, ctrl):
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_comma, ctrl=True))
        mock_settings.assert_called_once()
        assert result is True

    # ── Quit ──────────────────────────────────────────────────

    def test_ctrl_q_quits(self, ctrl):
        app = MagicMock()
        ctrl.window.get_application.return_value = app
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_q, ctrl=True))
        app.quit.assert_called_once()
        assert result is True

    # ── Zoom ──────────────────────────────────────────────────

    def test_ctrl_plus_zooms_in(self, ctrl):
        ctrl.on_key_press(None, make_event(Gdk.KEY_plus, ctrl=True))
        assert ctrl.zoom_level == pytest.approx(1.1)
        ctrl.update_zoom.assert_called_once()

    def test_ctrl_equal_zooms_in(self, ctrl):
        ctrl.on_key_press(None, make_event(Gdk.KEY_equal, ctrl=True))
        assert ctrl.zoom_level == pytest.approx(1.1)

    def test_ctrl_minus_zooms_out(self, ctrl):
        ctrl.on_key_press(None, make_event(Gdk.KEY_minus, ctrl=True))
        assert ctrl.zoom_level == pytest.approx(1.0 / 1.1)
        ctrl.update_zoom.assert_called_once()

    def test_ctrl_0_resets_zoom(self, ctrl):
        ctrl.zoom_level = 2.5
        ctrl.on_key_press(None, make_event(Gdk.KEY_0, ctrl=True))
        assert ctrl.zoom_level == 1.0
        ctrl.update_zoom.assert_called_once()

    # ── Unbound key → False ───────────────────────────────────

    def test_unbound_key_returns_false(self, ctrl):
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_z))
        assert result is False


# ════════════════════════════════════════════════════════════════
#  Search-focused key handling
# ════════════════════════════════════════════════════════════════


class TestSearchFocused:
    """Keys while the search entry has focus."""

    @pytest.fixture(autouse=True)
    def _focus_search(self, ctrl):
        ctrl.search_entry.has_focus.return_value = True

    # ── Character insertion ───────────────────────────────────

    @pytest.mark.parametrize(
        "keyval,expected_char",
        [
            (Gdk.KEY_v, "v"),
            (Gdk.KEY_x, "x"),
            (Gdk.KEY_p, "p"),
            (Gdk.KEY_j, "j"),
            (Gdk.KEY_k, "k"),
            (Gdk.KEY_f, "f"),
            (Gdk.KEY_slash, "/"),
            (Gdk.KEY_question, "?"),
            (Gdk.KEY_space, " "),
        ],
    )
    def test_bound_keys_insert_char(self, keyval, expected_char, ctrl):
        ctrl.search_entry.get_text.return_value = "abc"
        ctrl.search_entry.get_position.return_value = 2
        result = ctrl.on_key_press(None, make_event(keyval))
        ctrl.search_entry.set_text.assert_called_once_with(f"ab{expected_char}c")
        ctrl.search_entry.set_position.assert_called_once_with(3)
        assert result is True

    def test_char_appended_when_no_get_position(self, ctrl):
        ctrl.search_entry.get_text.return_value = "ab"
        del ctrl.search_entry.get_position  # remove the attribute
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_v))
        ctrl.search_entry.set_text.assert_called_once_with("abv")
        assert result is True

    # ── Blocked keys ──────────────────────────────────────────

    def test_tab_blocked(self, ctrl):
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Tab))
        assert result is True

    def test_return_blocked(self, ctrl):
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Return))
        assert result is True

    # ── Passthrough ───────────────────────────────────────────

    def test_unbound_key_passes_through(self, ctrl):
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_a))
        assert result is False

    # ── Escape in search ──────────────────────────────────────

    def test_escape_exits_selection_mode_first(self, ctrl):
        ctrl.selection_mode = True
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Escape))
        ctrl.toggle_selection_mode.assert_called_once()
        assert result is True

    @patch("clipse_gui.controller_mixins.keyboard_mixin.GLib")
    def test_escape_clears_text_and_unfocuses(self, mock_glib, ctrl):
        ctrl.search_entry.get_text.return_value = "query"
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Escape))
        ctrl.search_entry.set_text.assert_called_once_with("")
        mock_glib.idle_add.assert_called_once()
        assert result is True

    @patch("clipse_gui.controller_mixins.keyboard_mixin.GLib")
    def test_escape_unfocuses_even_when_text_empty(self, mock_glib, ctrl):
        ctrl.search_entry.get_text.return_value = ""
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Escape))
        # Should NOT call set_text (nothing to clear)
        ctrl.search_entry.set_text.assert_not_called()
        mock_glib.idle_add.assert_called_once()
        assert result is True


# ════════════════════════════════════════════════════════════════
#  Navigation from search
# ════════════════════════════════════════════════════════════════


class TestSearchNavigation:
    """Arrow / Page keys while search is focused navigate the list."""

    @pytest.fixture(autouse=True)
    def _focus_search(self, ctrl):
        ctrl.search_entry.has_focus.return_value = True

    def _make_rows(self, ctrl, n=10):
        rows = []
        for i in range(n):
            row = MagicMock()
            alloc = MagicMock()
            alloc.y = i * 40
            row.get_allocation.return_value = alloc
            rows.append(row)
        ctrl.list_box.get_children.return_value = rows
        # vadjustment needs real numbers for min() comparison
        adj = MagicMock()
        adj.get_upper.return_value = n * 40
        adj.get_page_size.return_value = 200
        ctrl.scrolled_window.get_vadjustment.return_value = adj
        return rows

    def test_down_from_no_focus_selects_first(self, ctrl):
        rows = self._make_rows(ctrl)
        ctrl.window.get_focus.return_value = None  # not on any row
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Down))
        ctrl.list_box.select_row.assert_called_once_with(rows[0])
        rows[0].grab_focus.assert_called_once()
        assert result is True

    def test_up_from_no_focus_selects_last(self, ctrl):
        rows = self._make_rows(ctrl, 5)
        ctrl.window.get_focus.return_value = None
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Up))
        ctrl.list_box.select_row.assert_called_once_with(rows[4])
        assert result is True

    def test_down_advances_by_one(self, ctrl):
        rows = self._make_rows(ctrl, 5)
        ctrl.window.get_focus.return_value = rows[1]
        ctrl.on_key_press(None, make_event(Gdk.KEY_Down))
        ctrl.list_box.select_row.assert_called_once_with(rows[2])

    def test_page_down_jumps_by_page_step(self, ctrl):
        rows = self._make_rows(ctrl, 20)
        ctrl.window.get_focus.return_value = rows[2]
        ctrl.on_key_press(None, make_event(Gdk.KEY_Page_Down))
        ctrl.list_box.select_row.assert_called_once_with(rows[7])  # 2 + 5

    def test_page_up_clamps_to_zero(self, ctrl):
        rows = self._make_rows(ctrl, 10)
        ctrl.window.get_focus.return_value = rows[2]
        ctrl.on_key_press(None, make_event(Gdk.KEY_Page_Up))
        ctrl.list_box.select_row.assert_called_once_with(rows[0])  # max(2-5, 0)

    def test_empty_list_returns_false(self, ctrl):
        ctrl.list_box.get_children.return_value = []
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Down))
        assert result is False

    def test_down_past_end_returns_false(self, ctrl):
        rows = self._make_rows(ctrl, 3)
        ctrl.window.get_focus.return_value = rows[2]  # last row
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Down))
        # target = 3, last = 2 → out of range
        assert result is False


# ════════════════════════════════════════════════════════════════
#  Return key handler
# ════════════════════════════════════════════════════════════════


class TestReturnKey:

    def test_return_activates_selected_row(self, ctrl):
        selected = MagicMock()
        ctrl.list_box.get_selected_row.return_value = selected
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Return))
        ctrl.copy_selected_item_to_clipboard.assert_called_once_with(False)
        assert result is True

    @patch(
        "clipse_gui.controller_mixins.keyboard_mixin.ENTER_TO_PASTE", new=False
    )
    def test_shift_return_pastes_when_enter_to_paste_off(self, ctrl):
        selected = MagicMock()
        ctrl.list_box.get_selected_row.return_value = selected
        ctrl.on_key_press(None, make_event(Gdk.KEY_Return, shift=True))
        # not ENTER_TO_PASTE → True → with_paste_simulation=True
        ctrl.copy_selected_item_to_clipboard.assert_called_once_with(True)

    @patch(
        "clipse_gui.controller_mixins.keyboard_mixin.ENTER_TO_PASTE", new=True
    )
    def test_shift_return_no_paste_when_enter_to_paste_on(self, ctrl):
        selected = MagicMock()
        ctrl.list_box.get_selected_row.return_value = selected
        ctrl.on_key_press(None, make_event(Gdk.KEY_Return, shift=True))
        # not ENTER_TO_PASTE → False
        ctrl.copy_selected_item_to_clipboard.assert_called_once_with(False)

    def test_return_selects_first_row_when_none_selected(self, ctrl):
        first = MagicMock()
        ctrl.list_box.get_selected_row.return_value = None
        ctrl.list_box.get_children.return_value = [first]
        ctrl.list_box.get_row_at_index.return_value = first
        ctrl.on_key_press(None, make_event(Gdk.KEY_Return))
        ctrl.list_box.select_row.assert_called_once_with(first)
        first.grab_focus.assert_called_once()

    def test_return_focuses_search_when_list_empty(self, ctrl):
        ctrl.list_box.get_selected_row.return_value = None
        ctrl.list_box.get_children.return_value = []
        ctrl.on_key_press(None, make_event(Gdk.KEY_Return))
        ctrl.search_entry.grab_focus.assert_called_once()


# ════════════════════════════════════════════════════════════════
#  Space key handler
# ════════════════════════════════════════════════════════════════


class TestSpaceKey:

    def test_space_toggles_item_in_selection_mode(self, ctrl):
        ctrl.selection_mode = True
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_space))
        ctrl.toggle_item_selection.assert_called_once()
        assert result is True

    def test_space_shows_preview_when_row_selected(self, ctrl):
        ctrl.list_box.get_selected_row.return_value = MagicMock(is_url=False)
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_space))
        ctrl.show_item_preview.assert_called_once()
        assert result is True

    @patch(
        "clipse_gui.controller_mixins.keyboard_mixin.OPEN_LINKS_WITH_BROWSER",
        new=True,
    )
    def test_space_opens_url_when_url_row(self, ctrl):
        row = MagicMock(is_url=True, website_url="https://example.com")
        ctrl.list_box.get_selected_row.return_value = row
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_space))
        ctrl.open_url_with_gtk.assert_called_once_with("https://example.com")
        assert result is True

    def test_space_noop_when_nothing_selected(self, ctrl):
        ctrl.list_box.get_selected_row.return_value = None
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_space))
        assert result is False


# ════════════════════════════════════════════════════════════════
#  Escape handler (main, not search)
# ════════════════════════════════════════════════════════════════


class TestEscapeKey:

    def test_escape_exits_selection_mode_first(self, ctrl):
        ctrl.selection_mode = True
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Escape))
        ctrl.toggle_selection_mode.assert_called_once()
        assert result is True

    def test_escape_clears_search_text_second(self, ctrl):
        ctrl.search_entry.get_text.return_value = "query"
        result = ctrl.on_key_press(None, make_event(Gdk.KEY_Escape))
        ctrl.search_entry.set_text.assert_called_once_with("")
        ctrl.list_box.grab_focus.assert_called_once()
        assert result is True

    def test_escape_quits_when_no_text_no_selection(self, ctrl):
        app = MagicMock()
        app.tray_manager = None
        ctrl.window.get_application.return_value = app
        ctrl.on_key_press(None, make_event(Gdk.KEY_Escape))
        app.quit.assert_called_once()

    def test_escape_minimizes_to_tray_when_enabled(self, ctrl):
        app = MagicMock()
        app.tray_manager = MagicMock()
        app.tray_manager.minimize_to_tray.return_value = True
        ctrl.window.get_application.return_value = app
        # _handle_escape does `from .. import constants` which resolves to
        # clipse_gui.constants already in sys.modules — patch it there.
        import clipse_gui.constants as real_const

        orig = getattr(real_const, "MINIMIZE_TO_TRAY", False)
        real_const.MINIMIZE_TO_TRAY = True
        try:
            result = ctrl.on_key_press(None, make_event(Gdk.KEY_Escape))
        finally:
            real_const.MINIMIZE_TO_TRAY = orig
        app.tray_manager.minimize_to_tray.assert_called_once()
        assert result is True


# ════════════════════════════════════════════════════════════════
#  Focus search (/ and f)
# ════════════════════════════════════════════════════════════════


class TestFocusSearch:

    @pytest.mark.parametrize("keyval", [Gdk.KEY_slash, Gdk.KEY_f])
    @patch("clipse_gui.controller_mixins.keyboard_mixin.GLib")
    def test_slash_and_f_show_search(self, mock_glib, keyval, ctrl):
        result = ctrl.on_key_press(None, make_event(keyval))
        ctrl.search_entry.set_no_show_all.assert_called_once_with(False)
        ctrl.search_entry.show.assert_called_once()
        mock_glib.idle_add.assert_called_once()
        assert result is True


# ════════════════════════════════════════════════════════════════
#  Public callbacks
# ════════════════════════════════════════════════════════════════


class TestPublicCallbacks:

    def test_on_row_single_click_selects_and_copies(self, ctrl):
        row = MagicMock()
        ctrl._on_row_single_click(row)
        ctrl.list_box.select_row.assert_called_once_with(row)
        ctrl.copy_selected_item_to_clipboard.assert_called_once_with(
            with_paste_simulation=True
        )
