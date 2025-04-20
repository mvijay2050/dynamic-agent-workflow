# app/config.py
import os
from dotenv import load_dotenv

# load .env immediately on import
load_dotenv()

# convenience getter
def get_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing OPENAI_API_KEY in environment. "
            "Please set it in your .env file."
        )
    return key
