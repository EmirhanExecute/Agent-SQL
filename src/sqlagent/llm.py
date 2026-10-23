from langchain_google_genai import ChatGoogleGenerativeAI

from .config import MODEL_NAME


def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0)


def text_of(msg) -> str:
    """Gemini returns content as a list of blocks; flatten to plain text."""
    c = msg.content
    if isinstance(c, str):
        return c
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in c)


def tokens_of(msg) -> int:
    return (getattr(msg, "usage_metadata", None) or {}).get("total_tokens", 0)
