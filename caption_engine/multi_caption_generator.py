# modules/multi_caption_generator.py

import json
import os
import random
from pathlib import Path

from caption_engine.caption_generator import generate_affiliate_caption
from caption_engine.hashtag_generator import generate_hashtags  # fallback only

# Gemini Support (Optional)
try:
    from google.generativeai import GenerativeModel
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    gemini_model = GenerativeModel("gemini-pro") if GEMINI_API_KEY else None
except:
    gemini_model = None


# -------------------------------------------------------------
# LOAD JSON FILES
# -------------------------------------------------------------
MODULE_DIR = Path(__file__).resolve().parent

CATEGORY_JSON_PATH = MODULE_DIR / "category_hashtags.json"
TEMPLATE_JSON_PATH = MODULE_DIR / "theme_templates.json"

try:
    with open(CATEGORY_JSON_PATH, "r") as f:
        CATEGORY_DATA = json.load(f)
except:
    CATEGORY_DATA = {}

try:
    with open(TEMPLATE_JSON_PATH, "r") as f:
        THEME_TEMPLATES = json.load(f)
except:
    THEME_TEMPLATES = {}


# -------------------------------------------------------------
# MAP categories → theme groups
# -------------------------------------------------------------
THEME_MAP = {
    "Beauty": "Beauty",
    "Beauty Tools": "Beauty",
    "Electronics": "Gadgets",
    "Gadgets": "Gadgets",
    "Home": "Home",
    "Decor": "Home",
    "Kitchen": "Kitchen",
    "Cleaning": "Home",
    "Kids & Toys": "Toys",
    "Baby": "Toys",
    "Crafts": "Home",
    "Fashion": "Beauty",
    "Fitness": "Health",
    "Health": "Health",
    "Pets": "Home",
    "Office": "Home",
    "Outdoors & Camping": "Sports",
    "Sports": "Sports",
    "Automotive": "Home",
    "Garden": "Home",
    "Seasonal": "Holiday Gifts",
    "Other": "Home"
}


# -------------------------------------------------------------
# AUTO-DETECT CATEGORY
# -------------------------------------------------------------
def detect_category(product_name: str):
    name = product_name.lower()

    for category, hashtags in CATEGORY_DATA.items():
        for tag in hashtags:
            keyword = tag.replace("#", "").lower()

            if keyword in name:
                return category

    return "Other"


# -------------------------------------------------------------
# AUTO-DETECT THEME
# -------------------------------------------------------------
def detect_theme(product_name: str):
    category = detect_category(product_name)
    return THEME_MAP.get(category, "Home")


# -------------------------------------------------------------
# BENEFIT TEXT GENERATOR
# -------------------------------------------------------------
def generate_benefit_text(product_name):
    if gemini_model:
        prompt = f"Write a short benefit (max 12 words) for: {product_name}"
        try:
            res = gemini_model.generate_content(prompt)
            text = res.text.strip()
            if text:
                return text
        except:
            pass

    # Fallback
    return f"People love how useful the {product_name} is!"


# -------------------------------------------------------------
# SINGLE CAPTION BUILDER
# -------------------------------------------------------------
def build_caption(product_name, link):
    theme = detect_theme(product_name)
    benefit = generate_benefit_text(product_name)

    # Theme intro from JSON
    intro_list = THEME_TEMPLATES.get(theme, THEME_TEMPLATES.get("Home", []))
    intro_line = random.choice(intro_list).format(benefit=benefit)

    # Your existing affiliate caption
    affiliate_caption = generate_affiliate_caption(product_name, link) or ""

    # Category hashtags
    category = detect_category(product_name)
    category_tags_str = " ".join(CATEGORY_DATA.get(category, []))

    # Fallback auto hashtags
    fallback_tags = " ".join(generate_hashtags(product_name))

    fixed_tags = "#deals2spot #dealstospot #stealspotdeals"

    final = (
        f"{intro_line}\n\n"
        f"✨ {product_name} 👉 {link}\n\n"
        f"{affiliate_caption}\n\n"
        f"{category_tags_str} {fallback_tags} {fixed_tags}"
    )

    return final


# -------------------------------------------------------------
# MULTI CAPTION GENERATOR
# -------------------------------------------------------------
def generate_multiple_captions(products):
    results = []
    for p in products:
        name = p.get("name", "Product")
        link = p.get("link", "")

        caption = build_caption(name, link)

        results.append({
            "product": name,
            "link": link,
            "category": detect_category(name),
            "theme": detect_theme(name),
            "caption": caption
        })

    return results
