# modules/badge_shapes.py
from PIL import ImageDraw

# Shape generator for future expansion
def get_polygon_for_shape(shape_type, x, y, size):
    if shape_type.lower() == "circle":
        cx = x + size // 2
        cy = y + size // 2
        return ("circle", (cx, cy, size // 2))

    if shape_type.lower() == "starburst_15":
        center_x = x + size // 2
        center_y = y + size // 2
        points = []
        import math
        for i in range(30):  # 15 spikes → 30 points
            angle = (i / 30) * 2 * math.pi
            r = size * 0.5 if i % 2 == 0 else size * 0.35
            px = center_x + r * math.cos(angle)
            py = center_y + r * math.sin(angle)
            points.append((px, py))
        return ("polygon", points)

    if shape_type.lower() == "none":
        # No shape → Only text
        return ("none", None)

    # Default to circle
    cx = x + size // 2
    cy = y + size // 2
    return ("circle", (cx, cy, size // 2))


def draw_shape(draw: ImageDraw.Draw, shape_type, fill_color, x, y, size):
    shape, data = get_polygon_for_shape(shape_type, x, y, size)

    if shape == "circle":
        cx, cy, r = data
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill_color)

    elif shape == "polygon":
        draw.polygon(data, fill=fill_color)

    elif shape == "none":
        # Do nothing
        pass
