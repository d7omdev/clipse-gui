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

## Actions

| Key | Action |
|-----|--------|
| `Enter` | Copy selected item to clipboard |
| `Shift+Enter` | Copy **and** paste selected item |
| `Space` | Show full preview (or open URL if detected) |
| `p` | Toggle pin status |
| `x` / `Del` | Delete selected item |

If `enter_to_paste = True`, `Enter` pastes and `Shift+Enter` only copies — the mapping flips.

## Multi-Select Mode

Enter with `v`. Exit with `v` or `Esc`.

| Key | Action |
|-----|--------|
| `v` | Toggle selection mode |
| `Space` | Toggle item selection |
| `Ctrl+A` | Select all visible items |
| `Ctrl+Shift+A` | Deselect all items |
| `Ctrl+X` / `Shift+Del` | Delete all selected items |
| `Ctrl+Shift+Del` / `Ctrl+D` | Clear all non-pinned items |

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
| `Ctrl+B` | Format text (pretty-print JSON) |
| `Ctrl+C` | Copy text from preview |
| `Esc` | Close preview |

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

When the search entry has focus, certain shortcuts are suppressed so you can type:

- `v`, `x`, `p`, `j`, `k`, `f`, `/`, `?`, `space` → inserted as characters
- `Up` / `Down` / `PgUp` / `PgDn` → navigate the list without losing typed query
- `Enter` / `Tab` → blocked (prevents accidental selection while typing)
- `Esc` → clear and return focus to list

See `clipse_gui/controller_mixins/keyboard_mixin.py` for the full dispatch table.
