"""Async engine and session factory.

One engine per process. Request handlers get a session through the `get_session` dependency,
so tests can swap it for a session bound to a rolled-back transaction.
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from realdrop.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    # pool_pre_ping drops connections that died while idle (e.g. after a Postgres restart).
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False keeps loaded attributes readable after commit, which async code needs:
    # an expired attribute would trigger lazy IO outside an awaitable context.
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, closed afterwards."""
    async with get_sessionmaker()() as session:
        yield session
