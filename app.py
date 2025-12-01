import sys
import os

# -------------------------------------------------------------------
# Ensure project + modules folder is on import path
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "modules"))

# -------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from dotenv import load_dotenv
import gspread

# Load environment variables early so import-time checks in modules succeed
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

from modules.processor import process_sheet


SHEET_ID = os.getenv("SHEET_ID")
FREEIMAGE_API_KEY = os.getenv("FREEIMAGE_API_KEY")
APP_API_KEY = os.getenv("APP_API_KEY")
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON", "service_account.json")
SHEET_NAME = os.getenv("SHEET_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
os.makedirs("logs", exist_ok=True)
handler = RotatingFileHandler("logs/app.log", maxBytes=10_000_000, backupCount=3)
logging.basicConfig(handlers=[handler], level=logging.INFO)
logger = logging.getLogger(__name__)
if GEMINI_API_KEY:
    logger.info("Gemini API key configured. Generative features enabled.")
else:
    logger.info("Gemini API key not configured. Generative features disabled (using deterministic fallbacks).")


# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(title="Secure Image Automation API")


# -------------------------------------------------------------------
# Allow Swagger UI to load WITHOUT API key
# -------------------------------------------------------------------
@app.get("/openapi.json")
def openapi_override():
    return app.openapi()


# -------------------------------------------------------------------
# Helper: load Google Sheet
# -------------------------------------------------------------------
def load_sheet():
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_JSON)
    ss = gc.open_by_key(SHEET_ID)

    if SHEET_NAME:
        return ss.worksheet(SHEET_NAME)
    return ss.sheet1


# -------------------------------------------------------------------
# API KEY CHECK (Swagger allowed w/o key)
# -------------------------------------------------------------------
def verify_api_key(
    x_api_key: str = Header(None),
    request: Request = None
):
    allowed_paths = [
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc"
    ]

    if request.url.path in allowed_paths:
        return  # allow Swagger UI to load

    if not x_api_key or x_api_key != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# -------------------------------------------------------------------
# Run the processor
# -------------------------------------------------------------------
@app.post("/run")
def run(background_tasks: BackgroundTasks, x_api_key: str = Header(None), request: Request = None):
    verify_api_key(x_api_key, request)

    sheet = load_sheet()
    background_tasks.add_task(process_sheet, sheet, FREEIMAGE_API_KEY)

    logger.info("Run endpoint triggered")
    return {"status": "processing_started"}


# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------
@app.get("/health")
def health(x_api_key: str = Header(None), request: Request = None):
    verify_api_key(x_api_key, request)
    return {"status": "ok"}
