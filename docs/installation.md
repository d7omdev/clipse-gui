# Installation

## Dependencies

Required regardless of install method:

| Package | Purpose | Notes |
|---------|---------|-------|
| `clipse` | Clipboard daemon | [github.com/savedra1/clipse](https://github.com/savedra1/clipse) |
| `gtk3` | UI toolkit | |
| `python-gobject` | GTK3 Python bindings | PyGObject |
| `wl-clipboard` | Wayland copy/paste | `wl-copy`, `wl-paste` |
| `wtype` | Wayland paste simulation | Needed for auto-paste |
| `xdotool` | X11 paste simulation | X11 users only |
| `xclip` | X11 clipboard fallback | X11 users only |

You only need the Wayland **or** X11 toolchain, not both.

## Arch Linux (AUR)

```bash
yay -S clipse-gui
# or
paru -S clipse-gui
```

This installs the `clipse-gui` binary and pulls required dependencies.

## From Source

```bash
git clone https://github.com/d7omdev/clipse-gui
cd clipse-gui
```

The project uses [just](https://github.com/casey/just) as a task runner:

| Command | Action |
|---------|--------|
| `just install` | Build and install system-wide |
| `just build` | Build without installing |
| `just run` | Run locally without installing |
| `just uninstall` | Remove installed files |

### Manual install (no just)

If you don't want `just`, the Makefile targets map directly:

```bash
make build
sudo make install
```

## Verifying the Install

```bash
clipse-gui --version
which clipse-gui
```

Then check the daemon is reachable:

```bash
pgrep -a clipse
```

If no output appears, start the daemon — see [Getting Started](getting-started.md#starting-the-daemon).

## Uninstalling

```bash
# AUR
yay -R clipse-gui

# Source
just uninstall
```

Config files at `~/.config/clipse-gui/` are **not** removed automatically. Delete manually if desired:

```bash
rm -rf ~/.config/clipse-gui
```
