# modules/processor.py  (FINAL FIXED VERSION)

import os
import socket
import ipaddress
import logging
import requests
from urllib.parse import urlparse
from datetime import datetime
import gspread

# ----------------------------------------
# UPDATED IMPORTS FOR NEW FOLDER STRUCTURE
# ----------------------------------------
from image_engine.image_composer import compose_image
from caption_engine.caption_generator import generate_affiliate_caption
from caption_engine.comment_generator import generate_comment_prompt

# Autofill (PA-API + Promo Code Scraper)
from autofill.autofill_engine import get_product_data

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 5_000_000

COLOR_MAP = {
    "red": "#FF0000",
    "green": "#3B8132",
    "blue": "#3895D3",
    "yellow": "#FFED29",
    "orange": "#FFAE42",
}

# ---------------------------
# COLOR HANDLING
# ---------------------------
def clean_color(value: str):
    if not value:
        return "#FF0000"
    value = value.strip()
    if value.startswith("#") and len(value) == 7:
        return value.upper()
    return COLOR_MAP.get(value.lower(), "#FF0000")


# ---------------------------
# NETWORK SAFETY HELPERS
# ---------------------------
def resolve_hostname(name):
    try:
        infos = socket.getaddrinfo(name, None)
        return {i[4][0] for i in infos}
    except:
        return []


def is_private_ip(ip_str):
    try:
        return ipaddress.ip_address(ip_str).is_private
    except:
        return True


# -----------------------------------------------------------
# 🔧 FIXED: SAFE IMAGE URL VALIDATION (DO NOT CRASH ON EMPTY)
# -----------------------------------------------------------
def validate_image_url(url: str):
    """
    Allow blank image URLs so PA-API autofill can fill them.
    Reject only dangerous or malformed URLs.
    """
    if not url:
        return ""  # allow empty; autofill will replace it

    parsed = urlparse(url)

    if not parsed.scheme or not parsed.scheme.startswith("http"):
        raise ValueError("Invalid IMAGEURL format")

    ips = resolve_hostname(parsed.hostname)
    for ip in ips:
        if is_private_ip(ip):
            raise ValueError("Private IP detected in IMAGEURL")

    return url


# ---------------------------
# DOWNLOAD UTILITIES
# ---------------------------
def make_local_filename(url):
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    if not name or "." not in name:
        name = f"img_{datetime.utcnow().timestamp()}.jpg"
    return name


def download_image(url, idx):
    fn = make_local_filename(url)
    local_path = os.path.join("images", f"{idx}_{fn}")

    resp = requests.get(url, headers={"User-Agent": "Mozilla"}, timeout=30)
    resp.raise_for_status()

    content = resp.content
    if len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Image too large")

    with open(local_path, "wb") as f:
        f.write(content)

    return local_path


# ---------------------------
# UPLOAD TO FREEIMAGE
# ---------------------------
def upload_to_freeimage(path, api_key):
    endpoint = f"https://freeimage.host/api/1/upload?key={api_key}"

    with open(path, "rb") as f:
        resp = requests.post(endpoint, files={"source": f})

    resp.raise_for_status()
    return resp.json()["image"]["url"]


# ---------------------------
# MAIN GOOGLE SHEET PROCESSOR
# ---------------------------
def process_sheet(sheet, freeimage_key):

    logger.info("START processing…")

    records = sheet.get_all_records()
    headers = sheet.row_values(1)

    def ensure(col):
        if col in headers:
            return headers.index(col) + 1
        pos = len(headers) + 1
        sheet.update_cell(1, pos, col)
        headers.append(col)
        return pos

    # Ensure output columns
    col_edit = ensure("EDITED_IMAGE")
    col_pin = ensure("PINTREST_EDITED")
    col_caption = ensure("CAPTION_WITH_HASHTAG")
    col_comment = ensure("COMMENTS")

    # Ensure input columns exist so we can write autofill results back
    col_product_title = ensure("PRODUCT_TITLE")
    col_imageurl = ensure("IMAGEURL")
    col_price = ensure("PRICE")
    col_reg = ensure("REG")

    edited_results = []
    pinterest_results = []
    caption_results = []
    comment_results = []

    # For writing back autofill input fields
    product_title_results = []
    imageurl_results = []
    price_results = []
    reg_results = []

    # ----------------------------------------
    # PROCESS ROWS
    # ----------------------------------------
    for idx, row in enumerate(records, start=2):

        # ----------------------------------------------------
        # 🔧 FIXED: SAFE DEFAULTS BEFORE TRY (prevents crash)
        # ----------------------------------------------------
        existing_edited = row.get("EDITED_IMAGE") or ""
        existing_pin = row.get("PINTREST_EDITED") or ""
        existing_caption = row.get("CAPTION_WITH_HASHTAG") or ""
        existing_comment = row.get("COMMENTS") or ""

        local = None
        out1 = None
        out2 = None

        try:
            # ---------------------------
            # READ INPUTS
            # ---------------------------
            link = row.get("DEAL_URL") or ""
            product_name = row.get("PRODUCT_TITLE") or ""
            image_url = row.get("IMAGEURL") or ""
            price = row.get("PRICE") or ""
            reg = row.get("REG") or ""
            badge = row.get("BADGE") or "circle"
            raw_color = row.get("COLOR") or row.get("BADGE_COLOR")
            color = clean_color(raw_color)

            # ---------------------------
            # PA-API AUTOFILL + PROMO CODE SCRAPER (SAFE)
            # ---------------------------
            promo_data = None
            promo_code_data = None

            if link:
                try:
                    autofill = get_product_data(link)
                except Exception:
                    logger.exception("Autofill failed; proceeding with available values")
                    autofill = None

                if autofill:
                    if not product_name:
                        product_name = autofill.get("title", product_name)

                    if not image_url:
                        image_url = autofill.get("image", image_url)

                    if not price:
                        price = autofill.get("price", price)

                    if not reg:
                        reg = autofill.get("reg_price", reg)

                    promo_data = autofill.get("promo")
                    promo_code_data = autofill.get("promo_code")

            # Safety
            image_url = validate_image_url(image_url)

            # Keep autofill values to write back — append later to ensure length matches

            # ---------------------------
            # SKIP CHECKS
            # ---------------------------
            need_edit = not bool(existing_edited)
            need_pin = not bool(existing_pin)
            need_caption = not bool(existing_caption)
            need_comment = not bool(existing_comment)

            if not (need_edit or need_pin or need_caption or need_comment):
                edited_results.append([existing_edited])
                pinterest_results.append([existing_pin])
                caption_results.append([existing_caption])
                comment_results.append([existing_comment])
                # Append autofill values so the results remain the same length
                product_title_results.append([product_name])
                imageurl_results.append([image_url])
                price_results.append([price])
                reg_results.append([reg])
                continue

            # ---------------------------
            # DOWNLOAD IMAGE
            # ---------------------------
            if (need_edit or need_pin) and image_url:
                try:
                    os.makedirs("images", exist_ok=True)
                    local = download_image(image_url, idx)
                except Exception as e:
                    logger.warning(f"Failed to download image for row {idx}: {e}")
                    local = None

            link1 = existing_edited
            link2 = existing_pin

            # ---------------------------
            # COMPOSE IMAGES
            # ---------------------------
            if need_edit and local:
                out1 = compose_image(
                    local,
                    price_text=price,
                    badge_type=badge,
                    badge_color=color,
                    include_link=True,
                    reg_text=reg,
                )
                try:
                    if freeimage_key:
                        link1 = upload_to_freeimage(out1, freeimage_key)
                    else:
                        logger.info("FREEIMAGE_API_KEY not configured: skipping upload for edited image")
                        link1 = out1
                except Exception as e:
                    logger.exception("Failed to upload edited image; keeping local path or existing link")
                    link1 = out1 or existing_edited

            if need_pin and local:
                out2 = compose_image(
                    local,
                    price_text=price,
                    badge_type=badge,
                    badge_color=color,
                    include_link=False,
                    reg_text=reg,
                )
                try:
                    if freeimage_key:
                        link2 = upload_to_freeimage(out2, freeimage_key)
                    else:
                        logger.info("FREEIMAGE_API_KEY not configured: skipping upload for pinterest image")
                        link2 = out2
                except Exception as e:
                    logger.exception("Failed to upload pinterest image; keeping local path or existing link")
                    link2 = out2 or existing_pin

            # ---------------------------
            # CAPTION & COMMENT
            # ---------------------------
            caption = existing_caption
            comment_text = existing_comment

            if need_caption:
                try:
                    caption = generate_affiliate_caption(
                        product_name,
                        link,
                        promo_data,
                        promo_code_data
                    )
                except Exception:
                    logger.exception("Failed to generate caption; falling back to simple header")
                    head = "(Ad)(#CommissionEarned)"
                    header_text = f"{head}\n{product_name}" if product_name else head
                    caption = f"{header_text}\n\n👉 {link}" if link else header_text

            if need_comment:
                comment_text = generate_comment_prompt(product_name)

            # ---------------------------
            # OUTPUTS
            # ---------------------------
            edited_results.append([link1])
            pinterest_results.append([link2])
            caption_results.append([caption])
            comment_results.append([comment_text])

            # Track autofill values to write back to sheet
            product_title_results.append([product_name])
            imageurl_results.append([image_url])
            price_results.append([price])
            reg_results.append([reg])

        except Exception as e:
            logger.error(f"Row {idx} failed: {e}")

            edited_results.append([existing_edited or "ERROR"])
            pinterest_results.append([existing_pin or "ERROR"])
            caption_results.append([existing_caption or "ERROR"])
            comment_results.append([existing_comment or "ERROR"])

            # If autofill fails, preserve original inputs (or write empties)
            product_title_results.append([product_name])
            imageurl_results.append([image_url])
            price_results.append([price])
            reg_results.append([reg])

        # Cleanup
        for p in [local, out1, out2]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

    # ---------------------------
    # WRITE BACK TO SHEET
    # ---------------------------
    sheet.update(f"{chr(64 + col_edit)}2:{chr(64 + col_edit)}{len(records) + 1}", edited_results)
    sheet.update(f"{chr(64 + col_pin)}2:{chr(64 + col_pin)}{len(records) + 1}", pinterest_results)
    sheet.update(f"{chr(64 + col_caption)}2:{chr(64 + col_caption)}{len(records) + 1}", caption_results)
    sheet.update(f"{chr(64 + col_comment)}2:{chr(64 + col_comment)}{len(records) + 1}", comment_results)

    # Write back autofilled input fields so subsequent runs or other processors can use them
    sheet.update(f"{chr(64 + col_product_title)}2:{chr(64 + col_product_title)}{len(records) + 1}", product_title_results)
    sheet.update(f"{chr(64 + col_imageurl)}2:{chr(64 + col_imageurl)}{len(records) + 1}", imageurl_results)
    sheet.update(f"{chr(64 + col_price)}2:{chr(64 + col_price)}{len(records) + 1}", price_results)
    sheet.update(f"{chr(64 + col_reg)}2:{chr(64 + col_reg)}{len(records) + 1}", reg_results)

    logger.info("FINISHED processing.")
