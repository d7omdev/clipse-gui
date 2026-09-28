# clipse-gui — agent guide

GTK3 (PyGObject) frontend for the `clipse` clipboard daemon. Python 3.11+, no framework.
User-facing docs live in `docs/` and are the source of truth for behaviour; keep them in
step with any keybinding, setting, or theme change (`docs/keybindings.md`,
`docs/configuration.md`, `docs/theming.md`).

## Run the gate

```bash
.venv/bin/python -m pytest -q      # must stay green
rtk proxy ruff check <files>       # or plain `ruff check`; see hook note below
```

The `.git/hooks/pre-commit` hook runs `ruff check` on staged files and HEAD already carries
~120 findings, so it blocks every commit that touches those files. Prove you added none
(diff `ruff check --output-format concise` against a temp `git worktree` of HEAD), then
commit with `--no-verify`. Do not fix unrelated lint as a side effect.

Tests import `clipse_gui.constants`, which reads the developer's real
`~/.config/clipse-gui/settings.ini` at import time. A test that depends on a default must
`patch` the constant (see `tests/test_keyboard_mixin.py`), never assume it.

Never launch the app or a build unless asked. When you must see the UI, render offscreen:
create `ClipseGuiApplication`, wait ~2.5 s, call `app.window.draw(cairo.Context(surface))`,
and point `HOME`/`XDG_CONFIG_HOME` at a sandbox with a fake `clipboard_history.json` so
real clipboard content never reaches the repo.

## Layout

- `clipse_gui/cli.py` — entry point; the `gi.require_version` calls live here and must run
  before any `from gi.repository import`. Importing a module directly outside the CLI
  prints a PyGIWarning; harmless.
- `clipse_gui/app.py` — `ClipseGuiApplication`, window creation, tray hookup, shutdown.
- `clipse_gui/controller.py` — thin assembler composing the mixins in
  `controller_mixins/` (data, style, list_view, search, item_ops, selection, clipboard,
  preview, scroll, keyboard, misc). Behaviour lives in the mixins; the controller only
  wires state and signals.
- `clipse_gui/ui/` — widget builders (list_row, preview, settings, help, icons, text,
  detection). `ui_components.py` is a re-export shim for back-compat; new code imports
  `clipse_gui.ui.*` directly.
- `clipse_gui/constants.py` — `DEFAULT_SETTINGS`, every derived constant, the CSS generator
  `get_app_css()`, and theme discovery (`list_themes`, `load_theme_css`, `load_user_css`).
- `clipse_gui/themes/*.css` — built-in themes, shipped as package data
  (`pyproject.toml` package-data and the Nuitka `--include-package-data` flag in `justfile`).
- `clipse_gui/data_manager.py` — history load/save and the file watcher.

## Gotchas that are not visible from the code

- Most consumers import constants by name (`from ..constants import ENTER_TO_PASTE`), so
  assigning `constants.X = ...` at runtime does nothing for them. Settings rows for those
  are labelled "(restart required)"; if you make one live, read it through the module
  (`constants.X`) at call time and drop the label.
- The clipse daemon writes `"filePath": "null"` (the string) for text items. Treat
  `None`, `""` and `"null"` as "no image".
- The daemon and the GUI both write `clipboard_history.json`. `DataManager.save_pending`
  and `_reloading` stop the watcher from reloading over an unsaved edit; keep them intact
  when touching save or watch paths.
- Rows are lazily loaded (`initial_load_count`). Anything that must cover "all items"
  iterates `self.filtered_items`, not `list_box.get_children()`.
- `selected_indices` are positions in `self.items`; any wholesale replacement of
  `self.items` must exit selection mode first.
- Pin icons are SVG pixbufs, not CSS. Their colour comes from the theme's
  `@define-color pin` (via `constants.THEME_PIN_COLOR`) or else `accent_color`; the
  `.pin-icon` CSS rules only affect the button chrome.
- Theme CSS is appended after `get_app_css()` in one provider; a theme wins by cascade
  order. `background_transparent = True` overrides every theme's window background, and
  `~/.config/clipse-gui/custom.css` is appended last.
- Single click on a row copies, pastes and closes by design; `row-activated` is only the
  double-click path and the ListBox has `activate_on_single_click` off.
