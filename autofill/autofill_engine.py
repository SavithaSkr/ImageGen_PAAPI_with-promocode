# autofill/autofill_engine.py
# FINAL VERSION — PAAPI + Promo Code Scraper

import logging
from urllib.parse import urlparse
from autofill.asin_extractor import extract_asin
from autofill.paapi_autofill import fetch_product_data
from autofill.promo_scraper import extract_promo_from_html

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

import re
import json

logger = logging.getLogger(__name__)

def get_product_data(url: str) -> dict:
    """
    Unified autofill engine.
    Returns:
    {
        "asin": "",
        "title": "",
        "image": "",
        "price": "",
        "reg_price": "",
        "promo": { has_promo, promo_text },
        "promo_code": { has_promo, code, discount, text }
    }
    """

    base = {
        "asin": "",
        "title": "",
        "image": "",
        "price": "",
        "reg_price": "",
        "promo": {
            "has_promo": False,
            "promo_text": ""
        },
        "promo_code": {
            "has_promo": False,
            "code": "",
            "discount": "",
            "text": ""
        }
    }

    if not url:
        return base

    try:
        asin = extract_asin(url)
        base["asin"] = asin

        # --- PA-API autofill ---
        pa = fetch_product_data(asin)
        for k in ["title", "image", "price", "reg_price", "promo"]:
            base[k] = pa.get(k, base[k])

        # --- PROMO CODE SCRAPER ---
        promo_code = extract_promo_from_html(url)
        base["promo_code"] = promo_code

        # --- FALLBACK: HTML scraping if PA-API didn't return enough (title/image/price/reg) ---
        # We will attempt to fetch the HTML and parse common meta tags, JSON-LD and domain-specific selectors
        if (not base.get("title") or not base.get("image") or not base.get("price") or not base.get("reg_price")) and HAS_BS4:
            try:
                r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                og_title = soup.find("meta", property="og:title")
                og_image = soup.find("meta", property="og:image")
                if og_title and not base.get("title"):
                    base["title"] = og_title.get("content", base.get("title", ""))
                if og_image and not base.get("image"):
                    base["image"] = og_image.get("content", base.get("image", ""))
                # Basic price scraping (amazon): #priceblock_ourprice or #priceblock_dealprice
                if not base.get("price"):
                    price_el = soup.find(id="priceblock_ourprice") or soup.find(id="priceblock_dealprice")
                    if price_el:
                        base["price"] = price_el.get_text(strip=True)
                # Regular/list price (strikethrough) or ListPrice meta
                if not base.get("reg_price"):
                    reg_el = soup.find("span", attrs={"class": "priceBlockStrikePriceString"}) or soup.find(id="priceblock_listprice")
                    if reg_el:
                        base["reg_price"] = reg_el.get_text(strip=True)
                # Attempt JSON-LD parsing for price info
                if (not base.get("price") or not base.get("reg_price")):
                    # collect JSON-LD script tags
                    for script in soup.find_all("script", type="application/ld+json"):
                        try:
                            data = json.loads(script.string)
                        except Exception:
                            continue
                        if isinstance(data, list):
                            for item in data:
                                p, r = _parse_price_from_ld(item)
                                if p and not base.get("price"):
                                    base["price"] = p
                                if r and not base.get("reg_price"):
                                    base["reg_price"] = r
                        else:
                            p, r = _parse_price_from_ld(data)
                            if p and not base.get("price"):
                                base["price"] = p
                            if r and not base.get("reg_price"):
                                base["reg_price"] = r

                # Domain-specific fallbacks: try usual tags for common sites
                try:
                    host = urlparse(url).hostname or ""
                    host = host.lower()
                    p, r = _domain_price_guess(soup, host)
                    if p and not base.get("price"):
                        base["price"] = p
                    if r and not base.get("reg_price"):
                        base["reg_price"] = r
                except Exception:
                    pass

                # Final regex fallback: find currency patterns in page text
                if not base.get("price"):
                    text = soup.get_text(" ", strip=True)
                    m = re.search(r"([$£€]\s?\d{1,3}(?:[.,]\d{2})?)", text)
                    if m:
                        base["price"] = m.group(1)

                # If we have both price and reg_price, compute % promo
                if base.get("price") and base.get("reg_price") and not base.get("promo", {}).get("has_promo"):
                    # compute numeric values
                    pv = _to_number(base.get("price"))
                    rv = _to_number(base.get("reg_price"))
                    if pv and rv and rv > pv:
                        pct = int(round((rv - pv) * 100 / rv))
                        base["promo"] = {"has_promo": True, "promo_text": f"Save {pct}% Today!"}
            except Exception:
                # fallback silently if we can't scrape
                pass

        return base

    except Exception as e:
        logger.error(f"get_product_data failed: {e}")
        return base


def _to_number(s: str):
    """Convert price like $12.34, 12.34, €12.34 to float or None"""
    if not s:
        return None
    try:
        # Remove non-numeric characters except dot and comma
        s2 = s.strip()
        s2 = re.sub(r"[^0-9.,-]", "", s2)
        # Normalize comma as decimal if there's no dot
        if s2.count(',') == 1 and '.' not in s2:
            s2 = s2.replace(',', '.')
        # Remove commas used as thousands separator
        if s2.count(',') > 1:
            s2 = s2.replace(',', '')
        s2 = s2.replace(',', '')
        return float(s2)
    except Exception:
        return None


def _parse_price_from_ld(ld):
    """Parse JSON-LD structured data to extract price and regular price"""
    price = None
    reg_price = None
    try:
        if not ld:
            return (None, None)
        # Common structure: ld['offers'] or ld['@type']==Product with offers
        offers = ld.get('offers') if isinstance(ld, dict) else None
        if offers:
            if isinstance(offers, list):
                o = offers[0]
            else:
                o = offers
            price = o.get('price') or o.get('priceSpecification', {}).get('price')
            # List price could be 'priceValidUntil' or 'priceCurrency'? Try priceSpecification
            if isinstance(o, dict):
                reg_price = o.get('priceSpecification', {}).get('originalPrice') or o.get('listPrice')
        # Some LD directly has 'price' or 'aggregateRating'
        if not price and isinstance(ld, dict):
            price = ld.get('price') or ld.get('offers', {}).get('price') if isinstance(ld.get('offers', {}), dict) else None
        return (str(price) if price else None, str(reg_price) if reg_price else None)
    except Exception:
        return (None, None)


def _domain_price_guess(soup, host):
    """Attempt to find price and reg price using domain-specific selectors or common heuristics."""
    price = None
    reg_price = None
    # Amazon (some additional selectors)
    if 'amazon.' in host:
        price_el = soup.find(id='priceblock_ourprice') or soup.find(id='priceblock_dealprice')
        if price_el:
            price = price_el.get_text(strip=True)
        reg_el = soup.find(id='priceblock_listprice') or soup.find(attrs={'class': 'priceBlockStrikePriceString'})
        if reg_el:
            reg_price = reg_el.get_text(strip=True)
    elif 'walmart.' in host:
        # Walmart item prop
        p = soup.find('span', itemprop='price') or soup.find('span', attrs={'class': re.compile(r'price|Price|price-characteristic')})
        if p:
            price = p.get_text(strip=True)
        # Regular price we inspect if there's a 'was-price' or strike inside
        reg = soup.find(attrs={'class': re.compile(r'was-price|price-old|price-strike|reg-price', re.I)})
        if reg:
            reg_price = reg.get_text(strip=True)
    elif 'bestbuy.' in host:
        p = soup.find('div', attrs={'class': re.compile(r'priceView|pricing')})
        if p:
            s = p.find('span', itemprop='price') or p.find('span', attrs={'class': re.compile(r'price|vitals-price')})
            if s:
                price = s.get_text(strip=True)
        reg = soup.find(attrs={'class': re.compile(r'was-price|pricing-old|price-strike', re.I)})
        if reg:
            reg_price = reg.get_text(strip=True)
    elif 'ebay.' in host:
        p = soup.find('meta', itemprop='price') or soup.find('span', itemprop='price')
        if p:
            price = p.get('content') if p.name == 'meta' else p.get_text(strip=True)
        reg = soup.find(attrs={'class': re.compile(r'oldprice|wasprice|priceold', re.I)})
        if reg:
            reg_price = reg.get_text(strip=True)
    else:
        # Generic search within intended container elements
        p = soup.find(attrs={'class': re.compile(r'price|Price|product-price', re.I)})
        if p:
            price = p.get_text(strip=True)
        reg = soup.find(attrs={'class': re.compile(r'was-price|price-old|reg-price|price-strike|original', re.I)})
        if reg:
            reg_price = reg.get_text(strip=True)

    return (price, reg_price)
