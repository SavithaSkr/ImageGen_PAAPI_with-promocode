# modules/composer_utils.py
from PIL import ImageFont, ImageDraw

# -----------------------------
# USER-CONTROLLED TITLE SETTINGS
# -----------------------------
TITLE_FONT = "arialbd.ttf"
TITLE_FONT_SIZE = 18
TITLE_MAX_WIDTH = 0.90   # 90% of canvas width
TITLE_LINE_SPACING = 4


def load_font(font_path, size, fallback=True):
    """Safe font loader."""
    try:
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default() if fallback else None


def wrap_text(draw: ImageDraw.Draw, text: str, font, max_width: int):
    """Wrap text based on pixel width."""
    words = text.split()
    lines = []
    current = ""

    for w in words:
        test = (current + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            lines.append(current)
            current = w

    if current:
        lines.append(current)
    return lines
