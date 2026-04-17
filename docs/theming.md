# Theming

Clipse GUI's visual style is driven by a small set of tokens in `[Style]` plus the CSS generator in `clipse_gui/constants.py:get_app_css`.

## Settings-Driven Theming

Change these in `~/.config/clipse-gui/settings.ini` or the in-app Settings → Appearance tab.

| Token | Default | Used for |
|-------|---------|----------|
| `border_radius` | `6` | All rounded corners (buttons, rows, switches' tracks use pill regardless) |
| `accent_color` | `#ffcc00` | Pin indicator, pinned row left border, active pin-filter toggle |
| `selection_color` | `#4a90e2` | Selected-row left border, focus rings, switch `on` state |
| `selection_bg_color` | `#4a90e2` | Reserved for future background tints |
| `hover_color` | `#4a90e2` | Hover border color on list rows |
| `hover_bg_color` | `#4a90e2` | Hover background tint on list rows |
| `visual_mode_color` | `#9b59b6` | Multi-select mode indicator and selected-in-visual-mode rows |

Colors accept any CSS-recognized format, but stick to `#RRGGBB` for portability.

### Live Reload

Style changes saved via the Settings window regenerate the CSS and reapply immediately — no restart needed. See `StyleMixin.update_style_css` in `clipse_gui/controller_mixins/style_mixin.py`.

## Palette Recipes

### Dark + Warm accent

```ini
border_radius = 10
accent_color = #ff9f43
selection_color = #5b8def
visual_mode_color = #a29bfe
```

### Muted monochrome

```ini
border_radius = 4
accent_color = #e0e0e0
selection_color = #9aa0a6
visual_mode_color = #8e8e8e
```

### High-contrast

```ini
border_radius = 2
accent_color = #ffd600
selection_color = #00e5ff
visual_mode_color = #ff1744
```

## GTK Theme Integration

Clipse GUI respects your system GTK3 theme for:

- Window chrome / titlebar
- Default text color
- Font family and base size

The `[Style]` tokens only override specific semantic surfaces (selection, pinning, multi-select). If your GTK theme already provides a selection color you prefer, set `selection_color` to match it.

## Advanced: Editing the CSS Generator

For structural changes (spacing, shadows, font weights), edit `get_app_css()` in `clipse_gui/constants.py`. The function accepts the four main color tokens plus `border_radius` as parameters, so any changes you make there immediately respond to settings updates.

Key classes you may want to customize:

| Class | What it styles |
|-------|----------------|
| `.list-row` | Each item in the main list |
| `.list-row:hover` | Hover state |
| `.list-row:selected` | Currently focused/selected item |
| `.pinned-row` | Rows with pinned items |
| `.selected-row` | Rows checked in multi-select mode |
| `.pin-icon` | Pin button in each row |
| `.status-label` | Bottom status bar |
| `.key-shortcut` | Key cap styling in help window |
| `.main-window .pin-toggle` | Header "Pinned Only" button |

## What You Cannot Theme (Yet)

- Font family — inherits from GTK
- List row height — driven by compact-mode toggle, not CSS
- Per-item colors — uniform across all items

These are intentional constraints. File an issue if you need them configurable.
