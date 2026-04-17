# Window Manager Integration

Clipse GUI is a regular GTK3 application. Most WM config involves:

1. Autostarting the `clipse -listen` daemon
2. Binding a hotkey to launch `clipse-gui`
3. Optionally forcing floating/centered layout

## Hyprland

```conf
# Start daemon on login
exec-once = clipse -listen

# Hotkey to summon
bind = SUPER, V, exec, clipse-gui

# Window rules
windowrule = float, title:(Clipse GUI)
windowrule = center, title:(Clipse GUI)
windowrule = size 600 800, title:(Clipse GUI)
```

## Sway / i3

```conf
# Autostart daemon
exec clipse -listen

# Hotkey
bindsym $mod+v exec clipse-gui

# Floating rule
for_window [title="Clipse GUI"] floating enable, resize set 600 800, move position center
```

## Niri

```kdl
spawn-at-startup "clipse" "-listen"

binds {
    Mod+V { spawn "clipse-gui"; }
}

window-rule {
    match title="Clipse GUI"
    default-column-width { fixed 600; }
}
```

## GNOME

### Autostart

Create `~/.config/autostart/clipse.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Clipse Daemon
Exec=clipse -listen
X-GNOME-Autostart-enabled=true
```

### Hotkey

Settings → Keyboard → Custom Shortcuts → Add:

- **Name:** Clipse GUI
- **Command:** `clipse-gui`
- **Shortcut:** `Super+V` (or whatever)

## KDE Plasma

### Autostart

System Settings → Autostart → Add Application → `clipse -listen`

### Hotkey

System Settings → Shortcuts → Custom Shortcuts → Edit → New → Global Shortcut → Command/URL:

- **Trigger:** your chosen keybind
- **Action:** `clipse-gui`

## XMonad

```haskell
-- ~/.xmonad/xmonad.hs
import XMonad.Util.SpawnOnce

myStartupHook = do
    spawnOnce "clipse -listen"

-- In your keys section
, ((modm, xK_v), spawn "clipse-gui")

-- In your manageHook
, title =? "Clipse GUI" --> doFloat
```

## Autostart Without a WM Config

If your WM doesn't have a native startup mechanism, use XDG autostart. Create `~/.config/autostart/clipse.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Clipse Daemon
Exec=clipse -listen
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
```

This works on any desktop environment that honors the XDG autostart spec (GNOME, KDE, XFCE, LXQt, Cinnamon, MATE).

## Recommended Window Sizes

- **500×700** — default, comfortable
- **400×600** — compact layouts
- **600×800** — content-heavy use (see Hyprland example above)

Override via `settings.ini`:

```ini
[UI]
default_window_width = 600
default_window_height = 800
```
