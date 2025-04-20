import configparser
import os
import logging
from typing import Optional, Any

log = logging.getLogger(__name__)


class ConfigManager:
    """Handles reading configuration from an INI file."""

    def __init__(self, config_path: str, default_settings: dict):
        """
        Initializes the ConfigManager.

        Args:
            config_path: The full path to the settings.ini file.
            default_settings: A dictionary containing default values.
                              Format: {'Section': {'key': 'value', ...}, ...}
        """
        self.config_path = config_path
        self.defaults = default_settings
        self.config = configparser.ConfigParser(interpolation=None)
        self.load_error_message = None
        self._load_config()

    def _load_config(self):
        """Loads configuration from the INI file."""
        for section, options in self.defaults.items():
            if not self.config.has_section(section):
                self.config.add_section(section)

        self.config.read_dict(self.defaults)

        if os.path.exists(self.config_path):
            try:
                read_files = self.config.read(self.config_path, encoding="utf-8")
                if read_files:
                    log.info(
                        f"Successfully loaded configuration from: {self.config_path}"
                    )
                else:
                    log.warning(
                        f"Configuration file exists but could not be read/parsed: {self.config_path}"
                    )
                    self.load_error_message = (
                        f"Configuration file exists but could not be read or is empty:\n"
                        f"{self.config_path}\n\n"
                        f"Using default settings. The file will be overwritten with defaults if possible."
                    )

            except configparser.Error as e:
                error_msg = f"Error parsing configuration file {self.config_path}: {e}"
                log.error(error_msg)
                self.load_error_message = (
                    f"Error parsing configuration file:\n{self.config_path}\n\n"
                    f"Details: {e}\n\n"
                    f"Using default settings. The file will be overwritten with defaults if possible."
                )

            except Exception as e:
                error_msg = f"Unexpected error reading config {self.config_path}: {e}"
                log.error(error_msg)
                self.load_error_message = (
                    f"Unexpected error reading configuration file:\n{self.config_path}\n\n"
                    f"Details: {e}\n\n"
                    f"Using default settings."
                )
        else:
            log.info(
                f"Configuration file not found: {self.config_path}. Creating with defaults."
            )
            self._ensure_config_file_exists()  # Create the default file

    def _ensure_config_file_exists(self):
        """Creates or updates the configuration file with current defaults if missing/problematic."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as configfile:
                configfile.write("# Clipse GUI Configuration File\n")
                configfile.write(
                    "# Settings here override the application defaults.\n\n"
                )
                temp_config_to_write = configparser.ConfigParser(interpolation=None)
                temp_config_to_write.read_dict(self.defaults)
                for section in self.config.sections():
                    if (
                        section == configparser.DEFAULTSECT
                        and section not in self.defaults
                    ):
                        continue
                    if not temp_config_to_write.has_section(section):
                        temp_config_to_write.add_section(section)
                    for key, value in self.config.items(section):
                        temp_config_to_write.set(section, key, value)

                temp_config_to_write.write(configfile)
            log.info(
                f"Ensured configuration file exists with defaults: {self.config_path}"
            )
        except OSError as e:
            error_msg = (
                f"Failed to create/update configuration file {self.config_path}: {e}"
            )
            log.error(error_msg)
            if not self.load_error_message:
                self.load_error_message = error_msg
        except Exception as e:
            error_msg = f"Unexpected error writing config file {self.config_path}: {e}"
            log.error(error_msg)
            if not self.load_error_message:
                self.load_error_message = error_msg

    def get(
        self, section: str, key: str, fallback: Optional[Any] = None
    ) -> Optional[str]:
        """Gets a string value from the configuration."""
        return self.config.get(section, key, fallback=fallback)

    def getint(
        self, section: str, key: str, fallback: Optional[int] = None
    ) -> Optional[int]:
        """Gets an integer value from the configuration."""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except ValueError:
            value_from_file = self.config.get(section, key, fallback=None)
            default_value_str = self.defaults.get(section, {}).get(key)

            if value_from_file is not None and str(value_from_file) != str(
                default_value_str
            ):
                log.warning(
                    f"Config value '{key}' = '{value_from_file}' in section '[{section}]' is not a valid integer. Using fallback: {fallback}"
                )

            if fallback is not None:
                return fallback
            try:
                return int(default_value_str)
            except (ValueError, TypeError, AttributeError):
                log.error(
                    f"Could not determine a valid integer fallback for [{section}]/{key}"
                )
                return None

    def getfloat(
        self, section: str, key: str, fallback: Optional[float] = None
    ) -> Optional[float]:
        """Gets a float value from the configuration."""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except ValueError:
            value_from_file = self.config.get(section, key, fallback=None)
            default_value_str = self.defaults.get(section, {}).get(key)
            if value_from_file is not None and str(value_from_file) != str(
                default_value_str
            ):
                log.warning(
                    f"Config value '{key}' = '{value_from_file}' in section '[{section}]' is not a valid float. Using fallback: {fallback}"
                )
            if fallback is not None:
                return fallback
            try:
                return float(default_value_str)
            except (ValueError, TypeError, AttributeError):
                log.error(
                    f"Could not determine a valid float fallback for [{section}]/{key}"
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

