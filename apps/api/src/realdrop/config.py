"""Application settings, read from environment variables and the repo-root `.env` file.

In production there is no `.env` file: the server's secret store sets real environment variables,
which always win over the file.
"""

from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import SecretStr, field_validator
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

    collector_user_agent: str = "realdrop-bot/0.1 (+https://github.com/AhmedElghazzawy/realdrop)"

    @field_validator("database_url")
    @classmethod
    def _asyncpg_url(cls, url: str) -> str:
        return asyncpg_url(url)


def asyncpg_url(url: str) -> str:
    """Accept a connection string exactly as Neon (or any host) shows it and make it asyncpg-ready.

    `postgresql://u:p@ep-x-pooler.eu-central-1.aws.neon.tech/db?sslmode=require&channel_binding=require`
    -> `postgresql+asyncpg://u:p@ep-x.eu-central-1.aws.neon.tech/db?ssl=require`

    - Driver prefix `postgresql+asyncpg`.
    - libpq-only options (`sslmode`, `channel_binding`) are not understood by asyncpg; `sslmode`
      becomes asyncpg's `ssl`.
    - Neon's pooled host (`-pooler`) runs PgBouncer in transaction mode, which breaks asyncpg's
      prepared statements; the direct host is the same name without `-pooler`. A job that opens a
      handful of connections does not need the pooler.
    """
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    netloc = parts.netloc
    if netloc.endswith(".neon.tech"):
        netloc = netloc.replace("-pooler.", ".", 1)
    query = dict(parse_qsl(parts.query))
    query.pop("channel_binding", None)
    sslmode = query.pop("sslmode", None)
    if sslmode and sslmode != "disable" and "ssl" not in query:
        query["ssl"] = sslmode
    return urlunsplit((scheme, netloc, parts.path, urlencode(query), parts.fragment))


@lru_cache
def get_settings() -> Settings:
    """Settings are read once per process; tests can call `get_settings.cache_clear()`."""
    return Settings()
