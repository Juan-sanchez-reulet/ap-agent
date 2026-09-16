from typing import Any, cast

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.rate_limiters import InMemoryRateLimiter

from apagent.config import Settings


def build_rate_limiter(requests_per_minute: float) -> InMemoryRateLimiter:
    """Keep requests under the provider's free-tier limit (no bursts)."""
    return InMemoryRateLimiter(
        requests_per_second=requests_per_minute / 60,
        check_every_n_seconds=0.1,
        max_bucket_size=1,
    )


def get_chat_model(settings: Settings) -> BaseChatModel:
    if settings.model.startswith("google_genai:") and settings.google_api_key is None:
        raise RuntimeError("GOOGLE_API_KEY is not set (see .env.example)")
    kwargs: dict[str, Any] = {
        "temperature": 0,
        "max_retries": 5,
        "rate_limiter": build_rate_limiter(settings.requests_per_minute),
    }
    if settings.google_api_key is not None:
        kwargs["api_key"] = settings.google_api_key.get_secret_value()
    return cast(BaseChatModel, init_chat_model(settings.model, **kwargs))
