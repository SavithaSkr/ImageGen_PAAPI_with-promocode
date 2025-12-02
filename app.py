import sys
import os
import json
import logging
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# -------------------------------------------------------------
# PATH SETUP
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "modules"))

from modules.processor import process_sheet

# -------------------------------------------------------------
# ENVIRONMENT VARIABLES
# -------------------------------------------------------------
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")

FREEIMAGE_API_KEY = os.getenv("FREEIMAGE_API_KEY")
APP_API_KEY = os.getenv("APP_API_KEY")

SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON", "service_account.json")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# -------------------------------------------------------------
# ENSURE REQUIRED DIRECTORIES (Render does NOT create them)
# -------------------------------------------------------------
os.makedirs(os.path.join(BASE_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

# -------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------
log_file = os.path.join(BASE_DIR, "logs", "app.log")
handler = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=3)

logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)
logger.info("🚀 Starting Image Automation Server (Render Ready)")


# -------------------------------------------------------------
# FASTAPI INITIALIZATION
# -------------------------------------------------------------
app = FastAPI(title="Image Automation API", version="2.0")


# -------------------------------------------------------------
# OPENAPI (Swagger) PUBLIC ACCESS
# -------------------------------------------------------------
@app.get("/openapi.json")
def openapi_override():
    return app.openapi()


# -------------------------------------------------------------
# GOOGLE SHEET LOADER (RENDER-SAFE)
# -------------------------------------------------------------
def load_sheet():
    try:
        # Prefer GOOGLE_CREDENTIALS_JSON env (Render best practice)
        if GOOGLE_CREDENTIALS_JSON:
            logger.info("Using GOOGLE_CREDENTIALS_JSON from environment")

            # Load JSON
            info = json.loads(GOOGLE_CREDENTIALS_JSON)

            # 🔥 DEBUG: Print the service account email Render is REALLY using
            sa_email = info.get("client_email")
            logger.error(f"🔥 SERVICE ACCOUNT USED BY RENDER: {sa_email}")

            # 🔥 DEBUG: Print the project ID too
            project_id = info.get("project_id")
            logger.error(f"🔥 PROJECT ID USED: {project_id}")

            # Continue authorization
            creds = Credentials.from_service_account_info(info)
            gc = gspread.authorize(creds)

        else:
            # Fallback only for local environment
            logger.info(f"Using service_account.json file: {SERVICE_ACCOUNT_JSON}")

            gc = gspread.service_account(filename=SERVICE_ACCOUNT_JSON)

        if not SHEET_ID:
            raise RuntimeError("SHEET_ID environment variable is missing.")

        ss = gc.open_by_key(SHEET_ID)

        if SHEET_NAME:
            logger.info(f"Opening worksheet: {SHEET_NAME}")
            return ss.worksheet(SHEET_NAME)

        logger.info("Opening default sheet (sheet1)")
        return ss.sheet1

    except Exception as e:
        logger.exception("❌ Google Sheet loading failed")
        raise HTTPException(status_code=500, detail=f"Google Sheet Error: {e}")



# -------------------------------------------------------------
# API KEY VERIFICATION
# -------------------------------------------------------------
def verify_api_key(x_api_key: str, request: Request):
    public_paths = ["/docs", "/openapi.json", "/docs/oauth2-redirect", "/redoc"]

    if request.url.path in public_paths:
        return

    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")

    if x_api_key != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


# -------------------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------------------
@app.get("/health")
def health(x_api_key: str = Header(None), request: Request = None):
    verify_api_key(x_api_key, request)
    return {"status": "ok"}


# -------------------------------------------------------------
# MAIN RUN ENDPOINT
# -------------------------------------------------------------
@app.post("/run")
def run(background_tasks: BackgroundTasks,
        x_api_key: str = Header(None),
        request: Request = None):

    verify_api_key(x_api_key, request)

    logger.info("🔥 /run triggered — loading Google Sheet...")
    sheet = load_sheet()

    # Background processing (non-blocking in Render)
    background_tasks.add_task(process_sheet, sheet, FREEIMAGE_API_KEY)

    logger.info("✔ Task queued successfully.")
    return {"status": "processing_started"}
