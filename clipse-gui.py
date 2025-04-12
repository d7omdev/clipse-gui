#!/usr/bin/env python3
import gi
import os
import sys
import logging
from pathlib import Path

# Ensure necessary GTK version
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402, F401

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format="\033[1;37m%(asctime)s\033[0m - \033[1;34m%(name)s\033[0m - \033[1;32m%(levelname)s\033[0m - %(message)s",
)
log = logging.getLogger(__name__)


# Ensure the package directory is importable if running directly
PACKAGE_PARENT = ".."
SCRIPT_DIR = os.path.dirname(
    os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__)))
)
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

try:
    # Import the Gtk.Application subclass, not the controller directly
    from clipse_gui.app import ClipseGuiApplication
    from clipse_gui.constants import CONFIG_DIR
except ImportError as e:
    log.critical(f"Error importing application modules: {e}")
    log.critical(
        "Please ensure the application structure is correct and all dependencies are installed."
    )
    sys.exit(1)


def main():
    # Ensure XDG config directory exists
    try:
        Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log.error(f"Error creating config directory {CONFIG_DIR}: {e}")
        # Allow running even if config dir creation fails? Might work read-only.
        # sys.exit(1) # Exit if config is critical

    log.info(f"Using config directory: {CONFIG_DIR}")

    # Instantiate the Gtk.Application
    app = ClipseGuiApplication()

    # Run the application's main loop
    exit_status = app.run(sys.argv)
    log.info(f"Application exited with status {exit_status}.")
    sys.exit(exit_status)


if __name__ == "__main__":
    main()
