# Clipse GUI Documentation

GTK3 frontend for the [clipse](https://github.com/savedra1/clipse) clipboard manager.

## Quick Links

| Page | What you'll find |
|------|------------------|
| [Installation](installation.md) | Arch, source build, dependencies |
| [Getting Started](getting-started.md) | First launch, daemon setup, basic workflow |
| [Keybindings](keybindings.md) | Every shortcut, grouped by context |
| [Configuration](configuration.md) | `settings.ini` — every option explained |
| [Theming](theming.md) | Colors, border radius, CSS customization |
| [Tray Integration](tray.md) | System tray menu, quick-paste |
| [Window Manager Setup](wm-integration.md) | Hyprland, Sway, i3, GNOME, KDE |
| [Troubleshooting](troubleshooting.md) | Common problems and fixes |

## What is Clipse GUI?

Clipse GUI is a graphical interface for browsing, searching, and pasting from your clipboard history. It depends on [`clipse`](https://github.com/savedra1/clipse) running in the background as the actual clipboard listener — this app is purely the UI layer.

### Architecture at a glance

```
┌──────────────┐      reads       ┌────────────────────────┐
│  clipse -l   │  ──────────────▶ │ ~/.config/clipse/      │
│  (daemon)    │     writes       │  clipboard_history.json│
└──────────────┘                  └──────────┬─────────────┘
                                             │ reads
                                             ▼
                                  ┌────────────────────────┐
                                  │      clipse-gui        │
                                  │   (this application)   │
                                  └────────────────────────┘
```

The daemon captures. The GUI displays and acts.

## Project Status

Version: `0.9.0`
License: MIT
Platforms: Linux (Wayland + X11)

## Reporting Issues

File bugs at [github.com/d7omdev/clipse-gui/issues](https://github.com/d7omdev/clipse-gui/issues).
