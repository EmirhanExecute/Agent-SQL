"""Few-shot retrieval: embed train (question, SQL) pairs and return the nearest ones for a new question."""
import hashlib
import json
import os
import threading
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml
from langchain_google_genai import GoogleGenerativeAIEmbeddings

EMB_MODEL = "gemini-embedding-001"
EMB_CACHE = Path("eval/.cache/emb.json")
QUESTIONS_PATH = "eval/questions.yaml"


_LOCK = threading.Lock()
_MEM: dict | None = None


def _load_cache() -> dict:
    global _MEM
    if _MEM is None:
        try:
            _MEM = json.loads(EMB_CACHE.read_text()) if EMB_CACHE.exists() else {}
        except json.JSONDecodeError:  # corrupt file from an interrupted write: rebuild
            _MEM = {}
    return _MEM


def _embed(texts: list[str]) -> np.ndarray:
    """Thread-safe: one lock around cache access, atomic file replace on write."""
    with _LOCK:
        cache = _load_cache()
        keys = [hashlib.sha256(t.encode()).hexdigest() for t in texts]
        missing = [(k, t) for k, t in zip(keys, texts) if k not in cache]
        if missing:
            vecs = GoogleGenerativeAIEmbeddings(model=EMB_MODEL).embed_documents([t for _, t in missing])
            cache.update({k: v for (k, _), v in zip(missing, vecs)})
            EMB_CACHE.parent.mkdir(parents=True, exist_ok=True)
            tmp = EMB_CACHE.with_suffix(".tmp")
            tmp.write_text(json.dumps(cache))
            os.replace(tmp, EMB_CACHE)
        arr = np.array([cache[k] for k in keys], dtype=np.float32)
    return arr / np.linalg.norm(arr, axis=1, keepdims=True)


class ExampleStore:
    def __init__(self, examples: list[dict]):
        assert all(e.get("split") == "train" for e in examples), "only train examples may be used as few-shot"
        self.examples = examples
        self.vecs = _embed([e["q"] for e in examples])

    def top_k(self, question: str, k: int = 3) -> list[dict]:
        sims = self.vecs @ _embed([question])[0]
        return [self.examples[i] for i in np.argsort(-sims)[:k] if self.examples[i]["q"] != question]


@lru_cache(maxsize=1)
def get_store() -> ExampleStore:
    items = yaml.safe_load(Path(QUESTIONS_PATH).read_text(encoding="utf-8"))
    return ExampleStore([e for e in items if e["split"] == "train"])
