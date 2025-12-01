# caption_engine/caption_generator.py
# FINAL VERSION with promo support + promo CODE + safe expiry hint

import logging
import random
import re

from caption_engine.hashtag_generator import generate_hashtags
from modules.gemini_safe import gemini_call
from autofill.promo_checker import promo_caption_text

REQUIRED_PREFIX = "(Ad)(#CommissionEarned)"

CATCHY_WORDS = [
    "Snag It!", "Grab It!", "Pick It!", "Spot It!",
    "DealSnag!", "TrendGrab!", "QuickGrab!", "HotPick!", "ClickSnag!"
]


def generate_affiliate_caption(product_name, link, promo_data=None, promo_code_data=None):
    logger = logging.getLogger(__name__)
    catchy = random.choice(CATCHY_WORDS)

    hashtags = generate_hashtags(product_name)

    # -----------------------------------
    # PROMO (PAAPI) — percentage or coupon box
    # -----------------------------------
    promo_line = ""
    if promo_data:
        promo_line = promo_caption_text(promo_data)

    # -----------------------------------
    # PROMO CODE BLOCK (scraped)
    # -----------------------------------
    code_block = ""
    if promo_code_data and promo_code_data.get("has_promo"):
        code = promo_code_data.get("code", "")
        discount = promo_code_data.get("discount", "")
        
        if code:
            if discount:
                code_block = f"💥 Code: {code} — {discount}\n⏳ Code may expire anytime"
            else:
                code_block = f"💥 Code: {code}\n⏳ Code may expire anytime"

    # -----------------------------------
    # Gemini formatting (structure only)
    # -----------------------------------
    prompt = f"""
Start with:
{REQUIRED_PREFIX}

Catchy word:
{catchy}

Product:
{product_name}

Link:
{link}

Rules:
- DO NOT include nicknames
- DO NOT include descriptions
- DO NOT rewrite the link
- DO NOT generate hashtags
- Use emojis only if natural
"""

    result = gemini_call(prompt)

    if result:
        content = result.strip()

        if content.startswith(REQUIRED_PREFIX):
            content = content[len(REQUIRED_PREFIX):].strip()

        for t in re.findall(r"#\w+", content):
            content = content.replace(t, "")

        content = "\n".join([l.strip() for l in content.splitlines() if l.strip()])

    # -----------------------------------
    # FINAL CAPTION FORMAT
    # -----------------------------------
    header = [
        REQUIRED_PREFIX,
        catchy,
        product_name
    ]

    if promo_line:
        header.append(promo_line)

    if code_block:
        header.append(code_block)

    header_text = "\n".join(header).strip()

    final = f"""{header_text}

👉 {link}

{hashtags}"""

    return final.strip()
