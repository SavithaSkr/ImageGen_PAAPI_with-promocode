# autofill/asin_extractor.py

import logging
from urllib.parse import urlparse
import re
import requests

logger = logging.getLogger(__name__)


SHORT_DOMAINS = {"amzn.to"}


def _expand_if_short(url: str) -> str:
    """
    If URL is an Amazon short link (amzn.to), follow redirects
    to get the full URL. Otherwise return original.
    """
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host in SHORT_DOMAINS:
            resp = requests.get(url, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            return resp.url
    except Exception as e:
        logger.warning(f"Failed to expand short URL {url}: {e}")
    return url


def extract_asin(url: str) -> str:
    """
    Extract ASIN from a variety of Amazon URL formats.
    Supports normal and amzn.to short links (via redirect).
    """
    if not url:
        return ""

    final_url = _expand_if_short(url)
    patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/product/([A-Z0-9]{10})",
        r"/ASIN/([A-Z0-9]{10})",
        r"/dp/([A-Z0-9]{10})",
        r"([A-Z0-9]{10})(?:[/?]|$)",
    ]

    for p in patterns:
        m = re.search(p, final_url)
        if m:
            asin = m.group(1)
            logger.debug(f"Extracted ASIN {asin} from URL {final_url}")
            return asin

    logger.warning(f"Could not extract ASIN from URL: {final_url}")
    return ""
