import logging
import signal
from . import constants
from .constants import (
    APP_NAME,
    APPLICATION_ID,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
)
from .controller import ClipboardHistoryController
from .tray_manager import TrayManager

from gi.repository import Gdk, Gtk, Gio, GLib  # noqa: E402

# gtk-layer-shell: optional, enables cursor-position launch on Wayland
try:
    import gi as _gi

    _gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell  # noqa: E402

    _HAS_LAYER_SHELL = True
except (ImportError, ValueError):
    _HAS_LAYER_SHELL = False

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
        self._install_signal_handlers()

    def _install_signal_handlers(self):
        """Wire SIGINT (Ctrl+C) and SIGTERM into the GLib main loop for graceful exit."""
        def _on_signal(sig_name):
            log.info(f"{sig_name} received — quitting application gracefully.")
            self.quit()
            return GLib.SOURCE_REMOVE

        GLib.unix_signal_add(
            GLib.PRIORITY_DEFAULT, signal.SIGINT, _on_signal, "SIGINT"
        )
        GLib.unix_signal_add(
            GLib.PRIORITY_DEFAULT, signal.SIGTERM, _on_signal, "SIGTERM"
        )

    def do_activate(self):
        """Called when the application is launched. Creates the main window and controller."""
        if not self.window:
            log.debug("Activating application - creating main window.")

            self.window = Gtk.ApplicationWindow(application=self, title=APP_NAME)

            # Pick initial window size based on compact mode setting from config.
            # This must happen BEFORE first show so the WM honors it.
            compact_mode_on = constants.config.getboolean(
                "General", "compact_mode", fallback=False
            )
            if compact_mode_on:
                init_w = int(DEFAULT_WINDOW_WIDTH * 0.6)
                init_h = int(DEFAULT_WINDOW_HEIGHT * 0.6)
            else:
                init_w = DEFAULT_WINDOW_WIDTH
                init_h = DEFAULT_WINDOW_HEIGHT
            try:
                self.window.set_icon_name("edit-copy")
            except GLib.Error as e:
                log.warning(f"Could not set window icon name: {e}")

            if compact_mode_on:
                # Layer-shell ignores set_default_size; use set_size_request
                self.window.set_size_request(init_w, init_h)
                self._position_at_cursor(init_w, init_h)
            else:
                self.window.set_default_size(init_w, init_h)

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

    def _position_at_cursor(self, win_w, win_h):
        """Position the window at the mouse cursor.

        Wayland: use gtk-layer-shell (anchor top-left, margins = cursor pos).
        X11 fallback: standard window.move().
        """
        import os

        is_wayland = "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower()

        if is_wayland and _HAS_LAYER_SHELL:
            cx, cy, mw, mh = self._get_cursor_pos_wayland()
            if cx is not None:
                # Clamp so the window stays within the monitor
                cx = min(cx, max(0, mw - win_w))
                cy = min(cy, max(0, mh - win_h))
                self._position_layer_shell(cx, cy)
        elif not is_wayland:
            self._position_at_cursor_x11(win_w, win_h)

    def _get_cursor_pos_wayland(self):
        """Get cursor position on Wayland, relative to the monitor the cursor is on.

        Returns (cx, cy, monitor_w, monitor_h) or (None, None, 0, 0).
        Layer-shell margins are per-output, so we convert global
        compositor coordinates to monitor-local offsets.
        """
        import shutil

        if shutil.which("hyprctl"):
            return self._hyprctl_cursor_pos_local()

        return None, None, 0, 0

    def _hyprctl_cursor_pos_local(self):
        """Query Hyprland for cursor pos and convert to monitor-local coords.

        Returns (local_x, local_y, monitor_w, monitor_h) or (None, None, 0, 0).
        """
        import json
        import subprocess

        env = None
        result = subprocess.run(
            ["hyprctl", "cursorpos"], capture_output=True, timeout=1
        )
        if result.returncode != 0:
            env = self._fix_hyprland_env()
            if env:
                result = subprocess.run(
                    ["hyprctl", "cursorpos"],
                    capture_output=True, timeout=1, env=env,
                )
        if result.returncode != 0:
            log.debug(
                f"hyprctl cursorpos failed (exit {result.returncode}): "
                f"{result.stderr.decode().strip()}"
            )
            return None, None, 0, 0

        try:
            raw = result.stdout.decode().strip()
            cx, cy = (int(v.strip()) for v in raw.split(","))
        except (ValueError, TypeError) as e:
            log.debug(f"hyprctl cursorpos parse error: {e}")
            return None, None, 0, 0

        # Get monitor geometry to convert global → local
        mon_result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            capture_output=True, timeout=1, env=env,
        )
        if mon_result.returncode == 0:
            try:
                monitors = json.loads(mon_result.stdout.decode())
                for m in monitors:
                    mx, my = m["x"], m["y"]
                    mw, mh = m["width"], m["height"]
                    if mx <= cx < mx + mw and my <= cy < my + mh:
                        return cx - mx, cy - my, mw, mh
            except (json.JSONDecodeError, KeyError) as e:
                log.debug(f"hyprctl monitors parse error: {e}")

        return cx, cy, 1920, 1080

    @staticmethod
    def _fix_hyprland_env():
        """Find the newest Hyprland instance socket when the env var is stale."""
        import os
        from pathlib import Path

        hypr_dir = Path(f"/run/user/{os.getuid()}/hypr")
        if not hypr_dir.is_dir():
            return None
        instances = sorted(hypr_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for inst in instances:
            sock = inst / ".socket.sock"
            if sock.exists():
                env = os.environ.copy()
                env["HYPRLAND_INSTANCE_SIGNATURE"] = inst.name
                return env
        return None

    def _position_layer_shell(self, cx, cy):
        """Use gtk-layer-shell to place the window at (cx, cy).

        init_for_window is only called once; subsequent calls just update margins.
        """
        if not GtkLayerShell.is_layer_window(self.window):
            GtkLayerShell.init_for_window(self.window)
            GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_keyboard_mode(
                self.window, GtkLayerShell.KeyboardMode.ON_DEMAND
            )
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)

        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, cy)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.LEFT, cx)
        log.debug(f"Layer-shell positioned at cursor ({cx}, {cy})")

    def _position_at_cursor_x11(self, win_w, win_h):
        """Use GTK window.move() to position at cursor (X11)."""
        display = Gdk.Display.get_default()
        if not display:
            return
        seat = display.get_default_seat()
        if not seat:
            return
        pointer = seat.get_pointer()
        if not pointer:
            return
        screen, cx, cy = pointer.get_position()

        monitor = display.get_monitor_at_point(cx, cy)
        if monitor:
            geo = monitor.get_geometry()
        else:
            geo = Gdk.Rectangle()
            geo.x, geo.y = 0, 0
            geo.width = screen.get_width() if screen else 1920
            geo.height = screen.get_height() if screen else 1080

        x = max(geo.x, min(cx, geo.x + geo.width - win_w))
        y = max(geo.y, min(cy, geo.y + geo.height - win_h))
        self.window.move(x, y)

    def _restore_window_from_tray(self):
        """Restore and show the window, even if minimized to tray."""
        if not self.window:
            return

        # Reposition at cursor in compact mode before showing
        compact_mode_on = constants.config.getboolean(
            "General", "compact_mode", fallback=False
        )
        if compact_mode_on:
            win_w = int(DEFAULT_WINDOW_WIDTH * 0.6)
            win_h = int(DEFAULT_WINDOW_HEIGHT * 0.6)
            self._position_at_cursor(win_w, win_h)

        if self.tray_manager:
            self.tray_manager._restore_window()
        else:
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
