from pathlib import Path

import pytest

from apagent.cache import JsonFileCache
from apagent.config import Settings
from apagent.llm import get_chat_model


def test_settings_read_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("APAGENT_MODEL", "google_genai:gemini-2.5-flash-lite")
    monkeypatch.setenv("APAGENT_REQUESTS_PER_MINUTE", "5")
    settings = Settings(_env_file=None)
    assert settings.google_api_key is not None
    assert settings.google_api_key.get_secret_value() == "test-key"
    assert settings.model == "google_genai:gemini-2.5-flash-lite"
    assert settings.requests_per_minute == 5


def test_get_chat_model_requires_key_for_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        get_chat_model(Settings(_env_file=None))


def test_get_chat_model_builds_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    model = get_chat_model(Settings(_env_file=None))
    assert model.rate_limiter is not None


def test_cache_roundtrip(tmp_path: Path) -> None:
    cache = JsonFileCache(tmp_path / "llm")
    key = JsonFileCache.make_key(model="m", prompt="v1", text="hello")
    assert cache.get(key) is None
    cache.set(key, {"invoice_number": "A-1"})
    assert cache.get(key) == {"invoice_number": "A-1"}


def test_cache_key_changes_with_any_part() -> None:
    base = JsonFileCache.make_key(model="m", prompt="v1", text="hello")
    assert base == JsonFileCache.make_key(text="hello", prompt="v1", model="m")
    assert base != JsonFileCache.make_key(model="m", prompt="v2", text="hello")
