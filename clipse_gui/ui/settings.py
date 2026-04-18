"""Settings window with General and Style tabs."""

import logging

from gi.repository import Gdk, Gtk

from ..constants import (
    ACCENT_COLOR,
    BORDER_RADIUS,
    CLEAR_SEARCH_ON_ESCAPE,
    COMPACT_MODE,
    ENTER_TO_PASTE,
    HIGHLIGHT_SEARCH,
    HOVER_TO_SELECT,
    MINIMIZE_TO_TRAY,
    OPEN_LINKS_WITH_BROWSER,
    PREVIEW_RICH_CONTENT,
    PROTECT_PINNED_ITEMS,
    SELECTION_COLOR,
    TRAY_ITEMS_COUNT,
    TRAY_PASTE_ON_SELECT,
    VISUAL_MODE_COLOR,
    config,
)


def _create_section_frame(title):
    """Helper to create a framed section with a label."""
    frame = Gtk.Frame()
    frame.set_shadow_type(Gtk.ShadowType.NONE)

    label = Gtk.Label()
    label.set_markup(f"<b>{title}</b>")
    label.set_halign(Gtk.Align.START)
    frame.set_label_widget(label)

    frame.get_style_context().add_class("settings-section")

    return frame


def _create_setting_row(label_text, widget, tooltip=None):
    """Helper to create a setting row with label and widget."""
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    box.set_margin_start(10)
    box.set_margin_end(10)
    box.set_margin_top(5)
    box.set_margin_bottom(5)

    label = Gtk.Label(label=label_text)
    label.set_halign(Gtk.Align.START)
    label.set_hexpand(True)
    if tooltip:
        label.set_tooltip_text(tooltip)

    widget.set_halign(Gtk.Align.END)
    if tooltip:
        widget.set_tooltip_text(tooltip)

    box.pack_start(label, True, True, 0)
    box.pack_start(widget, False, False, 0)

    return box


def show_settings_window(parent_window, close_cb, restart_app_cb=None,
                         update_style_cb=None, style_defaults=None):
    """Creates and shows the enhanced settings window with sections."""
    settings_window = Gtk.Window(title="Settings")
    settings_window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
    settings_window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
    settings_window.set_transient_for(parent_window)
    settings_window.set_default_size(500, 550)
    settings_window.set_border_width(15)

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

    # Header
    header = Gtk.Label()
    header.set_markup("<big><b>Settings</b></big>")
    header.set_halign(Gtk.Align.CENTER)
    header.set_margin_bottom(10)
    main_box.pack_start(header, False, False, 0)

    # Create notebook for tabs
    notebook = Gtk.Notebook()
    notebook.set_vexpand(True)

    # ============ GENERAL TAB ============
    general_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
    general_tab.set_margin_top(10)
    general_tab.set_margin_bottom(10)
    general_tab.set_margin_start(10)
    general_tab.set_margin_end(10)

    # General Section
    general_frame = _create_section_frame("General")
    general_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    general_box.set_margin_top(10)
    general_box.set_margin_bottom(10)

    # Compact Mode setting
    compact_switch = Gtk.Switch()
    compact_switch.set_active(COMPACT_MODE)
    compact_box = _create_setting_row(
        "Compact mode:",
        compact_switch,
        "Use a more compact layout with smaller margins",
    )

    # Hover to Select setting
    hover_switch = Gtk.Switch()
    hover_switch.set_active(HOVER_TO_SELECT)
    hover_box = _create_setting_row(
        "Hover to select:",
        hover_switch,
        "Select items by hovering over them with the mouse",
    )

    # Enter to Paste setting
    enter_paste_switch = Gtk.Switch()
    enter_paste_switch.set_active(ENTER_TO_PASTE)
    enter_paste_box = _create_setting_row(
        "Enter to paste:",
        enter_paste_switch,
        "Press Enter to paste the selected item and close the window",
    )

    # Highlight Search setting
    highlight_search_switch = Gtk.Switch()
    highlight_search_switch.set_active(HIGHLIGHT_SEARCH)
    highlight_search_box = _create_setting_row(
        "Highlight search:",
        highlight_search_switch,
        "Highlight matching search terms in the results list",
    )

    # Open links in browser setting
    open_links_switch = Gtk.Switch()
    open_links_switch.set_active(OPEN_LINKS_WITH_BROWSER)
    open_links_box = _create_setting_row(
        "Open links on Space:",
        open_links_switch,
        "Press Space on a URL item to open it in the browser (disable to show text preview)",
    )

    # Preview rich content setting
    rich_content_switch = Gtk.Switch()
    rich_content_switch.set_active(PREVIEW_RICH_CONTENT)
    rich_content_box = _create_setting_row(
        "Preview rich content:",
        rich_content_switch,
        "Render image URLs, SVGs, and base64 images as thumbnails in the list",
    )

    # Clear search on Escape setting
    clear_search_switch = Gtk.Switch()
    clear_search_switch.set_active(CLEAR_SEARCH_ON_ESCAPE)
    clear_search_box = _create_setting_row(
        "Clear search on Escape:",
        clear_search_switch,
        "When off, Escape only unfocuses the search bar and keeps the typed query "
        "so you can navigate results with j/k",
    )

    general_box.pack_start(compact_box, False, False, 0)
    general_box.pack_start(hover_box, False, False, 0)
    general_box.pack_start(enter_paste_box, False, False, 0)
    general_box.pack_start(highlight_search_box, False, False, 0)
    general_box.pack_start(open_links_box, False, False, 0)
    general_box.pack_start(rich_content_box, False, False, 0)
    general_box.pack_start(clear_search_box, False, False, 0)
    general_frame.add(general_box)
    general_tab.pack_start(general_frame, False, False, 0)

    # ============ CLIPBOARD SECTION ============
    clipboard_frame = _create_section_frame("Clipboard")
    clipboard_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    clipboard_box.set_margin_top(10)
    clipboard_box.set_margin_bottom(10)

    # Protect Pinned Items setting
    protect_switch = Gtk.Switch()
    protect_switch.set_active(PROTECT_PINNED_ITEMS)
    protect_box = _create_setting_row(
        "Protect pinned items:",
        protect_switch,
        "Prevent pinned items from being deleted when clearing history",
    )

    clipboard_box.pack_start(protect_box, False, False, 0)
    clipboard_frame.add(clipboard_box)
    general_tab.pack_start(clipboard_frame, False, False, 0)

    # ============ SYSTEM TRAY SECTION ============
    tray_frame = _create_section_frame("System Tray")
    tray_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    tray_box.set_margin_top(10)
    tray_box.set_margin_bottom(10)

    # Minimize to Tray setting
    tray_switch = Gtk.Switch()
    tray_switch.set_active(MINIMIZE_TO_TRAY)
    tray_enable_box = _create_setting_row(
        "Minimize to system tray:",
        tray_switch,
        "Keep the app running in the system tray when closing the window",
    )

    # Tray Items Count setting
    tray_items_spin = Gtk.SpinButton.new_with_range(5, 50, 1)
    tray_items_spin.set_value(TRAY_ITEMS_COUNT)
    tray_items_box = _create_setting_row(
        "Number of tray items:",
        tray_items_spin,
        "How many recent items to show in the system tray menu",
    )

    # Tray Paste on Select setting
    tray_paste_switch = Gtk.Switch()
    tray_paste_switch.set_active(TRAY_PASTE_ON_SELECT)
    tray_paste_box = _create_setting_row(
        "Paste on select from tray:",
        tray_paste_switch,
        "Automatically paste the item when selected from the tray menu",
    )

    tray_box.pack_start(tray_enable_box, False, False, 0)
    tray_box.pack_start(tray_items_box, False, False, 0)
    tray_box.pack_start(tray_paste_box, False, False, 0)
    tray_frame.add(tray_box)
    general_tab.pack_start(tray_frame, False, False, 0)

    # Add General tab to notebook
    general_scroll = Gtk.ScrolledWindow()
    general_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    general_scroll.add(general_tab)
    notebook.append_page(general_scroll, Gtk.Label(label="General"))

    # ============ STYLE TAB ============
    style_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
    style_tab.set_margin_top(10)
    style_tab.set_margin_bottom(10)
    style_tab.set_margin_start(10)
    style_tab.set_margin_end(10)

    # Appearance Section
    appearance_frame = _create_section_frame("Appearance")
    appearance_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    appearance_box.set_margin_top(10)
    appearance_box.set_margin_bottom(10)

    # Border Radius
    radius_spin = Gtk.SpinButton.new_with_range(0, 20, 1)
    radius_spin.set_value(BORDER_RADIUS)
    radius_row = _create_setting_row(
        "Border radius:",
        radius_spin,
        "Corner roundness applied to buttons, lists, and dialogs",
    )

    # Accent Color
    accent_button = Gtk.ColorButton()
    accent_rgba = Gdk.RGBA()
    accent_rgba.parse(ACCENT_COLOR)
    accent_button.set_rgba(accent_rgba)
    accent_row = _create_setting_row(
        "Accent color (pins):",
        accent_button,
        "Color used for pinned items and pin filter button",
    )

    # Selection Color
    selection_button = Gtk.ColorButton()
    selection_rgba = Gdk.RGBA()
    selection_rgba.parse(SELECTION_COLOR)
    selection_button.set_rgba(selection_rgba)
    selection_row = _create_setting_row(
        "Selection color:",
        selection_button,
        "Color used for selected list rows and focus rings",
    )

    # Visual Mode Color
    visual_button = Gtk.ColorButton()
    visual_rgba = Gdk.RGBA()
    visual_rgba.parse(VISUAL_MODE_COLOR)
    visual_button.set_rgba(visual_rgba)
    visual_row = _create_setting_row(
        "Visual mode color:",
        visual_button,
        "Color used for multi-select / visual mode highlights",
    )

    appearance_box.pack_start(radius_row, False, False, 0)
    appearance_box.pack_start(accent_row, False, False, 0)
    appearance_box.pack_start(selection_row, False, False, 0)
    appearance_box.pack_start(visual_row, False, False, 0)

    # Reset button — right-aligned, compact, not full-width
    reset_btn = Gtk.Button(label="Reset to Defaults")
    reset_btn.set_tooltip_text("Reset all style settings to default values")
    reset_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    reset_row.set_margin_start(10)
    reset_row.set_margin_end(10)
    reset_row.set_margin_top(12)
    reset_row.set_halign(Gtk.Align.END)
    reset_row.pack_end(reset_btn, False, False, 0)
    appearance_box.pack_start(reset_row, False, False, 0)

    appearance_frame.add(appearance_box)
    style_tab.pack_start(appearance_frame, False, False, 0)

    # Add Style tab to notebook
    style_scroll = Gtk.ScrolledWindow()
    style_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    style_scroll.add(style_tab)
    notebook.append_page(style_scroll, Gtk.Label(label="Style"))

    main_box.pack_start(notebook, True, True, 0)

    # Track changes
    settings_changed = False

    # Buttons
    button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    button_box.set_homogeneous(True)
    button_box.set_margin_top(10)

    # Apply & Restart button (initially disabled)
    apply_btn = Gtk.Button(label="Apply & Restart")
    apply_btn.set_sensitive(False)

    # Close button
    close_btn = Gtk.Button(label="Close")

    def update_button_states():
        """Update the state of buttons based on whether settings have changed."""
        apply_btn.set_sensitive(settings_changed)

    def on_protect_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "protect_pinned_items", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.PROTECT_PINNED_ITEMS = switch.get_active()

    def on_compact_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "compact_mode", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.COMPACT_MODE = switch.get_active()

    def on_hover_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "hover_to_select", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.HOVER_TO_SELECT = switch.get_active()

    def on_enter_paste_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "enter_to_paste", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.ENTER_TO_PASTE = switch.get_active()

    def on_highlight_search_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "highlight_search", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.HIGHLIGHT_SEARCH = switch.get_active()

    def on_open_links_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "open_links_with_browser", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.OPEN_LINKS_WITH_BROWSER = switch.get_active()

    def on_rich_content_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "preview_rich_content", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.PREVIEW_RICH_CONTENT = switch.get_active()

    def on_clear_search_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "clear_search_on_escape", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.CLEAR_SEARCH_ON_ESCAPE = switch.get_active()

    def on_tray_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "minimize_to_tray", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.MINIMIZE_TO_TRAY = switch.get_active()
        try:
            app = parent_window.get_application()
            if hasattr(app, "tray_manager") and app.tray_manager:
                app.tray_manager.set_tray_enabled(switch.get_active())
        except Exception as e:
            logging.debug(f"Could not update tray manager dynamically: {e}")

    def on_tray_items_changed(spin):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "tray_items_count", str(int(spin.get_value())))
        config._save_config()
        import clipse_gui.constants as constants

        constants.TRAY_ITEMS_COUNT = int(spin.get_value())

    def on_tray_paste_switch_toggled(switch, state):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        if not config.config.has_section("General"):
            config.config.add_section("General")
        config.config.set("General", "tray_paste_on_select", str(switch.get_active()))
        config._save_config()
        import clipse_gui.constants as constants

        constants.TRAY_PASTE_ON_SELECT = switch.get_active()

    # Style signal handlers
    def on_radius_changed(spin):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        value = int(spin.get_value())
        if not config.config.has_section("Style"):
            config.config.add_section("Style")
        config.config.set("Style", "border_radius", str(value))
        config._save_config()
        import clipse_gui.constants as constants
        constants.BORDER_RADIUS = value
        if update_style_cb:
            update_style_cb(border_radius=value)

    def on_accent_color_changed(button):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        rgba = button.get_rgba()
        color = f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
        if not config.config.has_section("Style"):
            config.config.add_section("Style")
        config.config.set("Style", "accent_color", color)
        config._save_config()
        import clipse_gui.constants as constants
        constants.ACCENT_COLOR = color
        if update_style_cb:
            update_style_cb(accent_color=color)

    def on_selection_color_changed(button):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        rgba = button.get_rgba()
        color = f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
        if not config.config.has_section("Style"):
            config.config.add_section("Style")
        config.config.set("Style", "selection_color", color)
        config._save_config()
        import clipse_gui.constants as constants
        constants.SELECTION_COLOR = color
        if update_style_cb:
            update_style_cb(selection_color=color)

    def on_visual_color_changed(button):
        nonlocal settings_changed
        settings_changed = True
        update_button_states()
        rgba = button.get_rgba()
        color = f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
        if not config.config.has_section("Style"):
            config.config.add_section("Style")
        config.config.set("Style", "visual_mode_color", color)
        config._save_config()
        import clipse_gui.constants as constants
        constants.VISUAL_MODE_COLOR = color
        if update_style_cb:
            update_style_cb(visual_mode_color=color)

    def on_reset_styles(button):
        if not style_defaults:
            return
        # Reset to defaults
        radius_spin.set_value(style_defaults.get("border_radius", 6))

        accent_rgba = Gdk.RGBA()
        accent_rgba.parse(style_defaults.get("accent_color", "#ffcc00"))
        accent_button.set_rgba(accent_rgba)

        selection_rgba = Gdk.RGBA()
        selection_rgba.parse(style_defaults.get("selection_color", "#4a90e2"))
        selection_button.set_rgba(selection_rgba)

        visual_rgba = Gdk.RGBA()
        visual_rgba.parse(style_defaults.get("visual_mode_color", "#9b59b6"))
        visual_button.set_rgba(visual_rgba)

        # Save defaults to config
        if not config.config.has_section("Style"):
            config.config.add_section("Style")
        for key, value in style_defaults.items():
            config.config.set("Style", key, str(value))
        config._save_config()

        # Update constants and apply
        import clipse_gui.constants as constants
        constants.BORDER_RADIUS = style_defaults.get("border_radius", 6)
        constants.ACCENT_COLOR = style_defaults.get("accent_color", "#ffcc00")
        constants.SELECTION_COLOR = style_defaults.get("selection_color", "#4a90e2")
        constants.VISUAL_MODE_COLOR = style_defaults.get("visual_mode_color", "#9b59b6")

        if update_style_cb:
            update_style_cb(
                border_radius=constants.BORDER_RADIUS,
                accent_color=constants.ACCENT_COLOR,
                selection_color=constants.SELECTION_COLOR,
                visual_mode_color=constants.VISUAL_MODE_COLOR,
            )

    # Connect signals
    protect_switch.connect("state-set", on_protect_switch_toggled)
    compact_switch.connect("state-set", on_compact_switch_toggled)
    hover_switch.connect("state-set", on_hover_switch_toggled)
    enter_paste_switch.connect("state-set", on_enter_paste_switch_toggled)
    highlight_search_switch.connect("state-set", on_highlight_search_switch_toggled)
    open_links_switch.connect("state-set", on_open_links_switch_toggled)
    rich_content_switch.connect("state-set", on_rich_content_switch_toggled)
    clear_search_switch.connect("state-set", on_clear_search_switch_toggled)
    tray_switch.connect("state-set", on_tray_switch_toggled)
    tray_items_spin.connect("value-changed", on_tray_items_changed)
    tray_paste_switch.connect("state-set", on_tray_paste_switch_toggled)

    # Style signals
    radius_spin.connect("value-changed", on_radius_changed)
    accent_button.connect("color-set", on_accent_color_changed)
    selection_button.connect("color-set", on_selection_color_changed)
    visual_button.connect("color-set", on_visual_color_changed)
    reset_btn.connect("clicked", on_reset_styles)

    def on_apply_clicked(button):
        settings_window.destroy()
        if restart_app_cb:
            restart_app_cb()

    apply_btn.connect("clicked", on_apply_clicked)

    def on_close_clicked(button):
        settings_window.destroy()
        if settings_changed and restart_app_cb:
            dialog = Gtk.MessageDialog(
                transient_for=settings_window,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Settings have been changed. Restart to apply changes?",
            )
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.YES:
                restart_app_cb()

    close_btn.connect("clicked", on_close_clicked)

    button_box.pack_start(apply_btn, True, True, 0)
    button_box.pack_start(close_btn, True, True, 0)
    main_box.pack_end(button_box, False, False, 0)

    settings_window.add(main_box)
    settings_window.connect(
        "key-press-event",
        lambda w, e: close_cb(w) if e.keyval == Gdk.KEY_Escape else None,
    )
    settings_window.show_all()
    close_btn.grab_focus()
