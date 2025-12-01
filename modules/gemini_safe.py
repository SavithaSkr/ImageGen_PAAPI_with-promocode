import os
import logging
import google.generativeai as genai

# Load key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Only raise if the app absolutely requires Gemini at import time; allow
# GEMINI_API_KEY to be missing in dev/test scenarios to reduce friction.
if GEMINI_API_KEY is None:
    # We intentionally do not raise here to allow local testing where the key
    # is not available. Individual callers should handle `None` returns.
    logging.getLogger(__name__).info(
        "GEMINI_API_KEY is not configured; Gemini generative features will be disabled. "
        "To enable Gemini, set GEMINI_API_KEY in your environment or .env file."
    )
else:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-1.5-flash"

def gemini_call(prompt):
    """
    Safe Gemini wrapper:
    - returns generated text
    - handles failures gracefully
    """

    logger = logging.getLogger(__name__)

    if GEMINI_API_KEY is None:
        logger.debug("Skipping Gemini call; GEMINI_API_KEY is not configured")
        return None

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        # Log exception with stack trace to help debugging when Gemini calls fail
        logger.exception("Gemini call failed")
        return None
