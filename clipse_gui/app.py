import logging
from . import constants
from .constants import (
    APP_NAME,
    APPLICATION_ID,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
)
from .controller import ClipboardHistoryController
from .tray_manager import TrayManager

from gi.repository import Gtk, Gio, GLib  # noqa: E402

log = logging.getLogger(__name__)


# --- Gtk.Application Subclass ---
class ClipseGuiApplication(Gtk.Application):
    """The main GTK Application."""

    def __init__(self):
        super().__init__(
            application_id=APPLICATION_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        self.window = None
        self.controller = None
        self.tray_manager = None

    def do_startup(self):
        """Called once when the application starts."""
        Gtk.Application.do_startup(self)
        log.debug(f"Application {APPLICATION_ID} starting up.")

    def do_activate(self):
        """Called when the application is launched. Creates the main window and controller."""
        if not self.window:
            log.debug("Activating application - creating main window.")

            self.window = Gtk.ApplicationWindow(application=self, title=APP_NAME)
            self.window.set_default_size(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
            try:
                self.window.set_icon_name("edit-copy")
            except GLib.Error as e:
                log.warning(f"Could not set window icon name: {e}")

            self.window.connect("delete-event", self._on_window_delete)

            # Show the window immediately so it appears without delay
            self.window.show_all()

            # Finish heavy initialization on the next idle cycle
            GLib.idle_add(self._finish_activation)
        else:
            log.debug("Application already active - presenting existing window.")
            self._restore_window_from_tray()

    def _finish_activation(self):
        """Heavy initialization deferred until after window is shown."""
        # Show config error if any
        if constants.config.load_error_message:
            log.warning("Displaying configuration error dialog to user.")
            error_dialog = Gtk.MessageDialog(
                transient_for=self.window,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="Configuration File Warning",
            )
            error_dialog.format_secondary_text(constants.config.load_error_message)
            error_dialog.run()
            error_dialog.destroy()
            constants.config.load_error_message = None

        try:
            self.controller = ClipboardHistoryController(self.window)
            self.window.show_all()
        except Exception as e:
            log.critical(f"Failed to initialize ClipboardHistoryController: {e}", exc_info=True)
            error_dialog = Gtk.MessageDialog(
                transient_for=self.window,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Application Initialization Failed",
            )
            error_dialog.format_secondary_text(
                f"Could not initialize the main application component.\n"
                f"Please check logs for details.\n\nError: {e}"
            )
            error_dialog.run()
            error_dialog.destroy()
            self.quit()
            return False

        # Tray setup after everything else
        self.tray_manager = TrayManager(self)
        return False

    def _restore_window_from_tray(self):
        """Restore and show the window, even if minimized to tray."""
        if self.window:
            # Restore from tray if minimized there
            if self.tray_manager:
                self.tray_manager._restore_window()
            else:
                # Fallback if no tray manager
                self.window.present()
                self.window.show_all()

    def do_shutdown(self):
        """Called when the application is shutting down."""
        log.debug(f"Application {APPLICATION_ID} shutting down.")
        # Ensure any pending save is triggered before exiting
        if (
            self.controller
            and hasattr(self.controller, "_save_timer_id")
            and self.controller._save_timer_id
        ):
            GLib.source_remove(self.controller._save_timer_id)
            log.info("Removed pending save timer on shutdown.")
            if hasattr(self.controller, "_trigger_save"):
                self.controller._trigger_save()

        # Cleanup tray resources
        if self.tray_manager:
            self.tray_manager.cleanup()

        Gtk.Application.do_shutdown(self)

    def _on_window_delete(self, window, event):
        """Handle window delete event - minimize to tray if enabled."""
        if self.tray_manager and constants.MINIMIZE_TO_TRAY:
            if self.tray_manager.minimize_to_tray():
                return True  # Prevent window destruction
        return False  # Allow normal window destruction
