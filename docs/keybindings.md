# Keybindings

Press `?` in the app for the same reference. Keys are grouped by context — some are only active in certain modes.

## Navigation

| Key | Action |
|-----|--------|
| `/` or `f` | Focus search field |
| `↑` / `k` | Navigate up |
| `↓` / `j` | Navigate down |
| `PgUp` | Scroll 5 items up |
| `PgDn` | Scroll 5 items down |
| `Home` | Go to top |
| `End` | Go to bottom of loaded items |
| `Tab` | Toggle "Pinned Only" filter |
| Any letter | Start searching (opens and focuses the search field) |

## Actions

| Key | Action |
|-----|--------|
| `Enter` | Copy selected item to clipboard |
| `Shift+Enter` | Copy **and** paste selected item |
| Click | Copy item and paste |
| `Space` | Show full preview (or open URL if detected) |
| `p` | Toggle pin status |
| `x` / `Del` | Delete selected item |
| `Ctrl+Shift+Del` / `Ctrl+D` | Clear all items (pinned kept only if `protect_pinned_items` is on) |

If `enter_to_paste = True`, `Enter` pastes and `Shift+Enter` only copies — the mapping flips.

## Multi-Select Mode

Enter with `v`. Exit with `v` or `Esc`.

| Key | Action |
|-----|--------|
| `v` | Toggle selection mode |
| `Space` | Toggle item selection |
| `Ctrl+A` | Select all visible items |
| `Ctrl+Shift+A` | Deselect all items |
| `x` / `Del` / `Ctrl+X` / `Shift+Del` | Delete all selected items |

## View

| Key | Action |
|-----|--------|
| `Ctrl +` | Zoom in |
| `Ctrl -` | Zoom out |
| `Ctrl 0` | Reset zoom |

Zoom affects list text size. Preview window has its own zoom.

## Preview Window

| Key | Action |
|-----|--------|
| `Ctrl+F` | Find text in preview |
| `Enter` / `Shift+Enter` | Next / previous find match |
| `Ctrl+B` | Format text (pretty-print JSON) |
| `Ctrl+C` | Copy text from preview |
| `Ctrl +` / `Ctrl -` / `Ctrl 0` | Zoom preview text in / out / reset |
| `Esc` / `Ctrl+W` | Close preview (`Esc` closes the find bar first if open) |

## General

| Key | Action |
|-----|--------|
| `?` | Show help window |
| `Ctrl+,` | Open settings |
| `Esc` | Clear search → exit mode → minimize/quit |
| `Ctrl+Q` | Quit application |

### `Esc` behavior

`Esc` cascades through contexts:

1. If in multi-select mode → exit multi-select
2. Else if search has text → clear search
3. Else if minimize-to-tray is enabled → minimize to tray
4. Else → quit

This lets a single key handle "undo state" without needing to remember which context you're in.

## Search-Focused Keys

When the search entry has focus, single-key shortcuts are off so you can type:

- `Up` / `Down` / `PgUp` / `PgDn` → navigate the list without losing typed query
- `Enter` / `Shift+Enter` → copy (or copy & paste) the selected row, or the first match
- `Esc` → clear and return focus to list

See `clipse_gui/controller_mixins/keyboard_mixin.py` for the full dispatch table.
