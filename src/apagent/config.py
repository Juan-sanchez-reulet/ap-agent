from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APAGENT_", extra="ignore")

    google_api_key: SecretStr | None = Field(default=None, validation_alias="GOOGLE_API_KEY")
    model: str = "google_genai:gemini-2.5-flash"
    requests_per_minute: float = 10.0
    cache_dir: Path = Path(".cache/llm")
