#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")

from clipse_gui import __version__, constants  # noqa: E402

PACKAGE_PARENT = ".."
SCRIPT_DIR = os.path.dirname(
    os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__)))
)
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

log = None


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[1;36m",
        "INFO": "\033[1;32m",
        "WARNING": "\033[1;33m",
        "ERROR": "\033[1;31m",
        "CRITICAL": "\033[1;41m",
        "RESET": "\033[0m",
    }

    def format(self, record):
        level_color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]
        record.levelname = f"{level_color}{record.levelname}{reset}"
        record.name = f"\033[1;34m{record.name}\033[0m"
        record.asctime = f"\033[1;37m{self.formatTime(record, self.datefmt)}\033[0m"
        return super().format(record)


def parse_args_from_sys_argv():
    parser = argparse.ArgumentParser(
        description="Start the Clipse GUI application.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"Clipse GUI v{__version__}"
    )
    return parser.parse_known_args()


def setup_logging(debug=False):
    global log
    try:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        stream_handler.setFormatter(ColorFormatter(log_format, datefmt=date_format))

        handlers = [stream_handler]

        # File logging only in debug mode — RotatingFileHandler adds ~100ms I/O on every start
        if debug:
            log_file_path = os.path.join(constants.CONFIG_DIR, "clipse-gui.log")
            file_handler = RotatingFileHandler(
                filename=log_file_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
            handlers.append(file_handler)

        logging.basicConfig(level=logging.DEBUG, handlers=handlers)
        log = logging.getLogger(__name__)
        log.info(f"Logging initialized ({'DEBUG + file' if debug else 'INFO'})")
    except Exception as e:
        print(f"CRITICAL: Failed to set up logging: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


def main():
    args, gtk_args = parse_args_from_sys_argv()
    setup_logging(debug=args.debug)

    if log is None:
        print("CRITICAL: Logging setup failed. Exiting.", file=sys.stderr)
        sys.exit(1)

    try:
        Path(constants.CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.critical(f"Failed to create config directory: {e}", exc_info=True)
        sys.exit(1)

    try:
        from clipse_gui.app import ClipseGuiApplication

        app = ClipseGuiApplication()
        exit_status = app.run(gtk_args)
        log.info(f"Application exited with status {exit_status}.")
        sys.exit(exit_status)
    except Exception as e:
        log.critical(f"Unhandled exception in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
