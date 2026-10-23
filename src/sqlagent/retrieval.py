"""Few-shot retrieval: embed train (question, SQL) pairs and return the nearest ones for a new question."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml
from langchain_google_genai import GoogleGenerativeAIEmbeddings

EMB_MODEL = "gemini-embedding-001"
EMB_CACHE = Path("eval/.cache/emb.json")
QUESTIONS_PATH = "eval/questions.yaml"


def _load_cache() -> dict:
    return json.loads(EMB_CACHE.read_text()) if EMB_CACHE.exists() else {}


def _embed(texts: list[str]) -> np.ndarray:
    cache = _load_cache()
    keys = [hashlib.sha256(t.encode()).hexdigest() for t in texts]
    missing = [(k, t) for k, t in zip(keys, texts) if k not in cache]
    if missing:
        vecs = GoogleGenerativeAIEmbeddings(model=EMB_MODEL).embed_documents([t for _, t in missing])
        cache = _load_cache()  # re-read: another thread may have written meanwhile
        cache.update({k: v for (k, _), v in zip(missing, vecs)})
        EMB_CACHE.parent.mkdir(parents=True, exist_ok=True)
        EMB_CACHE.write_text(json.dumps(cache))
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
