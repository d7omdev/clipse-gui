"""Clipboard copy/paste operations and paste-simulation."""

import logging
import mimetypes
import os
import shlex
import subprocess

from gi.repository import GLib

from ..constants import (
    COPY_TOOL_CMD,
    ENTER_TO_PASTE,
    PASTE_SIMULATION_CMD_WAYLAND,
    PASTE_SIMULATION_CMD_X11,
    PASTE_SIMULATION_DELAY_MS,
    X11_COPY_TOOL_CMD,
)

log = logging.getLogger(__name__)


class ClipboardMixin:
    def _run_paste_command(self, cmd_args, input_data=None, is_binary=False):
        """Helper to run the paste command subprocess."""
        try:
            log.info(f"Running paste command: {cmd_args}")
            process = subprocess.Popen(
                cmd_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout_output, stderr_output = None, None
            try:
                input_bytes = (
                    input_data
                    if is_binary
                    else input_data.encode("utf-8")
                    if input_data is not None
                    else None
                )
                stdout_output, stderr_output = process.communicate(
                    input=input_bytes, timeout=5
                )
            except subprocess.TimeoutExpired:
                log.error(f"Paste command timed out: {cmd_args}")
                process.kill()
                stdout_output, stderr_output = process.communicate()
                self.flash_status("Error: Paste command timed out")
                return False
            except OSError as e:
                log.error(f"OSError during paste command communicate: {e}")
                if process.stderr:
                    stderr_output = process.stderr.read()
                self.flash_status(f"Error communicating with paste command: {e}")
                return False
            except Exception as e:
                log.error(f"Unexpected error during paste command communicate: {e}")
                if process.stderr:
                    stderr_output = process.stderr.read()
                self.flash_status(f"Error running paste command: {e}")
                return False

            if process.returncode != 0:
                stderr_text = (
                    stderr_output.decode("utf-8", errors="ignore").strip()
                    if stderr_output
                    else "No stderr output"
                )
                log.error(
                    f"Paste command failed with code {process.returncode}: {stderr_text}"
                )
                self.flash_status(f"Paste command error: {stderr_text[:100]}")
                return False
            else:
                log.info("Paste command successful.")
                return True
        except FileNotFoundError:
            log.error(f"Paste command not found: {cmd_args[0]}")
            self.flash_status(f"Error: Command '{cmd_args[0]}' not found.")
            return False
        except Exception as e:
            log.error(f"Error invoking paste command {cmd_args}: {e}")
            self.flash_status(f"Error starting paste command: {str(e)}")
            return False

    def _get_copy_command(self):
        """Gets the appropriate command for copying TO the clipboard."""
        if self._is_wayland:
            return str(COPY_TOOL_CMD)
        else:
            return str(X11_COPY_TOOL_CMD or COPY_TOOL_CMD)

    def copy_text_to_clipboard(self, text_value):
        """Use the configured command to place text into the clipboard."""
        copy_cmd = self._get_copy_command()
        if not copy_cmd:
            self.flash_status("Error: No copy command configured.")
            return False
        try:
            cmd_args = shlex.split(copy_cmd)
        except Exception as e:
            log.error(f"Could not parse COPY_TOOL_CMD ('{COPY_TOOL_CMD}'): {e}")
            self.flash_status("Error: Invalid copy command in config")
            return False
        try:
            process = subprocess.Popen(
                cmd_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if process.stdin:
                process.stdin.write(text_value.encode("utf-8"))
                process.stdin.close()
                # Wait for process to complete to ensure clipboard is updated
                process.wait(timeout=5)
            else:
                log.error("Process stdin is None. Cannot write to clipboard.")
                self.flash_status("Error: Unable to write to clipboard")
                return False

            return True
        except subprocess.TimeoutExpired:
            log.error(f"Copy command timed out: {copy_cmd}")
            self.flash_status("Error: Copy command timed out")
            return False
        except FileNotFoundError:
            log.error(f"Copy command not found: {cmd_args[0]}")
            self.flash_status(f"Error: Copy command '{cmd_args[0]}' not found.")
            return False
        except Exception as e:
            log.error(f"Error copying text to clipboard: {e}")
            self.flash_status(f"Error copying text: {str(e)[:100]}")
            return False

    def copy_image_to_clipboard(self, image_path):
        """Use the configured command to place an image into the clipboard."""
        copy_cmd_base = self._get_copy_command()
        if not copy_cmd_base:
            self.flash_status("Error: No copy command configured.")
            return False

        try:
            if not os.path.isfile(image_path):
                log.error(f"Image file does not exist: {image_path}")
                self.flash_status("Error: Image file not found")
                return False

            mimetype, _ = mimetypes.guess_type(image_path)
            if not mimetype or not mimetype.startswith("image/"):
                image_ext = os.path.splitext(image_path)[1].lower()
                mimetype = (
                    f"image/{image_ext.lstrip('.')}" if image_ext else "image/png"
                )
                log.warning(
                    f"Could not guess mimetype for {image_path}, using {mimetype}"
                )

            try:
                base_cmd_args = shlex.split(copy_cmd_base)
            except Exception as e:
                log.error(f"Could not parse copy command ('{copy_cmd_base}'): {e}")
                self.flash_status(
                    f"Error: Invalid copy command: {copy_cmd_base[:50]}..."
                )
                return False

            cmd_args = base_cmd_args
            if "wl-copy" in os.path.basename(base_cmd_args[0]):
                cmd_args = base_cmd_args + ["--type", mimetype]

            with open(image_path, "rb") as img_file:
                try:
                    process = subprocess.Popen(
                        cmd_args,
                        stdin=img_file,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    stdout_data, stderr_data = process.communicate(timeout=10)

                    if process.returncode != 0:
                        err_msg = (
                            stderr_data.decode("utf-8", errors="ignore").strip()
                            or stdout_data.decode("utf-8", errors="ignore").strip()
                        )
                        log.error(
                            f"Image copy command failed (code {process.returncode}): {err_msg}"
                        )
                        self.flash_status(f"Image copy failed: {err_msg[:100]}")
                        return False

                    # self.flash_status("Image copied to clipboard")
                    log.info("Image copied successfully.")
                    return True

                except subprocess.TimeoutExpired:
                    log.error(f"Image copy command timed out: {cmd_args}")
                    self.flash_status("Error: Image copy timed out")
                    return False
                except FileNotFoundError:
                    log.error(f"Copy command not found: {cmd_args[0]}")
                    self.flash_status(f"Error: Copy command '{cmd_args[0]}' not found.")
                    return False
                except Exception as e:
                    log.error(f"Error copying image to clipboard: {e}")
                    self.flash_status(f"Error copying image: {str(e)[:100]}")
                    return False

        except Exception as e:
            log.error(f"Unexpected error preparing image copy: {e}", exc_info=True)
            self.flash_status(f"Error copying image: {str(e)[:100]}")
            return False

    def copy_selected_item_to_clipboard(self, with_paste_simulation=False):
        """Copies the selected item to the system clipboard and closes the window."""
        selected_row = self.list_box.get_selected_row()
        exit_timeout = 150
        if not selected_row:
            log.warning("Copy called with no row selected.")
            return

        original_index = getattr(selected_row, "item_index", -1)
        is_image = getattr(selected_row, "file_path") not in [None, "null"]
        item_value = getattr(selected_row, "item_value", None)

        if original_index == -1:
            log.error("Selected row missing valid item_index attribute.")
            self.flash_status("Error: Invalid selected item data.")
            return

        try:
            if not (0 <= original_index < len(self.items)):
                log.error(
                    f"Item with original index {original_index} no longer exists in master list."
                )
                self.flash_status("Error: Selected item no longer exists.")
                return

            item = self.items[original_index]

            def close_window_callback(window):
                if window and window.get_realized():
                    log.info("Closing window after successful copy.")
                    window.get_application().quit()
                return False

            copy_successful = False
            if is_image:
                image_path = item.get("filePath")
                if image_path and os.path.exists(image_path):
                    copy_successful = self.copy_image_to_clipboard(image_path)
                else:
                    log.error(
                        f"Image path invalid or file missing for item {original_index}: {image_path}"
                    )
                    self.flash_status("Image path invalid or file missing")
            else:
                text_to_copy = item.get("value")
                if text_to_copy is not None:
                    copy_successful = self.copy_text_to_clipboard(item_value)
                else:
                    log.error(f"Text item {original_index} has None value in data.")
                    self.flash_status("Cannot copy null text value.")

            if copy_successful:
                if ENTER_TO_PASTE or with_paste_simulation:
                    log.debug("Hiding window and scheduling paste simulation.")
                    self.window.hide()
                    GLib.timeout_add(
                        PASTE_SIMULATION_DELAY_MS or 150,
                        self._trigger_paste_simulation_and_quit,
                    )
                else:
                    GLib.timeout_add(100, self._quit_application)
            else:
                log.error("Copy operation failed.")
                self.flash_status("Error: Copy operation failed.")
                GLib.timeout_add(exit_timeout, close_window_callback, self.window)

        except Exception as e:
            log.error(f"Unexpected error during copy selection: {e}", exc_info=True)
            self.flash_status(f"Error copying: {str(e)}")

    def _trigger_paste_simulation_and_quit(self):
        """Called after a delay to run paste simulation and then quit."""
        log.debug("Attempting paste simulation...")
        paste_success = self.paste_from_clipboard_simulated()
        if paste_success:
            log.info("Paste simulation command successful.")
        else:
            log.warning("Paste simulation command failed or skipped.")
            # Optional: Show the window again if paste fails?
            # self.window.show()
            # self.flash_status("Paste failed. Check logs/dependencies (xdotool/wtype).")

        # Quit the application after a longer delay to ensure paste completes
        # Some applications need more time to receive and process the paste
        quit_delay = 200  # ms - increased from 50ms for better reliability
        GLib.timeout_add(quit_delay, self._quit_application)
        return False  # Prevent timer from repeating

    def _quit_application(self):
        """Safely quits the GTK application."""
        log.info("Quitting application.")
        app = self.window.get_application()
        if app:
            app.quit()
        return False  # Prevent timer from repeating

    def paste_from_clipboard_simulated(self):
        """Pastes FROM the clipboard by simulating key presses (Ctrl+V)."""
        if self._is_wayland:
            cmd_str = str(PASTE_SIMULATION_CMD_WAYLAND)
            tool_name = "wtype"
        else:
            cmd_str = str(PASTE_SIMULATION_CMD_X11)
            tool_name = "xdotool"

        if not cmd_str:
            log.error(
                f"Paste simulation command not configured for {'Wayland' if self._is_wayland else 'X11'}."
            )
            self.flash_status("Error: Paste simulation command not configured.")
            return False

        try:
            cmd_args = shlex.split(cmd_str)
        except Exception as e:
            log.error(f"Could not parse paste simulation command ('{cmd_str}'): {e}")
            self.flash_status(f"Error: Invalid Paste command: {cmd_str[:50]}...")
            return False

        log.debug(f"Executing paste simulation command: {cmd_args}")
        try:
            # Use run for simplicity, capture output for errors
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=5,  # Timeout for the simulation command
                check=False,  # Don't raise exception on non-zero exit code, check manually
            )

            if result.returncode != 0:
                error_output = result.stderr.strip() or result.stdout.strip()
                error_msg = f"Paste simulation ({tool_name}) failed (code {result.returncode}): {error_output}"
                log.error(error_msg)
                # Don't flash here, happens after window is hidden
                # self.flash_status(f"{tool_name} error: {error_output[:100]}")
                return False

            log.info(f"Paste simulation ({tool_name}) command successful.")
            return True

        except FileNotFoundError:
            error_msg = f"Paste simulation command not found: '{cmd_args[0]}'. Is '{tool_name}' installed?"
            log.error(error_msg)
            # self.flash_status(error_msg)
            return False
        except subprocess.TimeoutExpired:
            error_msg = f"Paste simulation command timed out: '{cmd_str}'"
            log.error(error_msg)
            # self.flash_status(error_msg)
            return False
        except Exception as e:
            error_msg = f"Error running paste simulation command '{cmd_str}': {e}"
            log.error(error_msg)
            # self.flash_status(error_msg[:150])
            return False
