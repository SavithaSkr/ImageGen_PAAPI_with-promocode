## Purpose

Help AI coding agents quickly understand and work on this project: a FastAPI service that reads a Google Sheet, downloads products images, composes promotional images, generates captions/comments using Gemini, uploads images to FreeImage, and writes results back to the sheet.

## Big picture

- app.py: FastAPI server and entrypoint. Exposes POST /run that queues the `process_sheet` background job.
- modules/processor.py: Central connector: reads Google Sheet, validates inputs, downloads images, composes images (`image_composer.compose_image`), uploads to FreeImage, generates captions/comments and writes back. This file shows the end-to-end data flow.
- modules/gemini_safe.py: Thin wrapper around `google-generativeai` — NOTE: the module validates `GEMINI_API_KEY` at import-time and raises if unset; set `GEMINI_API_KEY` for all local runs.
- modules/image_composer.py & modules/badge_shapes.py: Image composition and shape drawing. Uses PIL; falls back when fonts aren't available.
- modules/\*.py for caption/hashtag/comment generation: Shows prompt design, content rules, and how model output is used as a direct return value (string). Example: `generate_affiliate_caption(product_name, link)`.

## Key run & dev workflows

- Set up environment variables in `.env`:
  - `GEMINI_API_KEY` (required at import time), `SHEET_ID`, `FREEIMAGE_API_KEY`, `APP_API_KEY`, `SERVICE_ACCOUNT_JSON`.
- Run the service (PowerShell):

```powershell
.
# set up virtualenv (if needed)
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app:app --reload
```

- OR use provided scripts: `./run.ps1` or `./run_app.ps1`.
- The /run endpoint: POST /run with header `x-api-key: <APP_API_KEY>` triggers processing in the background. Example:

```bash
curl -X POST http://127.0.0.1:8000/run -H "x-api-key: isthismykeynewkey123"
```

## Project-specific conventions & caveats

- Column names the project expects (case-sensitive in sheet):
  - Input: `IMAGEURL`, `PRODUCT_TITLE`, `DEAL_URL`, `PRICE`, `BADGE`, `REG`, `COLOR` or `BADGE_COLOR`
  - Output created if missing: `EDITED_IMAGE`, `PINTREST_EDITED`, `CAPTION_WITH_HASHTAG`, `COMMENTS`
- `processor.py` uses `sheet.get_all_records()` and `sheet.update(...)` with a column-letter mapped via `chr(64 + col)` — this fails beyond column 26 (A–Z); update logic if you need >26 columns.
- `gemini_safe.py` requires a `GEMINI_API_KEY` when importing — this is deliberate to avoid accidental runs without the model key. Consider refactoring to avoid import-time failure in tests.
- Network safety: `validate_image_url()` rejects non-http schemes and private IPs; do not remove this without understanding the security risk.
- `download_image()` enforces `MAX_DOWNLOAD_BYTES = 5_000_000` and `requests.get(... timeout=30)` — follow these limits for stability.

## Integration & external services

- Google Sheets: Uses `gspread` with `service_account.json` via the `SERVICE_ACCOUNT_JSON` env var. The `service_account.json` file must exist and be valid.
- Gemini: `google-generativeai` client via `modules/gemini_safe` (MODEL_NAME=`gemini-1.5-flash`). Prompts are string-based and may include required labels (see `REQUIRED_PREFIX` in `caption_generator.py`).
  - Note: `modules/gemini_safe` has been made tolerant of missing `GEMINI_API_KEY` so you can run local tests without a key. When the API key is missing or Gemini calls fail the project now uses deterministic fallbacks for captions, hashtags, and comments. Hashtag fallbacks now use the product category rather than the product name to generate relevant tags; a simple local category heuristic is applied when Gemini is not configured. When testing or debugging:
    - Check `logs/app.log` for Gemini errors or exceptions (the wrapper logs stack traces).
    - Confirm `GEMINI_API_KEY` is set in your `.env` and valid before running the app if you need model-generated text.
- FreeImage: Image uploads use `https://freeimage.host/api/1/upload?key=<FREEIMAGE_API_KEY>`.

## Files to reference while making changes

- `app.py`: entrypoint; sets environment variables and implements API-key check and background task wiring.
- `modules/processor.py`: core flow (validate, download, compose, upload, generate text, update sheet).
- `modules/image_composer.py`, `modules/badge_shapes.py`: visual layout, fonts, badges, fallback behavior.
- `modules/gemini_safe.py`: wrapper and model config.
- `modules/caption_generator.py`, `modules/comment_generator.py`, `modules/hashtag_generator.py`: prompt-only logic for text generation; do not change the prompt rules blindly.
  - These modules now implement deterministic fallbacks so they return meaningful text even when Gemini is disabled or failing. Hashtag fallbacks are now category-driven (via `modules/hashtag_generator.py`) and call a lightweight category heuristic when Gemini is unavailable. Look at `unwanteted/test_dynamic_fallback.py` for a simple way to test this behavior locally.

## Typical work items & examples for AI agents

- Adding a new badge shape: Update `modules/badge_shapes.py` → add polygon generator → add unit test using `unwanteted/image_composer_test.py` sample.
- When adding environment keys, update `.env` or `run_app.ps1` and document in this file.
- If changing the sheet schema, update `processor.py` ensure() logic and tests; be cautious with column-letter mapping.

## Tests & experimentation

- There is no formal test suite. Quick experiments or manual tests live in `unwanteted/` (e.g., `edit_sheet_images.py`, `image_composer_test.py`).
- To run quick local steps, use `unwanteted/connect_sheet.py` or `unwanteted/edit_sheet_images.py` after populating `.env`.

## Security & sensitive data

- Do not commit `service_account.json`, `.env`, or API keys to version control. The `.env` file currently contains example values — replace with private keys in your environment.

## What not to change without review

- `validate_image_url` logic and network checks — they prevent SSRF and internal network scanning.
- `GEMINI_API_KEY` import-time validation unless you deliberately modify runtime behavior in tests.
- Changing output sheet column names without updating `processor.py`.

---

If anything here is unclear or missing (prompts, workflows, or edge cases), list them and I'll iterate. ✅
