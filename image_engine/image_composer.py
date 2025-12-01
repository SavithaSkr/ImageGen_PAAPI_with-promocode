# modules/image_composer.py

import os
from PIL import Image, ImageDraw, ImageFont
from image_engine.badge_shapes import draw_shape

# ---------------------------
# SIZES
# ---------------------------
BADGE_SIZE = 200
PRICE_FONT = 70
PRICE_FONT_SMALL = 50
#
#REG_FONT = PRICE_FONT // 2 
REG_FONT = 25      # exactly 50% of price font size
LINE_SPACING = 4

CANVAS_SIZE = (1080, 1080)
BACKGROUND_COLOR = (255, 255, 255)
MARGIN = 40

LINK_BADGE_PATH = "images/link.png"
BLACK_FRIDAY_PATH = "images/black_friday.png"
DISCLAIMER_TEXT = "*Prices are subject to change at any time."


# ---------------------------
# CONTRAST FUNCTION
# ---------------------------
def get_contrast_color(hex_color):
    hex_color = hex_color.replace("#", "")
    if len(hex_color) != 6:
        return "white"

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except:
        return "white"

    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "black" if brightness > 160 else "white"


# ---------------------------
# SPLIT PRICE INTO 1–2 LINES
# ---------------------------
def split_two_lines(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for w in words:
        test = (current + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
        if len(lines) == 2:
            break

    if current and len(lines) < 2:
        lines.append(current)

    return lines[:2]


# ---------------------------
# MAIN FUNCTION
# ---------------------------
def compose_image(
    image_path: str,
    price_text: str,
    badge_type: str = "circle",
    badge_color: str = "#FF0000",
    include_link: bool = True,
    reg_text: str = "",
    output_path: str = None
):

    # canvas
    canvas = Image.new("RGB", CANVAS_SIZE, BACKGROUND_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Black Friday badge small top-left
    if os.path.exists(BLACK_FRIDAY_PATH):
        bf = Image.open(BLACK_FRIDAY_PATH).convert("RGBA")
        scale = 0.30
        bf = bf.resize((int(bf.width * scale), int(bf.height * scale)), Image.LANCZOS)
        canvas.paste(bf, (MARGIN, MARGIN), bf)

    # Product image
    product = Image.open(image_path).convert("RGB")
    product.thumbnail((CANVAS_SIZE[0] * 0.7, CANVAS_SIZE[1] * 0.7))

    px = (CANVAS_SIZE[0] - product.width) // 2
    py = (CANVAS_SIZE[1] - product.height) // 2
    canvas.paste(product, (px, py))

    # Badge position
    bx = CANVAS_SIZE[0] - BADGE_SIZE - MARGIN
    by = MARGIN

    # Load fonts
    try:
        font_big = ImageFont.truetype("arialbd.ttf", PRICE_FONT)
        font_small = ImageFont.truetype("arialbd.ttf", PRICE_FONT_SMALL)
        font_reg = ImageFont.truetype("arial.ttf", REG_FONT)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_reg = ImageFont.load_default()

    # Text color logic
    if badge_type.lower() == "none":
        text_color = badge_color
    else:
        text_color = get_contrast_color(badge_color)

    # Price lines
    max_w = BADGE_SIZE * 0.75
    price_lines = split_two_lines(draw, price_text, font_big, max_w)
    use_font = font_small if len(price_lines) == 2 else font_big

    # ------------------------------
    # CASE A → SHAPE PRESENT
    # ------------------------------
    if badge_type.lower() != "none":

        # draw shape
        draw_shape(draw, badge_type.lower(), badge_color, bx, by, BADGE_SIZE)

        # total height of block
        height = sum(use_font.getbbox(x)[3] - use_font.getbbox(x)[1] for x in price_lines)
        height += (len(price_lines) - 1) * LINE_SPACING

        if reg_text.strip():
            height += REG_FONT + LINE_SPACING

        ty = by + (BADGE_SIZE - height) / 2

        # PRICE
        for line in price_lines:
            w = draw.textlength(line, font=use_font)
            draw.text((bx + (BADGE_SIZE - w)/2, ty), line, fill=text_color, font=use_font)
            ty += (use_font.getbbox(line)[3] - use_font.getbbox(line)[1]) + LINE_SPACING

        # REG
        if reg_text.strip():
            w = draw.textlength(reg_text, font=font_reg)
            rx = bx + (BADGE_SIZE - w) / 2
            draw.text((rx, ty), reg_text, fill="black", font=font_reg)

            # line-through
            draw.line(
                (rx, ty + REG_FONT/2, rx + w, ty + REG_FONT/2),
                fill="black", width=3
            )

    # ------------------------------
    # CASE B → NO SHAPE
    # ------------------------------
    else:

        right_x = CANVAS_SIZE[0] - MARGIN
        ty = MARGIN

        # PRICE
        for line in price_lines:
            w = draw.textlength(line, font=use_font)
            draw.text((right_x - w, ty), line, fill=text_color, font=use_font)
            ty += use_font.getbbox(line)[3] - use_font.getbbox(line)[1] + LINE_SPACING

        # REG
        if reg_text.strip():
            w = draw.textlength(reg_text, font=font_reg)
            draw.text((right_x - w, ty), reg_text, fill="black", font=font_reg)

            draw.line(
                (right_x - w, ty + REG_FONT/2, right_x, ty + REG_FONT/2),
                fill="black", width=3
            )

    # Disclaimer bottom-right
    try:
        small_font = ImageFont.truetype("arial.ttf", 24)
    except:
        small_font = ImageFont.load_default()

    dw = draw.textlength(DISCLAIMER_TEXT, font=small_font)
    draw.text(
        (CANVAS_SIZE[0] - dw - MARGIN, CANVAS_SIZE[1] - 50),
        DISCLAIMER_TEXT, fill="#777", font=small_font
    )

    # Link badge bottom-left
    if include_link and os.path.exists(LINK_BADGE_PATH):
        link = Image.open(LINK_BADGE_PATH).convert("RGBA")
        scale = 1.6
        link = link.resize((int(link.width * scale), int(link.height * scale)), Image.LANCZOS)
        canvas.paste(link, (20, CANVAS_SIZE[1] - link.height - 20), link)

    # Save result
    if output_path is None:
        base, ext = os.path.splitext(image_path)
        output_path = f"{base}_final.jpg"

    canvas.save(output_path)
    return os.path.abspath(output_path)
