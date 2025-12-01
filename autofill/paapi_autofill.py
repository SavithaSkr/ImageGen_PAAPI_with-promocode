# autofill/paapi_autofill.py

import os
import logging

logger = logging.getLogger(__name__)

try:
    from amazon_paapi import AmazonApi
except ImportError:
    AmazonApi = None
    logger.error("amazon_paapi library not installed. PA-API autofill will be disabled.")


def _get_client():
    """
    Build and cache the PA-API client.
    Returns None if keys are missing or library is not installed.
    """
    if AmazonApi is None:
        return None

    access_key = os.getenv("PAAPI_ACCESS_KEY")
    secret_key = os.getenv("PAAPI_SECRET_KEY")
    partner_tag = os.getenv("AMAZON_PARTNER_TAG")
    region = os.getenv("PAAPI_REGION", "us-east-1")

    if not (access_key and secret_key and partner_tag):
        logger.error("PA-API keys or tag missing in environment. Autofill disabled.")
        return None

    try:
        client = AmazonApi(
            access_key=access_key,
            secret_key=secret_key,
            partner_tag=partner_tag,
            partner_type="Associates",
            region=region,
        )
        return client
    except Exception as e:
        logger.error(f"Failed to initialize AmazonApi client: {e}")
        return None


def fetch_product_data(asin: str) -> dict:
    """
    Call PA-API for a single ASIN and return normalized product data:
    {
        "asin": str,
        "title": str,
        "image": str,
        "price": str,      # like "$29.99"
        "reg_price": str,  # like "$49.99" or ""
        "promo": {
            "has_promo": bool,
            "promo_text": str
        }
    }
    """
    base = {
        "asin": asin or "",
        "title": "",
        "image": "",
        "price": "",
        "reg_price": "",
        "promo": {
            "has_promo": False,
            "promo_text": ""
        }
    }

    if not asin:
        logger.warning("fetch_product_data called with empty ASIN.")
        return base

    client = _get_client()
    if client is None:
        return base

    try:
        resp = client.get_items(asin)
    except Exception as e:
        logger.error(f"PA-API get_items failed for {asin}: {e}")
        return base

    try:
        # Assume PA-API v5-like structure via wrapper
        if isinstance(resp, dict):
            items_result = resp.get("ItemsResult", {})
            items = items_result.get("Items", [])
            item = items[0] if items else None
        else:
            # Some wrappers may return a list-like
            items = getattr(resp, "items", None) or getattr(resp, "Items", None) or []
            item = items[0] if items else None

        if not item:
            logger.warning(f"No item found in PA-API response for ASIN {asin}")
            return base

        # TITLE
        title = (
            item.get("ItemInfo", {})
                .get("Title", {})
                .get("DisplayValue", "")
        )

        # IMAGE
        image = (
            item.get("Images", {})
                .get("Primary", {})
                .get("Large", {})
                .get("URL", "")
        )

        # PRICE & REGULAR PRICE
        offer = (item.get("Offers") or {}).get("Listings", [{}])[0]
        price_info = offer.get("Price", {}) or {}
        price_amount = price_info.get("Amount")
        list_price_amount = (
            item.get("ItemInfo", {})
                .get("ProductInfo", {})
                .get("ListPrice", {})
                .get("Amount")
        )

        price_str = ""
        if isinstance(price_amount, (int, float)):
            price_str = f"${price_amount:.2f}"
        elif price_amount is not None:
            price_str = str(price_amount)

        reg_str = ""
        if isinstance(list_price_amount, (int, float)):
            reg_str = f"${list_price_amount:.2f}"
        elif list_price_amount is not None:
            reg_str = str(list_price_amount)

        # PROMO / SAVINGS
        savings = price_info.get("Savings", {}) or {}
        percent = savings.get("Percentage")
        has_promo = False
        promo_text = ""

        if isinstance(percent, (int, float)) and percent > 0:
            has_promo = True
            promo_text = f"Save {int(percent)}% Today!"

        # Some wrappers may expose coupon info
        coupon = offer.get("Coupon") if isinstance(offer, dict) else None
        if coupon and not promo_text:
            label = coupon.get("CouponLabel") or coupon.get("BadgeText") or "Coupon available"
            has_promo = True
            promo_text = label

        base.update({
            "title": title or "",
            "image": image or "",
            "price": price_str,
            "reg_price": reg_str,
            "promo": {
                "has_promo": bool(has_promo),
                "promo_text": promo_text or ""
            }
        })
        return base

    except Exception as e:
        logger.error(f"Error parsing PA-API response for ASIN {asin}: {e}")
        return base
