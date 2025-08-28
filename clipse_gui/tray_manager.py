import logging
import gi

try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3

    HAS_APPINDICATOR = True
except (ImportError, ValueError):
    HAS_APPINDICATOR = False
    AppIndicator3 = None

from gi.repository import Gtk, GLib
from . import constants

log = logging.getLogger(__name__)


class TrayManager:
    def __init__(self, application):
        self.application = application
        self.indicator = None
        self.status_icon = None
        self.menu = None
        self._is_tray_enabled = constants.MINIMIZE_TO_TRAY
        self._setup_tray_icon()

    def _setup_tray_icon(self):
        if not self._is_tray_enabled:
            return
        # Don't create indicator on startup, only when needed
        if not HAS_APPINDICATOR:
            self._setup_status_icon()

    def _setup_appindicator(self):
        if not AppIndicator3:
            self._setup_status_icon()
            return
        try:
            import os

            # Try app icon first
            icon_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "clipse-gui.png"
            )
            if os.path.exists(icon_path):
                icon_name = icon_path
            else:
                icon_name = "edit-copy"

            self.indicator = AppIndicator3.Indicator.new(
                "clipse-gui",
                icon_name,
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )

            self._create_basic_menu()
            self.indicator.set_menu(self.menu)
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            log.debug("AppIndicator created and set to ACTIVE")

        except Exception as e:
            log.warning(f"AppIndicator failed: {e}")
            self.indicator = None
            self._setup_status_icon()

    def _setup_status_icon(self):
        try:
            self.status_icon = Gtk.StatusIcon.new_from_icon_name("edit-copy")
            self.status_icon.set_title(constants.APP_NAME)
            self.status_icon.set_tooltip_text(
                f"{constants.APP_NAME} - Clipboard Manager"
            )
            self.status_icon.connect("activate", self._on_tray_activate)
            self.status_icon.connect("popup-menu", self._on_tray_popup_menu)
            self.status_icon.set_visible(False)
        except Exception as e:
            self.status_icon = None

    def _create_basic_menu(self):
        """Create basic menu with Show/Quit only"""
        self.menu = Gtk.Menu()

        restore_item = Gtk.MenuItem.new_with_label("Show Clipse GUI")
        restore_item.connect("activate", lambda x: self._restore_window())
        restore_item.show()
        self.menu.append(restore_item)

        quit_item = Gtk.MenuItem.new_with_label("Quit")
        quit_item.connect("activate", lambda x: self.application.quit())
        quit_item.show()
        self.menu.append(quit_item)

    def _update_menu_with_items(self):
        """Update menu to include clipboard items"""
        if not self.menu:
            return

        # Clear menu
        for item in self.menu.get_children():
            self.menu.remove(item)

        # Get clipboard items
        items = []
        try:
            if (
                hasattr(self.application, "controller")
                and self.application.controller
                and hasattr(self.application.controller, "data_manager")
            ):
                items = self.application.controller.data_manager.load_history()
        except:
            pass

        recent_items = items[:5] if items else []

        if not self.menu:
            self._create_basic_menu()
            return

        # Add clipboard items
        if recent_items:
            for i, item in enumerate(recent_items):
                self._add_item_to_menu(item, i + 1)

            # Add separator
            separator = Gtk.SeparatorMenuItem()
            separator.show()
            self.menu.append(separator)
        else:
            no_items = Gtk.MenuItem.new_with_label("No clipboard items")
            no_items.set_sensitive(False)
            no_items.show()
            self.menu.append(no_items)

            separator = Gtk.SeparatorMenuItem()
            separator.show()
            self.menu.append(separator)

        # Add Show/Quit
        restore_item = Gtk.MenuItem.new_with_label("Show Clipse GUI")
        restore_item.connect("activate", lambda x: self._restore_window())
        restore_item.show()
        self.menu.append(restore_item)

        quit_item = Gtk.MenuItem.new_with_label("Quit")
        quit_item.connect("activate", lambda x: self.application.quit())
        quit_item.show()
        self.menu.append(quit_item)

    def _add_item_to_menu(self, item, index):
        """Add single clipboard item to menu"""
        if not self.menu:
            return
        try:
            value = item.get("value", "")
            is_image = item.get("filePath") not in [None, "", "null"]

            if is_image:
                display_text = f"Image ({index})"
            else:
                clean_text = value.replace("\n", " ").replace("\t", " ").strip()
                if len(clean_text) > 40:
                    display_text = f"{clean_text[:37]}..."
                else:
                    display_text = clean_text if clean_text else f"Empty ({index})"

            menu_item = Gtk.MenuItem.new_with_label(display_text)
            menu_item.connect(
                "activate", lambda x, item=item: self._copy_item_to_clipboard(item)
            )
            menu_item.show()
            self.menu.append(menu_item)
        except:
            pass

    def _copy_item_to_clipboard(self, item):
        """Copy selected item to clipboard"""
        try:
            if hasattr(self.application, "controller") and self.application.controller:
                controller = self.application.controller
                value = item.get("value", "")
                file_path = item.get("filePath")
                is_image = file_path not in [None, "", "null"]

                if is_image and file_path:
                    controller.copy_image_to_clipboard(file_path)
                else:
                    controller.copy_text_to_clipboard(value)
        except:
            pass

    def _on_tray_activate(self, status_icon):
        self._restore_window()

    def _on_tray_popup_menu(self, status_icon, button, activate_time):
        self._update_menu_with_items()
        if self.menu:
            self.menu.show_all()
            self.menu.popup(
                None,
                None,
                Gtk.StatusIcon.position_menu,
                status_icon,
                button,
                activate_time,
            )

    def _restore_window(self):
        if self.application.window:
            self.application.window.present()
            self.application.window.show_all()

            if self.indicator and AppIndicator3:
                self.indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
            elif self.status_icon:
                self.status_icon.set_visible(False)

    def minimize_to_tray(self):
        if not self._is_tray_enabled:
            return False

        if HAS_APPINDICATOR:
            # Create indicator only when minimizing
            if not self.indicator:
                self._setup_appindicator()

            if self.indicator and AppIndicator3:
                log.debug("Showing tray icon")
                self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
                GLib.timeout_add(200, self._delayed_menu_update)
                if self.application.window:
                    self.application.window.hide()
                return True

        elif self.status_icon:
            if not self.status_icon.is_embedded():
                return False
            self.status_icon.set_visible(True)
            if self.application.window:
                self.application.window.hide()
            return True

        return False

    def _delayed_menu_update(self):
        """Update menu after a small delay to ensure data is loaded"""
        self._update_menu_with_items()
        if self.indicator:
            self.indicator.set_menu(self.menu)
        return False  # Don't repeat

    def _set_attention(self):
        """Helper to set attention status"""
        if self.indicator and AppIndicator3:
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ATTENTION)
        return False

    def _set_active(self):
        """Helper to set active status"""
        if self.indicator and AppIndicator3:
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        return False

    def set_tray_enabled(self, enabled):
        self._is_tray_enabled = enabled
        if enabled and not (self.indicator or self.status_icon):
            self._setup_tray_icon()
        elif not enabled:
            self.cleanup()

    def is_tray_available(self):
        if self.indicator:
            return True
        elif self.status_icon:
            return self.status_icon.is_embedded()
        return False

    def cleanup(self):
        if self.indicator and AppIndicator3:
            self.indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
            self.indicator = None
        if self.status_icon:
            self.status_icon.set_visible(False)
            self.status_icon = None
        if self.menu:
            self.menu = None
