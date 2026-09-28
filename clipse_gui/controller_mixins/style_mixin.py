"""CSS, theming, zoom, compact mode, and hover-to-select styling."""

import logging

from gi.repository import Gdk, GLib, Gtk

from ..constants import (
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    get_app_css,
    load_theme_css,
    load_user_css,
)

log = logging.getLogger(__name__)


class StyleMixin:

    def _apply_css(self):
        """Applies the application-wide CSS including current zoom level."""
        screen = Gdk.Screen.get_default()
        if not screen:
            log.error("Cannot get default GdkScreen to apply CSS")
            return

        zoom_css = f"* {{ font-size: {round(self.zoom_level * 100)}%; }}".encode()
        try:
            if not hasattr(self, "style_provider"):
                log.debug("Creating and adding application CSS provider.")
                self.style_provider = Gtk.CssProvider()
                Gtk.StyleContext.add_provider_for_screen(
                    screen,
                    self.style_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )
            self.style_provider.load_from_data(
                self._get_current_css().encode() + b"\n" + zoom_css
            )
        except GLib.Error as e:
            log.error(f"Failed to load CSS: {e}")
        except Exception as e:
            log.error(f"Unexpected error applying CSS: {e}")

    def _get_current_css(self):
        """Get current CSS with applied style settings."""
        import clipse_gui.constants as constants
        css = get_app_css(
            border_radius=constants.BORDER_RADIUS,
            accent_color=constants.ACCENT_COLOR,
            selection_color=constants.SELECTION_COLOR,
            visual_mode_color=constants.VISUAL_MODE_COLOR,
            transparent=constants.BACKGROUND_TRANSPARENT,
        )
        log.debug(f"Generated CSS with border_radius={constants.BORDER_RADIUS}")
        glass = (
            ".main-window, .settings-window, .preview-window, .help-window"
            " { background-color: transparent; }"
            if constants.BACKGROUND_TRANSPARENT
            else ""
        )
        return "\n".join((css, load_theme_css(constants.THEME), glass, load_user_css()))

    def update_style_css(self, border_radius=None, accent_color=None,
                         selection_color=None, visual_mode_color=None,
                         transparent=None, theme=None):
        """Update CSS styles on-the-fly."""
        # Update global constants
        import clipse_gui.constants as constants

        if border_radius is not None:
            constants.BORDER_RADIUS = border_radius
        if accent_color is not None:
            constants.ACCENT_COLOR = accent_color
        if selection_color is not None:
            constants.SELECTION_COLOR = selection_color
        if visual_mode_color is not None:
            constants.VISUAL_MODE_COLOR = visual_mode_color
        if transparent is not None:
            constants.BACKGROUND_TRANSPARENT = transparent
        if theme is not None:
            constants.THEME = theme

        self._apply_css()
        if accent_color is not None or theme is not None:
            self.populate_list_view()
        if self.window:
            self.window.queue_draw()
            self._invalidate_style_contexts(self.window)

    def _invalidate_style_contexts(self, widget):
        """Recursively invalidate style contexts to force CSS reload."""
        if hasattr(widget, 'get_style_context'):
            widget.get_style_context().invalidate()
        if hasattr(widget, 'get_children'):
            for child in widget.get_children():
                self._invalidate_style_contexts(child)

    def update_zoom(self):
        """Applies the current zoom level to the application CSS."""
        self.zoom_level = max(0.5, min(self.zoom_level, 3.0))
        self._apply_css()
        log.debug(f"Zoom updated to {self.zoom_level:.2f}")

    def update_compact_mode(self, skip_populate=False):
        """Updates the UI based on compact mode state.

        Note: window resize only takes proper effect when this runs at startup
        (before/just after first show). Live toggling at runtime requires the
        Apply & Restart path in the settings dialog.
        """
        pin_btn = getattr(self, "pin_filter_button", None)

        if self.compact_mode:
            self.main_box.get_style_context().add_class("compact-mode")
            target_w = int(DEFAULT_WINDOW_WIDTH * 0.6)
            target_h = int(DEFAULT_WINDOW_HEIGHT * 0.6)
            # set_no_show_all = persistent hide, survives show_all() calls
            self.search_entry.set_no_show_all(True)
            self.search_entry.hide()
            if pin_btn:
                pin_btn.set_no_show_all(True)
                pin_btn.hide()
        else:
            self.main_box.get_style_context().remove_class("compact-mode")
            target_w = DEFAULT_WINDOW_WIDTH
            target_h = DEFAULT_WINDOW_HEIGHT
            self.search_entry.set_no_show_all(False)
            self.search_entry.show()
            if pin_btn:
                pin_btn.set_no_show_all(False)
                pin_btn.show()

        self.window.resize(target_w, target_h)

        if not skip_populate:
            self.populate_list_view()

    def update_hover_to_select(self, enabled):
        """Updates hover-to-select setting and repopulates the list."""
        self.hover_to_select = enabled
        self.populate_list_view()
