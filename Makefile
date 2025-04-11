# Makefile for clipse-gui

# --- Variables ---
PYTHON := python3
APP_NAME := clipse-gui
APP_SCRIPT := clipse-gui.py
PACKAGE_DIR := clipse_gui
BUILD_DIR := dist
ICON_NAME := clipse-gui
ICON_FILE := $(ICON_NAME).png
# Filename for the installed desktop file (NO trailing space)
GENERATED_DESKTOP_FILENAME := $(APP_NAME).desktop

# Installation directories (standard locations)
PREFIX ?= /usr/local
BIN_DIR := $(PREFIX)/bin
SHARE_DIR := $(PREFIX)/share
APP_DIR := $(SHARE_DIR)/$(APP_NAME)
ICON_DEST_DIR := $(SHARE_DIR)/icons/hicolor/128x128/apps
DESKTOP_DEST_DIR := $(SHARE_DIR)/applications

# Nuitka settings
NUITKA_OUTPUT_BASE_NAME := $(APP_SCRIPT:.py=)
NUITKA_DIST_DIR := $(NUITKA_OUTPUT_BASE_NAME).dist
NUITKA_BINARY := $(NUITKA_OUTPUT_BASE_NAME).bin

# Nuitka options
NUITKA_OPTS := --standalone --output-dir=$(BUILD_DIR) --remove-output \
	--include-package=clipse_gui \
	--include-package=gi \
	--include-module=gi._gi \
	--include-module=gi._propertyhelper \
	--include-module=gi._constants \
	--include-module=gi._signalhelper \
	--include-module=gi._enum \
	--include-module=gi._error \
	--include-module=asyncio

# Temporary file for generated desktop entry
TMP_DESKTOP_FILE := /tmp/$(GENERATED_DESKTOP_FILENAME)

# --- Targets ---

.PHONY: help run nuitka install uninstall clean

# Default target: Show help
help:
	@echo "Available targets:"
	@echo "  run        - Run the Clipse GUI application directly from source"
	@echo "  nuitka     - Build a standalone folder using Nuitka (in ./dist/)"
	@echo "  install    - Build with Nuitka and install system-wide to $(PREFIX) (requires sudo)"
	@echo "  uninstall  - Uninstall the system-wide application from $(PREFIX) (requires sudo)"
	@echo "  clean      - Remove temporary Python/Nuitka files and build artifacts"
	@echo "  help       - Show this help message"

# Run the application directly from source
run:
	@echo "Starting Clipse GUI from source..."
	$(PYTHON) $(APP_SCRIPT)

# Build the application using Nuitka
nuitka:
	@echo "Building standalone application using Nuitka..."
	@echo "NOTE: Ensure Nuitka is installed (pip install nuitka) and a C compiler is present."
	$(PYTHON) -m nuitka $(NUITKA_OPTS) $(APP_SCRIPT)
	@echo "Nuitka build complete. Application folder is in $(BUILD_DIR)/$(NUITKA_DIST_DIR)/"

# Install the Nuitka-built application system-wide
install: nuitka # Depends on the Nuitka build
	@echo "Installing Nuitka-built $(APP_NAME) to $(PREFIX)... (Requires sudo)"
	@if [ ! -d "$(BUILD_DIR)/$(NUITKA_DIST_DIR)" ]; then \
		echo "Error: Nuitka build directory '$(BUILD_DIR)/$(NUITKA_DIST_DIR)' not found. Run 'make nuitka' first."; \
		exit 1; \
	fi
	# --- Install Icon --- (Ensure ICON_FILE has no trailing space)
	@if [ -f "$(ICON_FILE)" ]; then \
		echo "Installing icon..."; \
		sudo install -Dm644 "$(ICON_FILE)" "$(ICON_DEST_DIR)/$(ICON_NAME).png"; \
		echo "Updating icon cache..."; \
		sudo gtk-update-icon-cache -f -t "$(SHARE_DIR)/icons/hicolor" || echo "Warning: gtk-update-icon-cache command failed."; \
	else \
		echo "Warning: Icon file '$(ICON_FILE)' not found. Skipping icon installation."; \
	fi
	# --- Install Application Files ---
	@echo "Installing application files from $(BUILD_DIR)/$(NUITKA_DIST_DIR)..."
	sudo install -d "$(APP_DIR)"
	sudo cp -r "$(BUILD_DIR)/$(NUITKA_DIST_DIR)/." "$(APP_DIR)/"
	# --- Create Binary Symlink ---
	sudo ln -sf "$(APP_DIR)/$(NUITKA_BINARY)" "$(BIN_DIR)/$(APP_NAME)"
	# --- Generate and Install Desktop File ---
	@echo "Generating and installing desktop entry..."
	@# Create the destination directory if it doesn't exist
	sudo install -d "$(DESKTOP_DEST_DIR)"
	@# Generate content using printf to a temporary file (safer for multi-line)
	@printf "%s\n" \
		"[Desktop Entry]" \
		"Version=1.0" \
		"Type=Application" \
		"Name=Clipse GUI" \
		"GenericName=Clipboard History Viewer" \
		"Comment=Graphical interface for the clipse clipboard manager" \
		"Exec=$(BIN_DIR)/$(APP_NAME)" \
		"Icon=$(ICON_NAME)" \
		"Terminal=false" \
		"Categories=Utility;GTK;" \
		"Keywords=clipboard;history;paste;gtk;clipse;" \
		"StartupNotify=true" \
		"StartupWMClass=org.d7om.ClipseGUI" \
		> $(TMP_DESKTOP_FILE)
	@# Add Icon line only if icon file exists
	@if [ ! -f "$(ICON_FILE)" ]; then \
		sed -i '/^Icon=/d' $(TMP_DESKTOP_FILE); \
	fi
	@# Install the generated temporary file with sudo and correct permissions
	sudo install -Dm644 $(TMP_DESKTOP_FILE) "$(DESKTOP_DEST_DIR)/$(GENERATED_DESKTOP_FILENAME)"
	@# Clean up temporary file
	rm -f $(TMP_DESKTOP_FILE)
	@# Update Desktop Database
	echo "Updating desktop database..."; \
	sudo update-desktop-database -q "$(DESKTOP_DEST_DIR)" || echo "Warning: update-desktop-database command failed."; \

	@echo "Installation complete. You can now run '$(APP_NAME)' from your terminal or application menu."

# Uninstall the application
uninstall:
	@echo "Uninstalling $(APP_NAME) from $(PREFIX)... (Requires sudo)"
	sudo rm -f "$(BIN_DIR)/$(APP_NAME)"
	sudo rm -rf "$(APP_DIR)"
	@if [ -f "$(ICON_DEST_DIR)/$(ICON_NAME).png" ]; then \
		echo "Removing icon..."; \
		sudo rm -f "$(ICON_DEST_DIR)/$(ICON_NAME).png"; \
		echo "Updating icon cache..."; \
		sudo gtk-update-icon-cache -f -t "$(SHARE_DIR)/icons/hicolor" || echo "Warning: gtk-update-icon-cache command failed."; \
	else \
		echo "Icon not found in install location. Skipping removal."; \
	fi
	# Remove generated desktop file by its installed name (NO trailing space)
	@if [ -f "$(DESKTOP_DEST_DIR)/$(GENERATED_DESKTOP_FILENAME)" ]; then \
		echo "Removing desktop entry..."; \
		sudo rm -f "$(DESKTOP_DEST_DIR)/$(GENERATED_DESKTOP_FILENAME)"; \
		echo "Updating desktop database..."; \
		sudo update-desktop-database -q "$(DESKTOP_DEST_DIR)" || echo "Warning: update-desktop-database command failed."; \
	else \
		echo "Desktop entry not found in install location. Skipping removal."; \
	fi
	@echo "Uninstallation complete."

# Clean temporary files and build/dist artifacts
clean:
	@echo "Cleaning up temporary files and build artifacts..."
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	# Clean PyInstaller stuff if present
	rm -rf build/ dist/ *.spec
	# Clean Nuitka stuff
	rm -rf *.build/ $(BUILD_DIR)/$(NUITKA_DIST_DIR)/ # Clean specific Nuitka output dir
	# Clean tmp desktop file just in case
	rm -f $(TMP_DESKTOP_FILE)
	@echo "Cleanup complete."

# --- Default Goal ---
.DEFAULT_GOAL := help
