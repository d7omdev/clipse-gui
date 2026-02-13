# Clipse GUI

A GTK3 GUI for the [clipse](https://github.com/savedra1/clipse) clipboard manager.

![Screenshot](docs/screenshot.png)

<details>
<summary>Compact Mode</summary>

![compact_clipse-gui.png](docs/compact_clipse-gui.png)

</details>

## Features

- Browse, search, and filter clipboard history
- Pin important items
- Image thumbnails and text preview with zoom
- Keyboard navigation (`?` for shortcuts)
- Compact mode, hover-to-select
- Multi-select mode
- Auto-paste on Enter (optional)

## Installation

### Arch Linux
```bash
yay -S clipse-gui
```

### From Source
```bash
git clone https://github.com/d7omdev/clipse-gui
cd clipse-gui

just install      # Build and install
just build       # Just build
just run         # Run without installing
just uninstall   # Remove
```

## Requirements

- [clipse](https://github.com/savedra1/clipse) CLI (running with `clipse -listen`)
- GTK3, wl-clipboard, wtype (Wayland) or xdotool (X11)

## Usage

```bash
clipse-gui
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` or `f` | Search |
| `Enter` | Copy item |
| `Space` | Preview |
| `p` | Pin/unpin |
| `x` or `Delete` | Delete |
| `Tab` | Show pinned only |
| `v` | Multi-select mode |
| `Ctrl+F` | Search in preview |
| `Ctrl+B` | Format JSON in preview |
| `Ctrl++/-/0` | Zoom |
| `?` | Help |

### Hyprland
Add to `hyprland.conf`:
```
windowrule = size 600 800,title:(Clipse GUI)
windowrule = center, title:(Clipse GUI)
windowrule = float, title:(Clipse GUI)
```

## Configuration

Settings file: `~/.config/clipse-gui/settings.ini` (created on first run).

### Key Options

```ini
[General]
clipse_dir = ~/.config/clipse        # Clipse history location
enter_to_paste = False              # Auto-paste after copy
compact_mode = False                # Minimal UI
hover_to_select = False             # Select on hover
protect_pinned_items = False        # Prevent deleting pinned

[Commands]
copy_tool_cmd = wl-copy            # Copy command (Wayland)
paste_simulation_cmd_wayland = wtype -M ctrl -P v -p v -m ctrl
```

## Troubleshooting

### No clipboard history
Ensure clipse is running:
```bash
clipse -listen
```

Add to window manager config to start on boot:
```
exec-once = clipse -listen  # Hyprland
```

### Paste not working
- Install `wtype` (Wayland) or `xdotool` (X11)
- Enable `enter_to_paste = True` in settings

## License

MIT - See [LICENSE](LICENSE)
