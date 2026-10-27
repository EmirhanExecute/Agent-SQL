import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODELS = {"gemini": "gemini-3.5-flash-lite", "anthropic": "claude-haiku-5-5"}
PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()   # "gemini" or "anthropic"
if PROVIDER not in DEFAULT_MODELS:
    raise ValueError(f"LLM_PROVIDER must be one of {sorted(DEFAULT_MODELS)}, got {PROVIDER!r}")
MODEL_NAME = os.getenv("MODEL_NAME") or DEFAULT_MODELS[PROVIDER]
DB_PATH = os.getenv("DB_PATH", "data/northwind_small.db")
MAX_ROWS = 100       # rows a query may return (enforced via LIMIT)
MAX_ATTEMPTS = 3
MEMORY_TURNS = 5     # previous turns used to rewrite a follow-up question
PREVIEW_ROWS = 20    # result rows shown to the LLM when writing the answer
