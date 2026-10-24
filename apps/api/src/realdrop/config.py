"""Application settings, read from environment variables and the repo-root `.env` file.

In production there is no `.env` file: the server's secret store sets real environment variables,
which always win over the file.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# src/realdrop/config.py -> parents[4] is the repo root, where docker-compose.yml and .env live.
_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/realdrop"
    redis_url: str = "redis://localhost:6379/0"

    # Free models only (CLAUDE.md rule 3). Defaults point at local Ollama.
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: SecretStr = SecretStr("ollama")
    llm_model_fast: str = "gemma4:12b"
    llm_model_main: str = "gemma4:12b"

    collector_user_agent: str = "realdrop-bot/0.1 (contact: you@example.com)"


@lru_cache
def get_settings() -> Settings:
    """Settings are read once per process; tests can call `get_settings.cache_clear()`."""
    return Settings()
