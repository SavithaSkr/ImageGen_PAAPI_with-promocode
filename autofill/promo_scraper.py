import os

ENABLED = os.getenv("PROMO_SCRAPER_ENABLED", "False").lower() == "true"

def extract_promo_from_html(url: str):
    """
    On local Windows: DISABLED
    On VPS Linux: ENABLED
    """

    if not ENABLED:
        return {
            "has_promo": False,
            "code": "",
            "discount": "",
            "text": ""
        }

    # VPS FULL SCRAPER BELOW
    import re
    import requests
    from bs4 import BeautifulSoup

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except:
        return {
            "has_promo": False,
            "code": "",
            "discount": "",
            "text": ""
        }

    html = soup.get_text(" ", strip=True)

    pattern1 = re.search(r"Save\s+(\d+%)\s+with\s+code\s+([A-Z0-9]{6,12})", html, re.I)
    if pattern1:
        return {
            "has_promo": True,
            "discount": pattern1.group(1),
            "code": pattern1.group(2),
            "text": f"Save {pattern1.group(1)} with code {pattern1.group(2)}"
        }

    pattern2 = re.search(r"Use\s+Code[:\s]+([A-Z0-9]{6,12})", html, re.I)
    if pattern2:
        return {
            "has_promo": True,
            "discount": "",
            "code": pattern2.group(1),
            "text": f"Use code {pattern2.group(1)}"
        }

    return {
        "has_promo": False,
        "code": "",
        "discount": "",
        "text": ""
    }
