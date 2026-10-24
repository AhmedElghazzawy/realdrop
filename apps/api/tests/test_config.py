"""Connection strings pasted from a host's console must work with asyncpg unchanged."""

import pytest

from realdrop.config import asyncpg_url

NEON_POOLED = (
    "postgresql://neondb_owner:secret@ep-cool-name-a1b2c3-pooler.eu-central-1.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)


def test_neon_string_as_copied_from_the_console() -> None:
    assert asyncpg_url(NEON_POOLED) == (
        "postgresql+asyncpg://neondb_owner:secret@ep-cool-name-a1b2c3.eu-central-1.aws.neon.tech"
        "/neondb?ssl=require"
    )


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://app:app@localhost:5432/realdrop",
        "postgresql+asyncpg://u:p@db.example.com/x?ssl=require",
    ],
)
def test_already_asyncpg_urls_are_unchanged(url: str) -> None:
    assert asyncpg_url(url) == url


def test_plain_postgres_scheme_gets_the_driver_and_disable_is_dropped() -> None:
    assert asyncpg_url("postgres://u:p@localhost/x?sslmode=disable") == (
        "postgresql+asyncpg://u:p@localhost/x"
    )


def test_pooler_is_only_rewritten_on_neon() -> None:
    url = "postgresql+asyncpg://u:p@my-pooler.example.com/x"
    assert asyncpg_url(url) == url
