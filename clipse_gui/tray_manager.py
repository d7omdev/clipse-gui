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
        self._last_items_hash = None  # Track if items changed
        self._setup_tray_icon()

    def _setup_tray_icon(self):
        if not self._is_tray_enabled:
            return
        # Don't create indicator on startup, only when needed
        if not HAS_APPINDICATOR:
            self._setup_status_icon()

    def _setup_appindicator(self):
        if not AppIndicator3:
            log.debug("AppIndicator3 not available, falling back to StatusIcon")
            self._setup_status_icon()
            return
        try:
            # Try multiple icon paths for development and production
            icon_name = self._get_icon_path()
            log.info(f"Using tray icon: {icon_name}")

            self.indicator = AppIndicator3.Indicator.new(
                "clipse-gui",
                icon_name,
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )

            # Build fresh menu with current items
            self._build_fresh_menu()
            self.indicator.set_menu(self.menu)

            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            log.info("AppIndicator created and set to ACTIVE")

        except Exception as e:
            log.warning(f"AppIndicator failed: {e}")
            self.indicator = None
            self._setup_status_icon()

    def _get_icon_path(self):
        """Find the best available icon path for tray."""
        import os

        # List of possible icon locations
        possible_paths = [
            # Development: relative to this file
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "clipse-gui.png"),
            # Installed: in the package data
            os.path.join(os.path.dirname(__file__), "clipse-gui.png"),
            # System: /usr/share/pixmaps
            "/usr/share/pixmaps/clipse-gui.png",
            # System: /usr/local/share/pixmaps
            "/usr/local/share/pixmaps/clipse-gui.png",
            # User: ~/.local/share/pixmaps
            os.path.expanduser("~/.local/share/pixmaps/clipse-gui.png"),
            # User: ~/.icons
            os.path.expanduser("~/.icons/clipse-gui.png"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                log.debug(f"Found icon at: {path}")
                return path

        # Fallback to system icon name
        log.warning("Custom icon not found, using fallback 'edit-copy'")
        return "edit-copy"

    def _setup_status_icon(self):
        try:
            # Try to use custom icon if available
            import os
            from gi.repository import GdkPixbuf

            icon_path = self._get_icon_path()
            if os.path.exists(icon_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 24, 24)
                    self.status_icon = Gtk.StatusIcon.new_from_pixbuf(pixbuf)
                    log.info(f"StatusIcon created with custom icon: {icon_path}")
                except Exception as e:
                    log.warning(f"Failed to load custom icon for StatusIcon: {e}")
                    self.status_icon = Gtk.StatusIcon.new_from_icon_name("edit-copy")
            else:
                self.status_icon = Gtk.StatusIcon.new_from_icon_name("edit-copy")
                log.info("StatusIcon created with fallback icon 'edit-copy'")

            self.status_icon.set_title(constants.APP_NAME)
            self.status_icon.set_tooltip_text(
                f"{constants.APP_NAME} - Clipboard Manager"
            )
            self.status_icon.connect("activate", self._on_tray_activate)
            self.status_icon.connect("popup-menu", self._on_tray_popup_menu)
            self.status_icon.set_visible(False)
        except Exception as e:
            log.error(f"Failed to setup StatusIcon: {e}")
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

    def _make_click_handler(self, item):
        """Create a click handler for a specific item - fixes closure capture issue."""
        # Store item data by value (deep copy of relevant fields)
        item_value = item.get("value", "")
        item_file_path = item.get("filePath", "")
        item_recorded = item.get("recorded", "")

        def handler(menu_item):
            # Reconstruct the item dict for the handler
            reconstructed_item = {
                "value": item_value,
                "filePath": item_file_path,
                "recorded": item_recorded,
            }
            log.debug(f"Tray menu item clicked: {item_value[:50]}...")
            self._copy_item_to_clipboard(reconstructed_item)

        return handler

    def _add_item_to_menu_internal(self, menu, item, index):
        """Add single clipboard item to a specific menu instance."""
        if not menu:
            return
        try:
            # Deep copy item data to avoid any reference issues
            item_copy = {
                "value": item.get("value", ""),
                "filePath": item.get("filePath", ""),
                "recorded": item.get("recorded", ""),
            }

            value = item_copy["value"]
            is_image = item_copy["filePath"] not in [None, "", "null"]

            if is_image:
                display_text = f"Image ({index})"
            else:
                clean_text = value.replace("\n", " ").replace("\t", " ").strip()
                if len(clean_text) > 40:
                    display_text = f"{clean_text[:37]}..."
                else:
                    display_text = clean_text if clean_text else f"Empty ({index})"

            menu_item = Gtk.MenuItem.new_with_label(display_text)
            menu_item.connect("activate", self._make_click_handler(item_copy))
            menu_item.show()
            menu.append(menu_item)
            log.debug(f"Added menu item {index}: {display_text[:40]}")
        except Exception as e:
            log.error(f"Error adding item to menu: {e}")

    def _add_item_to_submenu_internal(self, submenu, item, index):
        """Add single clipboard item to a specific submenu instance."""
        if not submenu:
            return
        try:
            # Deep copy item data to avoid any reference issues
            item_copy = {
                "value": item.get("value", ""),
                "filePath": item.get("filePath", ""),
                "recorded": item.get("recorded", ""),
            }

            value = item_copy["value"]
            is_image = item_copy["filePath"] not in [None, "", "null"]

            if is_image:
                display_text = f"Image ({index})"
            else:
                clean_text = value.replace("\n", " ").replace("\t", " ").strip()
                if len(clean_text) > 40:
                    display_text = f"{clean_text[:37]}..."
                else:
                    display_text = clean_text if clean_text else f"Empty ({index})"

            menu_item = Gtk.MenuItem.new_with_label(display_text)
            menu_item.connect("activate", self._make_click_handler(item_copy))
            menu_item.show()
            submenu.append(menu_item)
        except Exception as e:
            log.error(f"Error adding item to submenu: {e}")

    def _copy_item_to_clipboard(self, item):
        """Copy selected item to clipboard"""
        try:
            log.debug(
                f"_copy_item_to_clipboard called with item value: {item.get('value', '')[:80]}..."
            )
            if hasattr(self.application, "controller") and self.application.controller:
                controller = self.application.controller
                value = item.get("value", "")
                file_path = item.get("filePath")
                is_image = file_path not in [None, "", "null"]

                log.info(
                    f"Copying to clipboard from tray: {'Image' if is_image else value[:50]}..."
                )

                copy_success = False
                if is_image and file_path:
                    copy_success = controller.copy_image_to_clipboard(file_path)
                else:
                    copy_success = controller.copy_text_to_clipboard(value)

                # Paste on select if enabled
                if constants.TRAY_PASTE_ON_SELECT and copy_success:
                    log.debug(
                        "Tray paste on select enabled, scheduling paste simulation"
                    )
                    # Delay paste slightly to allow clipboard to update
                    GLib.timeout_add(100, self._delayed_paste)
            else:
                log.warning("Cannot copy: controller not available")
        except Exception as e:
            log.error(f"Error copying item from tray: {e}")

    def _delayed_paste(self):
        """Trigger paste simulation after a short delay."""
        try:
            if hasattr(self.application, "controller") and self.application.controller:
                self.application.controller.paste_from_clipboard_simulated()
        except Exception as e:
            log.error(f"Error in delayed paste: {e}")
        return False  # Don't repeat

    def _on_tray_activate(self, status_icon):
        self._restore_window()

    def _on_tray_popup_menu(self, status_icon, button, activate_time):
        # Rebuild menu fresh for StatusIcon
        self._build_fresh_menu()
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
        log.info("Restoring window from tray")

        if self.application.window:
            self.application.window.present()
            self.application.window.show_all()
            self.application.window.deiconify()

            if self.indicator and AppIndicator3:
                self.indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
                log.debug("Set AppIndicator to PASSIVE")
            elif self.status_icon:
                self.status_icon.set_visible(False)
                log.debug("Set StatusIcon to invisible")
        else:
            log.warning("Cannot restore: window is None")

    def minimize_to_tray(self):
        if not self._is_tray_enabled:
            log.debug("Minimize to tray disabled")
            return False

        log.info("Minimizing window to tray")

        if HAS_APPINDICATOR:
            # Create indicator only when minimizing
            if not self.indicator:
                self._setup_appindicator()

            if self.indicator and AppIndicator3:
                log.info("Showing AppIndicator tray icon")
                self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
                # Build fresh menu with current items
                self._build_fresh_menu()
                if self.application.window:
                    self.application.window.hide()
                    log.debug("Window hidden")
                return True
            else:
                log.warning("AppIndicator not available after setup")

        elif self.status_icon:
            if not self.status_icon.is_embedded():
                log.warning("StatusIcon not embedded in tray")
                return False
            log.info("Showing StatusIcon tray icon")
            self.status_icon.set_visible(True)
            if self.application.window:
                self.application.window.hide()
                log.debug("Window hidden")
            return True
        else:
            log.warning("No tray icon available (neither AppIndicator nor StatusIcon)")

        return False

    def _build_fresh_menu(self):
        """Build a completely fresh menu with current clipboard items."""
        log.debug("Building fresh tray menu")

        # Get current items
        items = []
        try:
            if (
                hasattr(self.application, "controller")
                and self.application.controller
                and hasattr(self.application.controller, "data_manager")
            ):
                items = self.application.controller.data_manager.load_history()
        except Exception as e:
            log.error(f"Error loading history for tray: {e}")
            return

        recent_items = items[: constants.TRAY_ITEMS_COUNT] if items else []

        # Create completely new menu
        new_menu = Gtk.Menu()

        # Add clipboard items
        if recent_items:
            visible_count = min(10, len(recent_items))

            for i, item in enumerate(recent_items[:visible_count]):
                self._add_item_to_menu_internal(new_menu, item, i + 1)

            if len(recent_items) > visible_count:
                more_item = Gtk.MenuItem.new_with_label(
                    f"More... ({len(recent_items) - visible_count} items)"
                )
                more_menu = Gtk.Menu()

                for i, item in enumerate(
                    recent_items[visible_count:], visible_count + 1
                ):
                    self._add_item_to_submenu_internal(more_menu, item, i)

                more_item.set_submenu(more_menu)
                more_item.show()
                new_menu.append(more_item)

            separator = Gtk.SeparatorMenuItem()
            separator.show()
            new_menu.append(separator)
        else:
            no_items = Gtk.MenuItem.new_with_label("No clipboard items")
            no_items.set_sensitive(False)
            no_items.show()
            new_menu.append(no_items)

            separator = Gtk.SeparatorMenuItem()
            separator.show()
            new_menu.append(separator)

        # Add Show/Quit
        restore_item = Gtk.MenuItem.new_with_label("Show Clipse GUI")
        restore_item.connect("activate", lambda x: self._restore_window())
        restore_item.show()
        new_menu.append(restore_item)

        quit_item = Gtk.MenuItem.new_with_label("Quit")
        quit_item.connect("activate", lambda x: self.application.quit())
        quit_item.show()
        new_menu.append(quit_item)

        # Replace the menu
        self.menu = new_menu
        if self.indicator:
            self.indicator.set_menu(self.menu)
            log.debug(f"Set new menu with {len(recent_items)} items")

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
