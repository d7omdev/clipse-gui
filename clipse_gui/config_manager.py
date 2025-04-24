import configparser
import os
import logging
from typing import Optional, Any
from copy import deepcopy

log = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, config_path: str, default_settings: dict):
        self.config_path = config_path
        self.defaults = deepcopy(default_settings)
        self.config = configparser.ConfigParser(interpolation=None)
        self.load_error_message = None
        self._load_config()

    def _load_config(self):
        final_config = configparser.ConfigParser(interpolation=None)
        final_config.read_dict(self.defaults)

        needs_save = False
        user_config_read_success = False

        if os.path.exists(self.config_path):
            user_config = configparser.ConfigParser(interpolation=None)
            try:
                read_files = user_config.read(self.config_path, encoding="utf-8")
                if read_files:
                    log.info(
                        f"Successfully read user configuration: {self.config_path}"
                    )
                    user_config_read_success = True
                else:
                    log.warning(
                        f"Configuration file exists but could not be parsed or is empty: {self.config_path}"
                    )
                    self.load_error_message = (
                        f"Configuration file exists but is empty or invalid:\n"
                        f"{self.config_path}\n\n"
                        f"Using default settings. The file will be overwritten."
                    )
                    needs_save = True

            except configparser.Error as e:
                error_msg = f"Error parsing configuration file {self.config_path}: {e}"
                log.error(error_msg)
                self.load_error_message = (
                    f"Error parsing configuration file:\n{self.config_path}\n\n"
                    f"Details: {e}\n\n"
                    f"Using default settings. The file will be overwritten."
                )
                needs_save = True

            except Exception as e:
                error_msg = f"Unexpected error reading config {self.config_path}: {e}"
                log.error(error_msg)
                self.load_error_message = (
                    f"Unexpected error reading configuration file:\n{self.config_path}\n\n"
                    f"Details: {e}\n\n"
                    f"Using default settings. A clean default file will be created if possible."
                )

            if user_config_read_success:
                for section in user_config.sections():
                    if not final_config.has_section(section):
                        final_config.add_section(section)
                        needs_save = True
                    for key, value in user_config.items(section):
                        current_default = self.defaults.get(section, {}).get(key)
                        if not final_config.has_option(section, key) or str(
                            value
                        ) != str(current_default):
                            final_config.set(section, key, value)

                for section, options in self.defaults.items():
                    if not user_config.has_section(section):
                        needs_save = True
                        continue

                    for key in options:
                        if not user_config.has_option(section, key):
                            needs_save = True

        else:
            log.info(
                f"Configuration file not found: {self.config_path}. Will create with defaults."
            )
            needs_save = True

        self.config = final_config

        if needs_save:
            log.info(
                f"Configuration file needs update/creation at {self.config_path}. Saving..."
            )
            self._save_config()

    def _save_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as configfile:
                configfile.write("# Clipse GUI Configuration File\n")
                configfile.write(
                    "# Settings here override the application defaults.\n\n"
                )
                self.config.write(configfile)
            log.info(f"Configuration saved successfully to: {self.config_path}")
        except OSError as e:
            error_msg = (
                f"Failed to create/write configuration file {self.config_path}: {e}"
            )
            log.error(error_msg)
            if not self.load_error_message:
                self.load_error_message = f"Could not save configuration file:\n{self.config_path}\n\nError: {e}"
        except Exception as e:
            error_msg = f"Unexpected error writing config file {self.config_path}: {e}"
            log.error(error_msg)
            if not self.load_error_message:
                self.load_error_message = f"Unexpected error saving configuration:\n{self.config_path}\n\nError: {e}"

    def get(
        self, section: str, key: str, fallback: Optional[Any] = None
    ) -> Optional[str]:
        if not self.config.has_section(section):
            log.warning(
                f"Attempted to get key '{key}' from non-existent section '[{section}]'. Using fallback: {fallback}"
            )
            return fallback
        return self.config.get(section, key, fallback=fallback)

    def getint(
        self, section: str, key: str, fallback: Optional[int] = None
    ) -> Optional[int]:
        if not self.config.has_section(section):
            log.warning(
                f"Attempted to get key '{key}' from non-existent section '[{section}]'. Using fallback: {fallback}"
            )
            return fallback
        try:
            return self.config.getint(section, key, fallback=fallback)
        except ValueError:
            value_from_config = self.config.get(section, key, fallback=None)
            default_value_str = self.defaults.get(section, {}).get(key)
            if value_from_config is not None and str(value_from_config) != str(
                default_value_str
            ):
                log.warning(
                    f"Config value '{key}' = '{value_from_config}' in section '[{section}]' is not a valid integer. Trying fallback/default."
                )
            if fallback is not None:
                return fallback
            try:
                return int(default_value_str)
            except (ValueError, TypeError, AttributeError):
                log.error(
                    f"Could not determine a valid integer fallback/default for [{section}]/{key}. Returning None."
                )
                return None

    def getfloat(
        self, section: str, key: str, fallback: Optional[float] = None
    ) -> Optional[float]:
        if not self.config.has_section(section):
            log.warning(
                f"Attempted to get key '{key}' from non-existent section '[{section}]'. Using fallback: {fallback}"
            )
            return fallback
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except ValueError:
            value_from_config = self.config.get(section, key, fallback=None)
            default_value_str = self.defaults.get(section, {}).get(key)
            if value_from_config is not None and str(value_from_config) != str(
                default_value_str
            ):
                log.warning(
                    f"Config value '{key}' = '{value_from_config}' in section '[{section}]' is not a valid float. Trying fallback/default."
                )
            if fallback is not None:
                return fallback
            try:
                return float(default_value_str)
            except (ValueError, TypeError, AttributeError):
                log.error(
                    f"Could not determine a valid float fallback/default for [{section}]/{key}. Returning None."
                )
                return None

    def getboolean(
        self, section: str, key: str, fallback: Optional[bool] = None
    ) -> Optional[bool]:
        """Gets a boolean value from the configuration."""
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except ValueError:
            value_from_file = self.config.get(section, key, fallback=None)
            default_value_str = self.defaults.get(section, {}).get(key)
            if value_from_file is not None and str(value_from_file) != str(
                default_value_str
            ):
                log.warning(
                    f"Config value '{key}' = '{value_from_file}' in section '[{section}]' is not a valid boolean. Using fallback: {fallback}"
                )
            if fallback is not None:
                return fallback
            try:
                default_val = default_value_str
                if isinstance(default_val, bool):
                    return default_val
                elif isinstance(default_val, str):
                    if default_val.lower() in ["true", "yes", "on", "1"]:
                        return True
                    elif default_val.lower() in ["false", "no", "off", "0"]:
                        return False
                elif isinstance(default_val, int):
                    return default_val != 0
                raise ValueError
            except (ValueError, TypeError, AttributeError):
                log.error(
                    f"Could not determine a valid boolean fallback for [{section}]/{key}"
                )
                return None
