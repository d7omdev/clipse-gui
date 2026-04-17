# Getting Started

## Starting the Daemon

Clipse GUI does not listen to clipboard events. The `clipse` daemon does. Start it before using the GUI:

```bash
clipse -listen &
```

For it to survive reboots, add an autostart entry for your environment. Window-manager-specific snippets are in [wm-integration.md](wm-integration.md).

Confirm it's running:

```bash
pgrep -a clipse
```

## First Launch

```bash
clipse-gui
```

On first run, Clipse GUI creates `~/.config/clipse-gui/settings.ini` with default values. Copy something to your clipboard — it should appear in the list.

### Empty list on first launch

This is expected if:

- The daemon was just started and no clipboard events have fired yet
- `~/.config/clipse/clipboard_history.json` doesn't exist yet

Copy any text. The list populates.

## Core Workflow

### Navigate

- `j` / `k` or arrow keys to move up/down
- `Home` / `End` to jump to top/bottom
- `PgUp` / `PgDn` to move 5 items at a time

### Search

- `/` or `f` focuses the search entry
- Type to filter; results update live
- `Esc` clears search and returns focus to the list

### Copy and Paste

| Action | Keys | Effect |
|--------|------|--------|
| Copy | `Enter` | Item copied to clipboard |
| Copy + paste | `Shift+Enter` | Item copied **and** pasted into the previously focused window |

To make `Enter` always paste (instead of just copying), set `enter_to_paste = True` — see [Configuration](configuration.md#enter_to_paste).

### Pin Items

- `p` toggles pin on the selected item
- `Tab` filters the list to show only pinned items
- Pinned items have an accent-colored left border

Pins survive restarts. If `protect_pinned_items = True`, they're excluded from bulk deletes.

### Multi-Select

- `v` enters multi-select mode
- `Space` toggles selection on the current item
- `Ctrl+A` / `Ctrl+Shift+A` select / deselect all
- `Ctrl+X` or `Shift+Delete` deletes all selected

Exit with `v` again, or `Esc`.

### Preview

- `Space` on a non-selection-mode row opens a preview
- Preview supports text search (`Ctrl+F`) and JSON prettify (`Ctrl+B`)
- URLs detected in the item open in your default browser (if `open_links_with_browser = True`)

### Zoom

- `Ctrl +` / `Ctrl -` adjust text size
- `Ctrl 0` resets to default

## Compact Mode

Compact mode removes metadata rows and tightens padding — more items per screen. Toggle from the header bar or set `compact_mode = True` in config.

## Tray Mode

By default, closing the window minimizes to tray instead of quitting. See [Tray Integration](tray.md) for the tray menu, quick-paste behavior, and disabling this.

## Next Steps

- Customize keys: they're hard-coded but extensible — see source at `clipse_gui/controller_mixins/keyboard_mixin.py`
- Change the theme: [Theming](theming.md)
- Tune for your WM: [Window Manager Setup](wm-integration.md)
