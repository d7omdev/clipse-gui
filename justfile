# Clipse GUI - Just command runner
#
# Available recipes: run `just` or `just --list`
# ============================================================================
# Settings
# ============================================================================
# Load .env file if present

set dotenv-load := true

# Use bash for recipes (better for complex scripts)

set shell := ["bash", "-euo", "pipefail", "-c"]

# Windows-specific shell fallback

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Allow positional arguments in recipes

set positional-arguments := true

# ============================================================================
# Variables
# ============================================================================
# Application metadata

export APP_NAME := "clipse-gui"
export APP_SCRIPT := APP_NAME + ".py"
export PACKAGE_DIR := "clipse_gui"
export ICON_FILE := APP_NAME + ".png"

# Installation paths (configurable via env vars)

export PREFIX := env("PREFIX", "/usr")
export BIN_DIR := PREFIX / "bin"
export SHARE_DIR := PREFIX / "share"
export APP_DIR := "/opt/" + APP_NAME
export ICON_DEST_DIR := SHARE_DIR / "icons/hicolor/128x128/apps"
export ICON_CACHE_DIR := SHARE_DIR / "icons/hicolor"
export DESKTOP_DEST_DIR := SHARE_DIR / "applications"

# Build directories

export BUILD_DIR := "dist"
export NUITKA_DIST_DIR := APP_NAME + ".dist"
export NUITKA_BINARY := APP_NAME

# Python configuration - auto-detects venv, uses uv to bootstrap Python 3.13 if needed

export PYTHON := if path_exists("venv/bin/python") == "true" { "venv/bin/python" } else if path_exists(".venv/bin/python") == "true" { ".venv/bin/python" } else if env("NO_UV_BOOTSTRAP", "") == "" { "uv run --python 3.13 --no-project -- python3" } else { env("PYTHON", "python3") }

# Virtual environment activation command (empty if using system python)

export VENV_ACTIVATE := if path_exists("venv/bin/activate") == "true" { "source venv/bin/activate && " } else if path_exists(".venv/bin/activate") == "true" { "source .venv/bin/activate && " } else { "" }

# Nuitka build options

NUITKA_OPTS := "--onefile --output-dir=" + BUILD_DIR + " --remove-output --include-package=" + PACKAGE_DIR + " --follow-imports --nofollow-import-to=*.tests --assume-yes-for-downloads"

# Current version extracted from source

VERSION := `grep -oP '__version__ = "\K[^"]+' clipse_gui/__init__.py 2>/dev/null || echo "unknown"`

# Colors for output (disable if NO_COLOR is set)

BOLD := `tput bold 2>/dev/null || echo ""`
GREEN := `tput setaf 2 2>/dev/null || echo ""`
YELLOW := `tput setaf 3 2>/dev/null || echo ""`
BLUE := `tput setaf 4 2>/dev/null || echo ""`
RESET := `tput sgr0 2>/dev/null || echo ""`

# ============================================================================
# Default Recipe
# ============================================================================

# Show available recipes (default)
default:
    @just --list --unsorted

# ============================================================================
# Development Recipes (group: 'dev')
# ============================================================================

# Run the Clipse GUI from source (group: 'dev')
[group('dev')]
run *args:
    @echo "{{ GREEN }}-> Running {{ APP_NAME }} (v{{ VERSION }})...{{ RESET }}"
    {{ VENV_ACTIVATE }}{{ PYTHON }} {{ APP_SCRIPT }} {{ args }}

# Run with debug logging enabled (group: 'dev')
[group('dev')]
debug *args:
    @echo "{{ GREEN }}-> Running {{ APP_NAME }} in DEBUG mode...{{ RESET }}"
    CLIPSE_DEBUG=1 {{ VENV_ACTIVATE }}{{ PYTHON }} {{ APP_SCRIPT }} {{ args }}

# Watch for file changes and auto-restart - requires watchmedo (group: 'dev')
[group('dev')]
watch:
    @echo "{{ YELLOW }}-> Starting watch mode...{{ RESET }}"
    @if ! command -v watchmedo &> /dev/null; then \
        echo "{{ YELLOW }}⚠ watchmedo not found. Install with: pip install watchdog{{ RESET }}"; \
        exit 1; \
    fi
    watchmedo auto-restart --directory=. --pattern="*.py" --recursive -- \
        {{ PYTHON }} {{ APP_SCRIPT }}

# Setup development environment - create venv, install deps (group: 'dev')
[group('dev')]
setup:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "{{ BLUE }}-> Setting up development environment...{{ RESET }}"
    if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
    pip install ruff pyright watchdog
    echo -e "{{ GREEN }}✓ Development environment ready!{{ RESET }}"

# Update dependencies (group: 'dev')
[group('dev')]
update-deps:
    @echo "{{ BLUE }}-> Updating dependencies...{{ RESET }}"
    {{ VENV_ACTIVATE }}pip install --upgrade -r requirements.txt

# ============================================================================
# Quality Assurance Recipes (group: 'qa')
# ============================================================================

# Run all quality checks - lint + type-check (group: 'qa')
[group('qa')]
check: lint type-check
    @echo "{{ GREEN }}✓ All quality checks passed!{{ RESET }}"

# Run linting with ruff (group: 'qa')
[group('qa')]
lint:
    @echo "{{ BLUE }}-> Running ruff linter...{{ RESET }}"
    {{ VENV_ACTIVATE }}ruff check .

# Run linting and auto-fix issues (group: 'qa')
[group('qa')]
lint-fix:
    @echo "{{ BLUE }}-> Running ruff linter (with auto-fix)...{{ RESET }}"
    {{ VENV_ACTIVATE }}ruff check . --fix

# Run type checking with pyright (group: 'qa')
[group('qa')]
type-check:
    @echo "{{ BLUE }}-> Running pyright type checker...{{ RESET }}"
    {{ VENV_ACTIVATE }}pyright

# Format code with ruff (group: 'qa')
[group('qa')]
format:
    @echo "{{ BLUE }}-> Formatting code...{{ RESET }}"
    {{ VENV_ACTIVATE }}ruff format .

# Check code formatting without making changes (group: 'qa')
[group('qa')]
format-check:
    @echo "{{ BLUE }}-> Checking code formatting...{{ RESET }}"
    {{ VENV_ACTIVATE }}ruff format --check .

# Run full quality pipeline - format, lint, type-check (group: 'qa')
[group('qa')]
qa: format lint type-check
    @echo "{{ GREEN }}✓ Quality assurance complete!{{ RESET }}"

# ============================================================================
# Build Recipes (group: 'build')
# ============================================================================

# Ensure Python 3.13 venv exists using uv (downloads Python if needed)
[group('build')]
_ensure-python:
    #!/usr/bin/env bash
    set -euo pipefail
    PYTHON_VERSION=$(venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "none")
    if [ ! -d "venv" ] || [ "$PYTHON_VERSION" != "3.13" ]; then
        echo "{{ YELLOW }}-> Creating venv with Python 3.13 (downloading if needed)...{{ RESET }}"
        rm -rf venv
        uv venv --python 3.13 venv
    fi
    if ! venv/bin/python -c "import nuitka" 2>/dev/null; then
        echo "{{ YELLOW }}-> Installing nuitka...{{ RESET }}"
        uv pip install nuitka --python venv/bin/python
    fi
    if ! venv/bin/python -c "import gi" 2>/dev/null; then
        echo "{{ YELLOW }}-> Installing PyGObject...{{ RESET }}"
        uv pip install PyGObject --python venv/bin/python
    fi

# Build standalone binary using Nuitka (group: 'build')
[group('build')]
build: clean-build _ensure-python
    @echo "{{ BLUE }}-> Building standalone binary with Nuitka...{{ RESET }}"
    @echo "{{ YELLOW }}  This may take a few minutes...{{ RESET }}"
    venv/bin/python -m nuitka {{ NUITKA_OPTS }} {{ APP_SCRIPT }}
    @if [ -f "{{ BUILD_DIR }}/{{ APP_NAME }}.bin" ]; then \
        mv "{{ BUILD_DIR }}/{{ APP_NAME }}.bin" "{{ BUILD_DIR }}/{{ APP_NAME }}"; \
    fi
    @echo "{{ GREEN }}✓ Build complete: {{ BUILD_DIR }}/{{ APP_NAME }}{{ RESET }}"

# Build and verify the binary works (group: 'build')
[group('build')]
build-verify: build
    @echo "{{ BLUE }}-> Verifying build...{{ RESET }}"
    @if [ -f "{{ BUILD_DIR }}/{{ APP_NAME }}" ]; then \
        echo "{{ GREEN }}✓ Binary exists and is ready for installation{{ RESET }}"; \
        ls -lh {{ BUILD_DIR }}/{{ APP_NAME }}; \
    else \
        echo "{{ YELLOW }}✗ Binary not found at expected location{{ RESET }}"; \
        exit 1; \
    fi

# ============================================================================
# Installation Recipes (group: 'install')
# ============================================================================

# Install binary and assets system-wide - requires sudo (group: 'install')
[group('install')]
install: build verify-prefix
    #!/usr/bin/env bash
    set -euo pipefail
    echo "{{ BLUE }}-> Installing {{ APP_NAME }} v{{ VERSION }}...{{ RESET }}"

    # Remove old installation and copy new one to /opt
    echo "Installing to {{ APP_DIR }}..."
    sudo rm -rf "{{ APP_DIR }}"
    sudo mkdir -p "{{ APP_DIR }}"
    sudo cp "{{ BUILD_DIR }}/{{ APP_NAME }}" "{{ APP_DIR }}/{{ APP_NAME }}"
    sudo chmod +x "{{ APP_DIR }}/{{ APP_NAME }}"

    # Create symlink
    echo "Creating symlink..."
    sudo ln -sf "{{ APP_DIR }}/{{ APP_NAME }}" "{{ BIN_DIR }}/{{ APP_NAME }}"

    # Install icon if present
    if [ -f "{{ ICON_FILE }}" ]; then
        echo "Installing icon..."
        sudo install -Dm644 "{{ ICON_FILE }}" "{{ ICON_DEST_DIR }}/{{ APP_NAME }}.png"
        if [ -f "{{ ICON_CACHE_DIR }}/index.theme" ]; then
            sudo gtk-update-icon-cache "{{ ICON_CACHE_DIR }}" 2>/dev/null || true
        fi
    fi

    # Generate and install desktop file
    echo "Installing desktop entry..."
    just _generate-desktop | sudo tee "{{ DESKTOP_DEST_DIR }}/{{ APP_NAME }}.desktop" > /dev/null
    sudo chmod 644 "{{ DESKTOP_DEST_DIR }}/{{ APP_NAME }}.desktop"

    # Update desktop database
    sudo update-desktop-database -q "{{ DESKTOP_DEST_DIR }}" 2>/dev/null || true

    echo -e "{{ GREEN }}✓ Installation complete!{{ RESET }}"
    echo "  Run with: {{ BOLD }}{{ APP_NAME }}{{ RESET }} or from your applications menu"

# Uninstall the application [confirm] (group: 'install')
[confirm("Are you sure you want to uninstall clipse-gui?")]
[group('install')]
uninstall:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "{{ YELLOW }}-> Uninstalling {{ APP_NAME }}...{{ RESET }}"

    sudo rm -f "{{ BIN_DIR }}/{{ APP_NAME }}"
    sudo rm -rf "{{ APP_DIR }}"
    sudo rm -f "{{ DESKTOP_DEST_DIR }}/{{ APP_NAME }}.desktop"

    if [ -f "{{ ICON_DEST_DIR }}/{{ APP_NAME }}.png" ]; then
        echo "Removing icon..."
        sudo rm -f "{{ ICON_DEST_DIR }}/{{ APP_NAME }}.png"
        if [ -f "{{ ICON_CACHE_DIR }}/index.theme" ]; then
            sudo gtk-update-icon-cache "{{ ICON_CACHE_DIR }}" 2>/dev/null || true
        fi
    fi

    sudo update-desktop-database -q "{{ DESKTOP_DEST_DIR }}" 2>/dev/null || true
    echo "{{ GREEN }}✓ Uninstalled successfully{{ RESET }}"

# Install git hooks for development (group: 'install')
[group('install')]
install-hooks:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "{{ BLUE }}-> Installing git hooks...{{ RESET }}"
    if [ -f ".githooks/pre-commit" ]; then
        cp .githooks/pre-commit .git/hooks/pre-commit
        chmod +x .git/hooks/pre-commit
        echo "{{ GREEN }}✓ Pre-commit hook installed{{ RESET }}"
    else
        echo "{{ YELLOW }}⚠ No hooks found in .githooks/{{ RESET }}"
    fi

# Dry-run install - show what would be installed (group: 'install')
[group('install')]
dry-install: build
    @echo "{{ BLUE }}-> Dry-run install (would install to {{ PREFIX }}):{{ RESET }}"
    @echo "  Binary: {{ BUILD_DIR }}/{{ NUITKA_BINARY }} → {{ BIN_DIR }}/{{ APP_NAME }}"
    @echo "  Icon:   {{ ICON_FILE }} → {{ ICON_DEST_DIR }}/{{ APP_NAME }}.png"
    @echo "  Desktop: {{ DESKTOP_DEST_DIR }}/{{ APP_NAME }}.desktop"
    @echo ""
    @echo "{{ YELLOW }}Run 'just install' to perform actual installation{{ RESET }}"

# ============================================================================
# Version Management Recipes (group: 'version')
# ============================================================================

# Show current version (group: 'version')
[group('version')]
version:
    @echo "{{ BOLD }}{{ APP_NAME }}{{ RESET }} v{{ VERSION }}"

# Show version in different formats (group: 'version')
[group('version')]
version-full:
    #!/usr/bin/env bash
    echo "{{ BOLD }}{{ APP_NAME }}{{ RESET }}"
    echo "  Version:     v{{ VERSION }}"
    echo "  Git branch:  $(git branch --show-current 2>/dev/null || echo 'n/a')"
    echo "  Git commit:  $(git rev-parse --short HEAD 2>/dev/null || echo 'n/a')"
    echo "  Build date:  $(date -Iseconds)"

# Calculate next versions without changing anything (group: 'version')
[group('version')]
version-preview:
    #!/usr/bin/env bash
    current="{{ VERSION }}"
    IFS='.' read -r major minor patch <<< "$current"
    echo "{{ BOLD }}Current:{{ RESET }} v$current"
    echo ""
    echo "{{ BOLD }}Next versions:{{ RESET }}"
    echo "  major: v$((major + 1)).0.0"
    echo "  minor: v$major.$((minor + 1)).0"
    echo "  patch: v$major.$minor.$((patch + 1))"

# Bump version - usage: just bump [major|minor|patch] [--commit] [--tag] [--dry-run] (group: 'version')
[group('version')]
bump bump_type="" *flags="":
    #!/usr/bin/env bash
    set -euo pipefail

    # Parse flags
    commit_flag=""
    tag_flag=""
    dry_run=""
    for flag in {{ flags }}; do
        case "$flag" in
            --commit|-c) commit_flag="1" ;;
            --tag|-t) tag_flag="1" ;;
            --dry-run|-d) dry_run="1" ;;
        esac
    done

    # Validate bump type
    valid_types="major minor patch"
    if [ -z "{{ bump_type }}" ]; then
        echo "{{ YELLOW }}No bump type specified. Use: just bump <major|minor|patch>{{ RESET }}"
        just version-preview
        exit 0
    fi

    if [[ ! " $valid_types " =~ " {{ bump_type }} " ]]; then
        echo "{{ YELLOW }}Error: Invalid bump type '{{ bump_type }}'{{ RESET }}"
        echo "Valid types: major, minor, patch"
        exit 1
    fi

    # Calculate new version
    current="{{ VERSION }}"
    IFS='.' read -r major minor patch <<< "$current"

    case "{{ bump_type }}" in
        major) new_version="$((major + 1)).0.0" ;;
        minor) new_version="$major.$((minor + 1)).0" ;;
        patch) new_version="$major.$minor.$((patch + 1))" ;;
    esac

    echo "{{ BLUE }}-> Bumping version...{{ RESET }}"
    echo "  Current: v$current"
    echo "  New:     v$new_version ({{ bump_type }})"

    # Check for uncommitted changes
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        echo ""
        echo "{{ YELLOW }}⚠ Warning: You have uncommitted changes{{ RESET }}"
        git status --short
        echo ""
        if [ -z "$dry_run" ]; then
            read -p "Continue anyway? (y/N): " confirm
            if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
                echo "Cancelled"
                exit 0
            fi
        fi
    fi

    # Dry run mode
    if [ -n "$dry_run" ]; then
        echo ""
        echo "{{ BLUE }}[DRY RUN] Would update:{{ RESET }}"
        echo "  - clipse_gui/__init__.py: __version__ = \"$new_version\""
        echo "  - Makefile: Version=$new_version"
        if [ -n "$commit_flag" ]; then
            echo "  - Git commit: 'chore: bump version to v$new_version'"
        fi
        if [ -n "$tag_flag" ]; then
            echo "  - Git tag: v$new_version"
        fi
        exit 0
    fi

    # Confirm
    echo ""
    read -p "Proceed with version bump? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 0
    fi

    # Update __init__.py
    sed -i "s/__version__ = \"[^\"]*/__version__ = \"$new_version/" clipse_gui/__init__.py
    echo "{{ GREEN }}✓ Updated clipse_gui/__init__.py{{ RESET }}"

    # Update Makefile desktop entry
    if [ -f "Makefile" ]; then
        sed -i "s/Version=[^\\\"]*/Version=$new_version/g" Makefile
        echo "{{ GREEN }}✓ Updated Makefile{{ RESET }}"
    fi

    # Git commit
    if [ -n "$commit_flag" ]; then
        git add clipse_gui/__init__.py Makefile 2>/dev/null || true
        git commit -m "chore: bump version to v$new_version"
        echo "{{ GREEN }}✓ Created commit{{ RESET }}"
    fi

    # Git tag
    if [ -n "$tag_flag" ]; then
        git tag -a "v$new_version" -m "Release v$new_version"
        echo "{{ GREEN }}✓ Created tag v$new_version{{ RESET }}"
    fi

    echo ""
    echo "{{ GREEN }}✓ Version bumped to v$new_version{{ RESET }}"
    if [ -n "$commit_flag" ] && [ -z "$tag_flag" ]; then
        echo "  Run '{{ BOLD }}git push{{ RESET }}' to publish"
    elif [ -n "$tag_flag" ]; then
        echo "  Run '{{ BOLD }}git push && git push --tags{{ RESET }}' to publish"
    fi

# Quick bump patch version (no confirmation) (group: 'version')
[group('version')]
bump-patch *flags:
    @just bump patch {{ flags }}

# Quick bump minor version (no confirmation) (group: 'version')
[group('version')]
bump-minor *flags:
    @just bump minor {{ flags }}

# Quick bump major version (no confirmation) (group: 'version')
[group('version')]
bump-major *flags:
    @just bump major {{ flags }}

# Show git log since last version tag (group: 'version')
[group('version')]
changelog:
    #!/usr/bin/env bash
    latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    if [ -n "$latest_tag" ]; then
        echo "{{ BOLD }}Changes since $latest_tag:{{ RESET }}"
        git log "$latest_tag"..HEAD --oneline --no-decorate
    else
        echo "{{ BOLD }}All commits (no tags found):{{ RESET }}"
        git log --oneline --no-decorate -20
    fi

# Show suggested version bump based on commits (group: 'version')
[group('version')]
version-suggest:
    #!/usr/bin/env bash
    latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    if [ -z "$latest_tag" ]; then
        echo "{{ YELLOW }}No previous tags found{{ RESET }}"
        exit 0
    fi

    echo "{{ BOLD }}Analyzing commits since $latest_tag...{{ RESET }}"
    echo ""

    # Check for breaking changes
    if git log "$latest_tag"..HEAD --oneline | grep -qiE "(breaking|break|BREAKING)"; then
        echo "{{ YELLOW }}⚠ Breaking changes detected → suggest {{ BOLD }}MAJOR{{ RESET }}{{ YELLOW }} bump{{ RESET }}"
        suggested="major"
    elif git log "$latest_tag"..HEAD --oneline | grep -qiE "(feat|feature|add)"; then
        echo "{{ BLUE }}ℹ New features detected → suggest {{ BOLD }}MINOR{{ RESET }}{{ BLUE }} bump{{ RESET }}"
        suggested="minor"
    else
        echo "{{ GREEN }}ℹ Only fixes/chores → suggest {{ BOLD }}PATCH{{ RESET }}{{ GREEN }} bump{{ RESET }}"
        suggested="patch"
    fi

    echo ""
    echo "Run: {{ BOLD }}just bump $suggested [--commit] [--tag]{{ RESET }}"

# ============================================================================
# Cleanup Recipes (group: 'clean')
# ============================================================================

# Clean build artifacts (group: 'clean')
[group('clean')]
clean-build:
    @echo "{{ BLUE }}-> Cleaning build files...{{ RESET }}"
    rm -rf {{ BUILD_DIR }}/ {{ NUITKA_DIST_DIR }}/ *.spec *.build/
    @echo "{{ GREEN }}✓ Build files cleaned{{ RESET }}"

# Clean Python cache files (group: 'clean')
[group('clean')]
clean-cache:
    @echo "{{ BLUE }}-> Cleaning Python cache...{{ RESET }}"
    find . -type f -name '*.pyc' -delete 2>/dev/null || true
    find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name '.pyright' -exec rm -rf {} + 2>/dev/null || true
    rm -rf .mypy_cache/ .pytest_cache/
    @echo "{{ GREEN }}✓ Cache cleaned{{ RESET }}"

# Clean virtual environment - use with caution! [confirm] (group: 'clean')
[confirm("This will delete your virtual environment. Continue?")]
[group('clean')]
clean-venv:
    @echo "{{ YELLOW }}-> Removing virtual environment...{{ RESET }}"
    rm -rf venv/ .venv/
    @echo "{{ GREEN }}✓ Virtual environment removed{{ RESET }}"

# Clean everything except source [confirm] (group: 'clean')
[confirm("This will remove ALL generated files. Continue?")]
[group('clean')]
clean-all: clean-build clean-cache
    @echo "{{ BLUE }}-> Deep cleaning...{{ RESET }}"
    rm -rf .taskmaster/tasks/*.md
    @echo "{{ GREEN }}✓ All artifacts cleaned{{ RESET }}"

# Alias for clean-build
clean: clean-build

# ============================================================================
# Info & Diagnostics Recipes (group: 'info')
# ============================================================================

# Show project information (group: 'info')
[group('info')]
info:
    @echo "{{ BOLD }}{{ APP_NAME }}{{ RESET }} v{{ VERSION }}"
    @echo ""
    @echo "{{ BOLD }}Paths:{{ RESET }}"
    @echo "  Python:     {{ PYTHON }}"
    @echo "  Prefix:     {{ PREFIX }}"
    @echo "  Build dir:  {{ BUILD_DIR }}"
    @echo ""
    @echo "{{ BOLD }}Status:{{ RESET }}"
    @echo "  Venv:       {{ if path_exists("venv") == "true" { "✓ present" } else { "✗ not found" } }}"
    @echo "  Build:      {{ if path_exists(BUILD_DIR / NUITKA_BINARY) == "true" { "✓ available" } else { "✗ not built" } }}"

# Show installation paths - where files would be installed (group: 'info')
[group('info')]
paths:
    @echo "{{ BOLD }}Installation Paths (PREFIX={{ PREFIX }}):{{ RESET }}"
    @echo "  Binary:     {{ BIN_DIR }}/{{ APP_NAME }}"
    @echo "  Icon:       {{ ICON_DEST_DIR }}/{{ APP_NAME }}.png"
    @echo "  Desktop:    {{ DESKTOP_DEST_DIR }}/{{ APP_NAME }}.desktop"

# ============================================================================
# Private Helper Recipes
# ============================================================================

# Generate desktop entry content (private)
[private]
_generate-desktop:
    #!/usr/bin/env bash
    cat <<EOF
    [Desktop Entry]
    Version={{ VERSION }}
    Type=Application
    Name=Clipse GUI
    GenericName=Clipboard Manager
    Comment=GTK Clipboard Manager
    Exec={{ BIN_DIR }}/{{ APP_NAME }}
    Icon={{ APP_NAME }}
    Terminal=false
    Categories=Utility;GTK;
    StartupNotify=true
    StartupWMClass=org.d7om.ClipseGUI
    EOF

# Build a standalone binary with Nuitka (group: 'build')
[group('build')]
nuitka:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p dist
    python3 -m nuitka \
        --onefile \
        --linux-onefile-compression=none \
        --output-dir=dist \
        --output-filename=clipse-gui.bin \
        --include-package=clipse_gui \
        --include-package-data=clipse_gui \
        --enable-plugin=gi \
        --noinclude-default-mode=nofollow \
        clipse-gui.py

# Verify prefix directory exists and is writable (private)
[private]
verify-prefix:
    #!/usr/bin/env bash
    if [ ! -d "{{ PREFIX }}" ]; then
        echo "{{ YELLOW }}Warning: PREFIX directory {{ PREFIX }} does not exist{{ RESET }}"
        echo "Creating with sudo..."
        sudo mkdir -p "{{ PREFIX }}"
    fi
