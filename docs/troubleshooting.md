# Troubleshooting

## No Clipboard History Appears

**Check 1:** Is the daemon running?

```bash
pgrep -a clipse
```

No output → start it:

```bash
clipse -listen &
```

**Check 2:** Does the history file exist?

```bash
ls -la ~/.config/clipse/clipboard_history.json
```

If missing, the daemon hasn't captured anything yet. Copy any text, then check again.

**Check 3:** Is `clipse_dir` pointing at the right place?

If you customized `clipse`'s data directory, mirror that in `[General] clipse_dir` in `settings.ini`.

## Paste Doesn't Work

Copy works, but nothing pastes into the target window.

**Wayland:**

```bash
which wtype
```

If missing: install via your package manager. Arch: `sudo pacman -S wtype`.

**X11:**

```bash
which xdotool
```

Install if missing: `sudo pacman -S xdotool` (or equivalent).

**Both:** check `enter_to_paste` behavior. Copy might be working while paste simulation fails silently. Try increasing `paste_simulation_delay_ms` to `300` — some compositors race the keystroke with the clipboard write.

## App Won't Start

```bash
clipse-gui
```

### `ModuleNotFoundError: No module named 'gi'`

Install PyGObject:

```bash
# Arch
sudo pacman -S python-gobject gtk3

# Debian/Ubuntu
sudo apt install python3-gi gir1.2-gtk-3.0
```

### `ValueError: Namespace Gtk not available`

GTK3 introspection data missing. Install `gir1.2-gtk-3.0` (Debian) or `gtk3` (Arch).

### Silent failure, no window

Run from a terminal with debug logging:

```bash
G_MESSAGES_DEBUG=all clipse-gui
```

Look for CSS parse errors or missing dependencies.

## UI Glitches

### List items overlap or mis-render

Your GTK theme may conflict with the app's CSS. Test with the default theme:

```bash
GTK_THEME=Adwaita clipse-gui
```

If it renders correctly, the theme is the culprit — either switch themes or edit `get_app_css()` in `clipse_gui/constants.py` to override the conflicting rules.

### Blurry icons at high DPI

Set:

```bash
GDK_SCALE=2 clipse-gui
```

Or globally via your WM.

## Tray Issues

See [tray.md](tray.md#troubleshooting).

## Search is Slow

With histories > 10k items, filtering can lag. Tune:

```ini
[General]
search_debounce_ms = 500

[Performance]
initial_load_count = 50
load_batch_size = 30
```

Higher debounce = fewer re-renders but less responsive feel.

## Config File Corrupted

If the app crashes on launch after a config edit, back up and reset:

```bash
mv ~/.config/clipse-gui/settings.ini ~/.config/clipse-gui/settings.ini.bak
clipse-gui
```

A fresh default config regenerates.

## Logs

Clipse GUI uses Python's `logging` module. To see detail:

```bash
CLIPSE_GUI_LOG=DEBUG clipse-gui 2>&1 | less
```

Or:

```bash
clipse-gui 2>&1 | grep -i error
```

## Reporting a Bug

When filing an issue at [github.com/d7omdev/clipse-gui/issues](https://github.com/d7omdev/clipse-gui/issues), include:

- Output of `clipse-gui --version`
- Your desktop environment / window manager
- Wayland or X11
- Output of `pgrep -a clipse`
- Contents of `settings.ini` (redact paths if needed)
- Any error output with `G_MESSAGES_DEBUG=all`
