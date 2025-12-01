import logging
import re
from modules.gemini_safe import gemini_call

BRAND_TAGS = "#deals2spot #dealstospot #stealspotdeals #amazonfinds #AmazonDeals #BlackFriday "
_ALLOWED_CATEGORIES = {"beauty", "electronics", "home", "kitchen", "toys", "crafts", "fashion", "kids", "fitness", "pets", "office", "decor", "gadgets", "other"}

# Load category -> hashtags mapping from JSON file; fallback to a minimal default
import os
import json
_HERE = os.path.dirname(os.path.abspath(__file__))
_CATEGORY_FILE = os.path.join(_HERE, "category_hashtags.json")
try:
    with open(_CATEGORY_FILE, "r", encoding="utf-8") as f:
        CATEGORY_HASHTAGS = json.load(f)
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.exception("Failed to load category_hashtags.json; using minimal defaults: %s", e)
    CATEGORY_HASHTAGS = {
        "Other": ["#amazonfinds", "#musthaves", "#giftideas"],
        "Home": ["#homedecor", "#home"],
        "Kids & Toys": ["#kids", "#toys"],
        "Electronics": ["#electronics", "#gadgets"]
    }


def _heuristic_detect_category(product_name):
    """Use simple keyword matching to guess category when gemini isn't available."""
    if not product_name:
        return None
    s = product_name.lower()
    # keyword->category map (lowercase keys)
    keyword_map = {
        "earbud": "Electronics",
        "earbuds": "Electronics",
        "headphone": "Electronics",
        "headphones": "Electronics",
        "coffee": "Kitchen",
        "stainless": "Kitchen",
        "maker": "Kitchen",
        "toilet": "Home",
        "lamp": "Home",
        "sofa": "Home",
        "table": "Home",
        "block": "Toys",
        "blocks": "Toys",
        "kids": "Kids",
        "dog": "Pets",
        "cat": "Pets",
        "yoga": "Fitness",
        "workout": "Fitness",
        "dress": "Fashion",
        "skincare": "Beauty",
        "makeup": "Beauty",
        "gadget": "Gadgets",
        "charger": "Electronics",
    }
    for kw, cat in keyword_map.items():
        if kw in s:
            return cat
    return None


def _find_category_key(category_name):
    """Return the best matching JSON key for a detected category name.

    Uses simple aliases and title-case lookup; defaults to 'Other'.
    """
    if not category_name:
        return "Other"
    # direct match (case sensitive JSON keys)
    if category_name in CATEGORY_HASHTAGS:
        return category_name
    # normalized alias map
    aliases = {
        "kids": "Kids & Toys",
        "toys": "Kids & Toys",
        "gadgets": "Gadgets",
        "electronics": "Electronics",
        "decor": "Decor",
        "garden": "Garden",
        "fitness": "Fitness",
        "beauty": "Beauty",
        "kitchen": "Kitchen",
        "home": "Home",
    }
    key = aliases.get(category_name.lower())
    if key and key in CATEGORY_HASHTAGS:
        return key
    title_key = category_name.title()
    if title_key in CATEGORY_HASHTAGS:
        return title_key
    return "Other"

def detect_category(product_name):
    prompt = f"""
Based on this product name:

{product_name}

Choose ONE best category:
Beauty, Electronics, Home, Kitchen, Toys, Crafts,
Fashion, Kids, Fitness, Pets, Office, Decor, Gadgets, Other.

Return ONLY the category name.
"""
    logger = logging.getLogger(__name__)
    result = gemini_call(prompt)
    if not result:
        logger.debug("Category detection failed; trying heuristic detection")
        # try a basic local heuristic fallback based on product name keywords
        h = _heuristic_detect_category(product_name)
        if h:
            return h
        return "Home"

    try:
        cat = result.splitlines()[0].strip().lower()
    except Exception:
        cat = "home"

    # try heuristic detection in parallel
    heuristic = _heuristic_detect_category(product_name)

    # If model returned a valid category, pick it — except prefer heuristic
    # when the model returns a generic 'home' or 'other' but heuristic is
    # more specific (e.g., 'Toys' or 'Electronics')
    if cat in _ALLOWED_CATEGORIES:
        if cat in ("home", "other") and heuristic and heuristic.lower() in _ALLOWED_CATEGORIES:
            logger.debug("Model returned generic category '%s' — overriding with heuristic '%s'", cat, heuristic)
            return heuristic
        return cat.title()

    # If model returned something invalid, fallback to heuristic or Home
    if heuristic:
        logger.debug("Model returned invalid category '%s' — using heuristic '%s'", cat, heuristic)
        return heuristic

    logger.debug("Detected category not in allowed list: %s — falling back to Home", cat)
    return "Home"

def _simple_hashtags_from_category(category, max_tags=12):
    """Build a simple set of hashtags from the product category (fallback).

    The goal here is to provide category-aligned hashtags rather than deriving
    anything from the product name. We add a mix of category tags, niche tags,
    and brand tags to ensure a useful set when Gemini is offline.
    """
    
    # Helper: map category to best matching key in CATEGORY_HASHTAGS
    def _find_category_key(category_name):
        if not category_name:
            return "Other"
        if category_name in CATEGORY_HASHTAGS:
            return category_name
        aliases = {
            "kids": "Kids & Toys",
            "toys": "Kids & Toys",
            "gadgets": "Gadgets",
            "electronics": "Electronics",
            "decor": "Decor",
            "garden": "Garden",
            "fitness": "Fitness",
            "beauty": "Beauty",
            "kitchen": "Kitchen",
            "home": "Home",
        }
        key = aliases.get(category_name.lower())
        if key and key in CATEGORY_HASHTAGS:
            return key
        title_key = category_name.title()
        if title_key in CATEGORY_HASHTAGS:
            return title_key
        return "Other"

    key = _find_category_key(category)
    base = CATEGORY_HASHTAGS.get(key, CATEGORY_HASHTAGS.get("Other", []))[:max_tags]
    # We may add a few broader tags based on the category for reach
    broader = []
    if category in ("Electronics", "Gadgets"):
        broader = ["#tech", "#dealalert"]
    elif category in ("Home", "Decor", "Kitchen"):
        broader = ["#home", "#homedecor"]
    elif category in ("Beauty",):
        broader = ["#beauty", "#skincare"]

    tags = base + broader
    unique_tags = []
    for t in tags:
        if t not in unique_tags and len(unique_tags) < max_tags:
            unique_tags.append(t)
    if not unique_tags:
        return f"#giftideas #musthave {BRAND_TAGS}"
    return f"{' '.join(unique_tags)} {BRAND_TAGS}"


def _extract_hashtags(text):
    if not text:
        return []
    return re.findall(r"#\w+", text)


def generate_hashtags(product_name):
    logger = logging.getLogger(__name__)
    category = detect_category(product_name)

    prompt = f"""
Create 12–16 social media hashtags for a product in the "{category}" category.

Rules:
- NO commas
- NO line breaks
- ONLY hashtags separated by spaces
- Make them relevant and engaging
Return ONLY hashtags, separated by spaces.
"""

    # Use category mapping defined in the JSON as primary source for hashtags.
    # This ensures consistent hashtags per category. If the mapping is missing
    # or the category is 'Other', fall back to Gemini (if configured) to obtain
    # additional hashtags, and finally fallback to the JSON's 'Other' list.
    key = _find_category_key(category)
    base_tags = CATEGORY_HASHTAGS.get(key, [])[:12]

    if base_tags:
        return f"{' '.join(base_tags)} {BRAND_TAGS}"

    # If no base tags found (unlikely), fall back to Gemini and then to 'Other'
    tags_text = gemini_call(prompt)
    hashtags = _extract_hashtags(tags_text)
    if hashtags:
        unique_tags = []
        for t in hashtags:
            if t not in unique_tags:
                unique_tags.append(t)
        return f"{' '.join(unique_tags)} {BRAND_TAGS}"

    # Final fallback: use 'Other'
    return f"{' '.join(CATEGORY_HASHTAGS.get('Other', []))} {BRAND_TAGS}"
