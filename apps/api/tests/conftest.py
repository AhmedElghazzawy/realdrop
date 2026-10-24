"""Shared fixtures.

Database tests run against a separate `realdrop_test` database on the local Docker Postgres, never
the dev database. The schema is built by running the real Alembic migrations, so the tests also
prove the migrations work. Each test runs inside a transaction that is rolled back afterwards.

The network stays blocked (pytest-socket); tests that use `db_session` are allowed to reach
localhost only. If Postgres is not running, those tests are skipped with a hint.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from realdrop.config import get_settings

API_DIR = Path(__file__).resolve().parents[1]
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
LOCAL_IPS = ["127.0.0.1", "::1"]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "db_session" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.allow_hosts(LOCAL_IPS))


def _test_database_url() -> URL:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return make_url(explicit)
    return make_url(get_settings().database_url).set(database="realdrop_test")


async def _create_database_if_missing(url: URL) -> None:
    conn = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port or 5432,
        database="postgres",
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", url.database)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def database_url() -> str:
    url = _test_database_url()
    if url.host not in LOCAL_HOSTS or url.database in {None, "realdrop", "postgres"}:
        pytest.fail(f"refusing to run tests against {url.host}/{url.database}")
    try:
        asyncio.run(_create_database_if_missing(url))
    except OSError as exc:
        pytest.skip(f"Postgres not reachable ({exc}). Start it with `docker compose up -d`.")

    rendered = url.render_as_string(hide_password=False)
    config = Config(API_DIR / "alembic.ini")
    config.set_main_option("sqlalchemy.url", rendered.replace("%", "%%"))
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
    return rendered


@pytest.fixture
async def db_session(database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        # create_savepoint: code under test may call commit(); it only releases a savepoint, and
        # the outer transaction is still rolled back at the end.
        session = AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()
