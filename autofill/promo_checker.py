# autofill/promo_checker.py

import os

PROMO_ENABLED = os.getenv("PROMO_ENABLED", "True").lower() == "true"
PROMO_DEFAULT = os.getenv("PROMO_DEFAULT_MESSAGE", "Limited-time deal available!")
PROMO_EXPIRED = os.getenv("PROMO_EXPIRED_MESSAGE", "Price updated — deal may no longer be available.")


def promo_caption_text(promo: dict | None) -> str:
    """
    Given promo info dict from PA-API-normalized structure:
    {"has_promo": bool, "promo_text": str}
    return a single caption line (or empty if disabled).
    """
    if not PROMO_ENABLED:
        return ""

    if not promo:
        return PROMO_EXPIRED

    has_promo = promo.get("has_promo", False)
    text = (promo.get("promo_text") or "").strip()

    if has_promo and text:
        return f"✨ {text} ✨"

    if has_promo:
        return f"✨ {PROMO_DEFAULT} ✨"

    return PROMO_EXPIRED
