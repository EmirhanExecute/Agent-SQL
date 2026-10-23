import os

from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.5-flash-lite")
DB_PATH = os.getenv("DB_PATH", "data/northwind_small.db")
MAX_ROWS = 100
MAX_ATTEMPTS = 3
