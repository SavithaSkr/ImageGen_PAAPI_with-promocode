import logging
import random
from modules.gemini_safe import gemini_call

def generate_comment_prompt(product_name):
    """Generate a short, high-engagement comment for a product.

    Uses the Gemini wrapper `gemini_call` to request creative text. If Gemini
    is not configured or fails, returns a deterministic, product-specific
    fallback message.
    """
    logger = logging.getLogger(__name__)

    prompt = f"""
Create a short, fun, high-engagement comment message
to encourage users to comment after seeing this product:

Product: {product_name}

Examples:
"Who’s grabbing this first? Comment below! 👇🔥"
"Tell me if you’re getting it! ❤️👇"
"Let’s see who buys this first — comment DONE! 🎉"
"Would you get this? Comment YES! 👇"

Rules:
- Must be unique
- Must encourage comments
- Should feel natural for Facebook product posts
"""

    # Try Gemini first
    text = gemini_call(prompt)
    if text:
        logger.debug("Gemini comment generated")
        return text.strip()

    # Fallback: choose from pre-approved example comments (product-agnostic)
    EXAMPLE_COMMENTS = [
        "Who’s grabbing this first? Comment below! 👇🔥",
        "Tell me if you’re getting it! ❤️👇",
        "Let’s see who buys this first — comment DONE! 🎉",
        "Would you get this? Comment YES! 👇",
    ]

    fallback = random.choice(EXAMPLE_COMMENTS)
    logger.info("Using fallback comment (example): %s", fallback)
    return fallback
