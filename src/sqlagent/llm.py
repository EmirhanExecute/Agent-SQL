import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from .config import MODEL_NAME, PROVIDER

CACHE_PATH = Path("eval/.cache/llm.sqlite")


@dataclass
class LLMResult:
    text: str
    tokens: int
    seconds: float  # wall time of the original (uncached) call


def get_llm():
    """Chat model for the configured provider (LLM_PROVIDER=gemini|anthropic, MODEL_NAME overrides the default)."""
    if PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=MODEL_NAME, max_tokens=2048)  # no temperature: newer Claude models reject it
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0)


def text_of(msg) -> str:
    """Models may return content as a list of blocks (Gemini always does); flatten to plain text."""
    c = msg.content
    if isinstance(c, str):
        return c
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in c)


def tokens_of(msg) -> int:
    return (getattr(msg, "usage_metadata", None) or {}).get("total_tokens", 0)


def _cache_get(key: str):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(CACHE_PATH, timeout=30) as c:
        c.execute("create table if not exists c (k text primary key, v text)")
        row = c.execute("select v from c where k = ?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def _cache_put(key: str, value: dict) -> None:
    with sqlite3.connect(CACHE_PATH, timeout=30) as c:
        c.execute("insert or replace into c values (?, ?)", (key, json.dumps(value)))


def call(messages: list[tuple[str, str]]) -> LLMResult:
    """Invoke the model with retries. LLM_CACHE=1 enables a disk cache (LLM_CACHE_SALT forces fresh samples)."""
    use_cache = os.getenv("LLM_CACHE") == "1"
    parts = [MODEL_NAME, os.getenv("LLM_CACHE_SALT", ""), messages]
    if PROVIDER != "gemini":  # gemini keeps the original key format so existing cached results stay valid
        parts.insert(0, PROVIDER)
    key = hashlib.sha256(json.dumps(parts).encode()).hexdigest()
    if use_cache and (hit := _cache_get(key)):
        return LLMResult(**hit)
    last: Exception | None = None
    for attempt in range(4):
        try:
            t0 = time.perf_counter()
            msg = get_llm().invoke(messages)
            res = LLMResult(text_of(msg).strip(), tokens_of(msg), time.perf_counter() - t0)
            if use_cache:
                _cache_put(key, res.__dict__)
            return res
        except Exception as e:  # rate limits / transient network errors
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"LLM call failed after retries: {last}")
