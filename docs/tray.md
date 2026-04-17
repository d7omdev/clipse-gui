# Tray Integration

When `minimize_to_tray = True` (the default), closing the Clipse GUI window sends it to the system tray instead of quitting.

## Requirements

A working system tray implementation. Compatible with:

- **StatusNotifier (modern)** — KDE Plasma, `waybar`, `hyprland` with `waybar`, GNOME with the AppIndicator extension
- **XEmbed (legacy)** — i3bar, older panels

If no tray host is running, minimize-to-tray falls back to hiding the window without an indicator. You can still re-summon the app by running `clipse-gui` again or from a keybind.

## Tray Menu

Right-clicking the tray icon (or left-clicking depending on your panel) shows:

1. **Show Window** — brings the app back to foreground
2. **Recent Items** — last N clipboard entries (N = `tray_items_count`, default 20)
3. **Quit** — fully exit the app

### Quick Paste

With `tray_paste_on_select = True` (default), clicking a recent item from the tray menu:

1. Copies it to the clipboard
2. Simulates paste into the focused window

Set to `False` if you want tray clicks to only copy without pasting.

## Positioning on Reopen

When restored from tray, the window repositions **at the current cursor location** (commit `9ac5ee1`). This is intentional — the primary use case is quick-paste at the cursor, not returning to a saved window position.

If you prefer fixed positioning, use your window manager's rules — see [wm-integration.md](wm-integration.md).

## Disabling Tray Behavior

Set in `settings.ini`:

```ini
[General]
minimize_to_tray = False
```

`Esc` and close-button will then quit immediately.

## Troubleshooting

### Icon doesn't appear

- Verify a tray host is running: `pgrep -a waybar` / check KDE Plasma status
- On GNOME, install the **AppIndicator and KStatusNotifierItem Support** extension
- Check Clipse GUI logs for `tray_manager` warnings

### Clicking tray items does nothing

- `tray_paste_on_select` requires paste simulation tools (`wtype` or `xdotool`)
- If paste fails but copy succeeds, you'll still see clipboard content — manually paste with `Ctrl+V`

### Menu doesn't update with recent items

- The menu rebuilds on tray activation, not on every clipboard event
- If the daemon isn't writing history, items won't appear — check `pgrep clipse`
