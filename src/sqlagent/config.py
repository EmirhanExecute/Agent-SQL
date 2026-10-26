import os

from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.5-flash-lite")
DB_PATH = os.getenv("DB_PATH", "data/northwind_small.db")
MAX_ROWS = 100       # rows a query may return (enforced via LIMIT)
MAX_ATTEMPTS = 3
MEMORY_TURNS = 5     # previous turns used to rewrite a follow-up question
PREVIEW_ROWS = 20    # result rows shown to the LLM when writing the answer
