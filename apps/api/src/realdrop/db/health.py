"""Database health check, used by `GET /health`."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


async def database_is_up(session: AsyncSession) -> bool:
    """Run a trivial query. Any database or connection error means "down", never an exception."""
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        return False
    return True
