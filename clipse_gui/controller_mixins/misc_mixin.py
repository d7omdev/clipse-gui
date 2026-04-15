"""Application lifecycle: restart and window destroy callback."""

import logging

log = logging.getLogger(__name__)


class MiscMixin:
    def restart_application(self):
        """Restarts the application to apply settings changes."""
        import sys
        import os
        import subprocess
        import shutil

        log.info("Restarting application to apply settings changes...")
        app = self.window.get_application()
        if app:
            app.quit()

        try:
            clipse_gui_path = shutil.which("clipse-gui")

            if clipse_gui_path:
                args = [clipse_gui_path] + sys.argv[1:]
                log.debug(f"Restarting with system executable: {args}")
                subprocess.Popen(args, cwd=os.getcwd())
            elif getattr(sys, "frozen", False):
                executable = sys.executable
                args = [executable] + sys.argv[1:]
                log.debug(f"Restarting with frozen executable: {args}")
                subprocess.Popen(args, cwd=os.getcwd())
            else:
                original_cmd = sys.argv[0]
                if os.path.isfile(original_cmd) and os.access(original_cmd, os.X_OK):
                    args = [original_cmd] + sys.argv[1:]
                    log.debug(f"Restarting with original command: {args}")
                    subprocess.Popen(args, cwd=os.getcwd())
                else:
                    raise Exception(f"Cannot find executable: {original_cmd}")

        except Exception as e:
            log.error(f"Failed to restart application: {e}")

        if app:
            app.quit()
        else:
            sys.exit(0)

    def on_window_destroy(self, widget):
        log.info("Main window closed.")
