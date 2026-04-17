# Configuration

All settings live in `~/.config/clipse-gui/settings.ini`. The file is created on first launch with default values. Most options are also exposed in the in-app Settings window (`Ctrl+,`).

## File Format

Standard INI. Sections are `[General]`, `[Style]`, `[Commands]`, `[UI]`, `[Performance]`. Boolean values accept `True`/`False` (case-insensitive).

## `[General]`

Behavior and workflow toggles.

### `clipse_dir`
- **Default:** `~/.config/clipse`
- Path where the `clipse` daemon writes its history. Change only if you've customized the daemon's output location.

### `history_filename`
- **Default:** `clipboard_history.json`
- Filename inside `clipse_dir` to read.

### `enter_to_paste`
- **Default:** `False`
- When `True`: `Enter` copies **and** simulates paste. `Shift+Enter` only copies.
- When `False`: `Enter` only copies. `Shift+Enter` copies and pastes.
- Requires `wtype` (Wayland) or `xdotool` (X11).

### `compact_mode`
- **Default:** `False`
- Denser row layout. Hides metadata like timestamps.

### `protect_pinned_items`
- **Default:** `False`
- When `True`, bulk delete operations (`Ctrl+D`, `Ctrl+Shift+Del`) skip pinned items.

### `hover_to_select`
- **Default:** `False`
- Selection follows the mouse pointer instead of requiring a click. Useful for single-click-to-paste workflows.

### `highlight_search`
- **Default:** `True`
- Highlights matching substrings in list rows when searching.

### `save_debounce_ms`
- **Default:** `300`
- Delay before persisting config changes to disk. Higher = fewer writes, more risk of loss on crash.

### `search_debounce_ms`
- **Default:** `250`
- Delay after last keystroke before filtering the list. Lower = snappier, higher CPU with large histories.

### `paste_simulation_delay_ms`
- **Default:** `150`
- Pause between clipboard copy and paste keystroke injection. Increase if paste races the copy on slow systems.

### `minimize_to_tray`
- **Default:** `True`
- Close button minimizes to tray instead of quitting. Requires a system tray (StatusNotifier or legacy XEmbed).

### `tray_items_count`
- **Default:** `20`
- Number of recent items shown directly in the tray menu.

### `tray_paste_on_select`
- **Default:** `True`
- Clicking a tray item pastes it immediately instead of only copying.

### `open_links_with_browser`
- **Default:** `True`
- When an item is a detected URL, `Space` opens it in the default browser instead of showing preview.

### `preview_rich_content`
- **Default:** `True`
- Preview window attempts to render images, format JSON, etc. Disable for plain-text only.

## `[Style]`

See [Theming](theming.md) for full treatment. Keys:

- `border_radius` — integer px, default `6`
- `accent_color` — hex, used for pinned items and active toggles, default `#ffcc00`
- `selection_color` — hex, default `#4a90e2`
- `selection_bg_color` — hex, default `#4a90e2`
- `hover_color` — hex, default `#4a90e2`
- `hover_bg_color` — hex, default `#4a90e2`
- `visual_mode_color` — hex, multi-select indicator, default `#9b59b6`

## `[Commands]`

External tools invoked for copy and paste simulation. Override only if you use non-standard tooling.

### `copy_tool_cmd`
- **Default:** `wl-copy`
- Wayland clipboard write command.

### `x11_copy_tool_cmd`
- **Default:** `xclip -i -selection clipboard`

### `paste_simulation_cmd_wayland`
- **Default:** `wtype -M ctrl -P v -p v -m ctrl`
- Command that simulates `Ctrl+V` on Wayland.

### `paste_simulation_cmd_x11`
- **Default:** `xdotool key --clearmodifiers ctrl+v`

## `[UI]`

Window dimensions — all integer pixels.

| Key | Default | Purpose |
|-----|---------|---------|
| `default_window_width` | 500 | Main window |
| `default_window_height` | 700 | Main window |
| `default_preview_text_width` | 700 | Text preview |
| `default_preview_text_height` | 550 | Text preview |
| `default_preview_img_width` | 400 | Image preview |
| `default_preview_img_height` | 200 | Image preview |
| `default_help_width` | 550 | Help window |
| `default_help_height` | 550 | Help window |
| `list_item_image_width` | 200 | Thumbnail width in list rows |
| `list_item_image_height` | 100 | Thumbnail height in list rows |

## `[Performance]`

Tune for large histories. Defaults work well for typical use (< 10k items).

### `initial_load_count`
- **Default:** `30`
- Rows created when the window opens. Lower = faster startup.

### `load_batch_size`
- **Default:** `20`
- Rows added per scroll-triggered batch.

### `load_threshold_factor`
- **Default:** `0.95`
- Scroll position (0..1) at which the next batch loads. `0.95` = "95% scrolled."

### `image_cache_max_size`
- **Default:** `50`
- Max decoded image thumbnails kept in memory. Higher = smoother re-scrolling, more RAM.

## Applying Changes

- Style changes apply live when saved through the Settings window
- Behavior changes (tray, debounce, etc.) may require restart — the Settings window prompts when needed
- Manual edits to `settings.ini` require restarting the app

## Full Example

```ini
[General]
clipse_dir = ~/.config/clipse
history_filename = clipboard_history.json
enter_to_paste = False
compact_mode = False
protect_pinned_items = True
hover_to_select = False
highlight_search = True
save_debounce_ms = 300
search_debounce_ms = 250
paste_simulation_delay_ms = 150
minimize_to_tray = True
tray_items_count = 20
tray_paste_on_select = True
open_links_with_browser = True
preview_rich_content = True

[Style]
border_radius = 8
accent_color = #f5a623
selection_color = #4a90e2
selection_bg_color = #4a90e2
hover_color = #4a90e2
hover_bg_color = #4a90e2
visual_mode_color = #9b59b6

[Commands]
copy_tool_cmd = wl-copy
x11_copy_tool_cmd = xclip -i -selection clipboard
paste_simulation_cmd_wayland = wtype -M ctrl -P v -p v -m ctrl
paste_simulation_cmd_x11 = xdotool key --clearmodifiers ctrl+v
```
