"""Pin icon creation and shake animation."""

import logging

from gi.repository import GdkPixbuf, GLib, Gtk

log = logging.getLogger(__name__)

# SVG icon data for pushpin (rotated 25 degrees to the right for a natural look)
PIN_SVG_BASE = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <g transform="rotate({angle} 12 12)">
        <path d="M16,12V4H17V2H7V4H8V12L6,14V16H11.2V22H12.8V16H18V14L16,12Z"
              fill="currentColor" stroke="currentColor" stroke-width="0.5"/>
    </g>
</svg>
"""


def create_pin_icon(is_pinned, angle=25):
    """Creates a pin icon from SVG data with color based on pinned state."""
    try:
        # Replace currentColor with actual color
        color = "#ffcc00" if is_pinned else "rgba(255,255,255,0.25)"
        svg_data = PIN_SVG_BASE.replace("currentColor", color).replace(
            "{angle}", str(angle)
        )

        # Load SVG into pixbuf
        loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
        loader.write(svg_data.encode("utf-8"))
        loader.close()
        pixbuf = loader.get_pixbuf()

        # Create image from pixbuf
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        image.get_style_context().add_class("pin-icon")
        if is_pinned:
            image.get_style_context().add_class("pinned")
        else:
            image.get_style_context().add_class("unpinned")

        return image
    except Exception as e:
        log.error(f"Error creating pin icon: {e}")
        # Fallback to label
        label = Gtk.Label(label="📌")
        return label


def animate_pin_shake(container, is_pinned):
    """Animates a gentle rotation wiggle effect by recreating the icon at different angles."""
    # Gentle rotation sequence: base angle ± small rotations
    base_angle = 25
    rotation_sequence = [
        base_angle + 8,  # Rotate right
        base_angle - 8,  # Rotate left
        base_angle + 5,  # Rotate right (less)
        base_angle - 5,  # Rotate left (less)
        base_angle,  # Back to normal
    ]

    def apply_wiggle(index):
        if index < len(rotation_sequence):
            # Remove old icon
            children = container.get_children()
            if children:
                old_icon = children[-1]
                container.remove(old_icon)

            # Create new icon with rotated angle
            new_icon = create_pin_icon(is_pinned, rotation_sequence[index])
            new_icon.set_tooltip_text("Pinned" if is_pinned else "Not Pinned")
            new_icon.set_valign(Gtk.Align.START)  # Keep top alignment
            new_icon.set_margin_top(2)  # Keep top margin
            new_icon.show()
            container.pack_end(new_icon, False, False, 0)

            GLib.timeout_add(70, apply_wiggle, index + 1)
        return False

    apply_wiggle(0)
