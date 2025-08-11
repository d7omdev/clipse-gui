# Makefile for Clipse GUI

# --- Variables ---
PYTHON := python3
APP_NAME := clipse-gui
APP_SCRIPT := $(APP_NAME).py
PACKAGE_DIR := clipse_gui
BUILD_DIR := dist
ICON_NAME := $(APP_NAME)
ICON_FILE := $(ICON_NAME).png
DESKTOP_FILE := $(APP_NAME).desktop

PREFIX ?= /usr/local
BIN_DIR := $(PREFIX)/bin
SHARE_DIR := $(PREFIX)/share
APP_DIR := $(SHARE_DIR)/$(APP_NAME)
ICON_DEST_DIR := $(SHARE_DIR)/icons/hicolor/128x128/apps
ICON_CACHE_DIR := $(SHARE_DIR)/icons/hicolor
DESKTOP_DEST_DIR := $(SHARE_DIR)/applications
TMP_DESKTOP_FILE := /tmp/$(DESKTOP_FILE)

NUITKA_DIST_DIR := $(APP_NAME).dist
NUITKA_BINARY := $(APP_NAME).bin

NUITKA_OPTS := \
  --standalone \
  --output-dir=$(BUILD_DIR) \
  --remove-output \
  --include-package=$(PACKAGE_DIR) \
  --include-package=gi \
  --include-module=gi._gi \
  --include-module=gi._propertyhelper \
  --include-module=gi._constants \
  --include-module=gi._signalhelper \
  --include-module=gi._enum \
  --include-module=gi._error \
  --include-module=asyncio

.DEFAULT_GOAL := help

.PHONY: help run nuitka install uninstall clean bump

help:
	@echo "Available targets:"
	@echo "  run        - Run the Clipse GUI from source"
	@echo "  nuitka     - Build a standalone binary using Nuitka"
	@echo "  install    - Install built binary and assets system-wide"
	@echo "  uninstall  - Uninstall the application"
	@echo "  clean      - Clean build and temp files"
	@echo "  bump       - Interactively bump version (major/minor/patch)"

run:
	@echo "Running Clipse GUI..."
	@$(PYTHON) $(APP_SCRIPT)

watch:
	@echo "Starting Clipse GUI in watch mode..."
	watchmedo auto-restart --directory=. --pattern="*.py" --recursive -- \
		$(PYTHON) $(APP_SCRIPT)

nuitka:
	@echo "Building standalone app using Nuitka..."
	$(PYTHON) -m nuitka $(NUITKA_OPTS) $(APP_SCRIPT)

install: nuitka
	@echo "Installing $(APP_NAME)..."
	@sudo install -d "$(APP_DIR)"
	@sudo cp -r "$(BUILD_DIR)/$(NUITKA_DIST_DIR)/." "$(APP_DIR)/"

	@sudo ln -sf "$(APP_DIR)/$(NUITKA_BINARY)" "$(BIN_DIR)/$(APP_NAME)"

	@if [ -f "$(ICON_FILE)" ]; then \
		echo "Installing icon..."; \
		sudo install -Dm644 "$(ICON_FILE)" "$(ICON_DEST_DIR)/$(ICON_NAME).png"; \
		if [ -f "$(ICON_CACHE_DIR)/index.theme" ]; then \
			sudo gtk-update-icon-cache "$(ICON_CACHE_DIR)"; \
		else \
			echo "Skipping icon cache update: index.theme not found in $(ICON_CACHE_DIR)"; \
		fi; \
	fi

	@echo "Creating .desktop file..."
	@mkdir -p "$(DESKTOP_DEST_DIR)"
	@printf "%s\n" \
		"[Desktop Entry]" \
		"Version=0.1.5" \
		"Type=Application" \
		"Name=Clipse GUI" \
		"GenericName=Clipboard Manager" \
		"Comment=GTK Clipboard Manager" \
		"Exec=$(BIN_DIR)/$(APP_NAME)" \
		"Icon=$(ICON_NAME)" \
		"Terminal=false" \
		"Categories=Utility;GTK;" \
		"StartupNotify=true" \
		"StartupWMClass=org.d7om.ClipseGUI" > "$(TMP_DESKTOP_FILE)"

	@sudo install -Dm644 "$(TMP_DESKTOP_FILE)" "$(DESKTOP_DEST_DIR)/$(DESKTOP_FILE)"
	@rm -f "$(TMP_DESKTOP_FILE)"

	@echo "Updating desktop database..."
	@sudo update-desktop-database -q "$(DESKTOP_DEST_DIR)"

uninstall:
	@echo "Uninstalling $(APP_NAME)..."
	@sudo rm -f "$(BIN_DIR)/$(APP_NAME)"
	@sudo rm -rf "$(APP_DIR)"
	@sudo rm -f "$(DESKTOP_DEST_DIR)/$(DESKTOP_FILE)"

	@if [ -f "$(ICON_DEST_DIR)/$(ICON_NAME).png" ]; then \
		echo "Removing icon..."; \
		sudo rm -f "$(ICON_DEST_DIR)/$(ICON_NAME).png"; \
		if [ -f "$(ICON_CACHE_DIR)/index.theme" ]; then \
			sudo gtk-update-icon-cache "$(ICON_CACHE_DIR)"; \
		else \
			echo "Skipping icon cache update: index.theme not found in $(ICON_CACHE_DIR)"; \
		fi; \
	fi

	@echo "Updating desktop database..."
	@sudo update-desktop-database -q "$(DESKTOP_DEST_DIR)"

clean:
	@echo "Cleaning build files..."
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@rm -rf build/ dist/ *.spec *.build/ "$(TMP_DESKTOP_FILE)"

bump:
	@echo "Bumping version..."
	@$(PYTHON) bump_version.py

