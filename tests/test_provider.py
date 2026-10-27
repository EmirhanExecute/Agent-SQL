import importlib

import pytest

from sqlagent import llm


@pytest.fixture
def reload_config(monkeypatch):
    import sqlagent.config as cfg
    yield lambda: importlib.reload(cfg)
    monkeypatch.undo()
    importlib.reload(cfg)  # leave the module as the environment defines it


def test_default_model_follows_provider(monkeypatch, reload_config):
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    assert reload_config().MODEL_NAME == "claude-haiku-5-5"
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    assert reload_config().MODEL_NAME == "gemini-3.5-flash-lite"
    monkeypatch.setenv("MODEL_NAME", "custom-model")
    assert reload_config().MODEL_NAME == "custom-model"


def test_unknown_provider_is_rejected(monkeypatch, reload_config):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(ValueError):
        reload_config()


def test_get_llm_picks_the_configured_provider(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    monkeypatch.setattr(llm, "PROVIDER", "anthropic")
    monkeypatch.setattr(llm, "MODEL_NAME", "claude-haiku-5-5")
    assert type(llm.get_llm()).__name__ == "ChatAnthropic"
    monkeypatch.setattr(llm, "PROVIDER", "gemini")
    monkeypatch.setattr(llm, "MODEL_NAME", "gemini-3.5-flash-lite")
    assert type(llm.get_llm()).__name__ == "ChatGoogleGenerativeAI"


def test_text_of_handles_plain_and_block_content():
    class Msg:
        def __init__(self, content):
            self.content = content

    assert llm.text_of(Msg("SELECT 1")) == "SELECT 1"
    assert llm.text_of(Msg([{"type": "text", "text": "SELECT "}, {"type": "text", "text": "1"}])) == "SELECT 1"
