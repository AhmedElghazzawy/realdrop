from collections.abc import AsyncIterator
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.db.session import get_session
from realdrop.main import create_app


async def _get_health(session: Any) -> httpx.Response:
    app = create_app()

    async def override() -> AsyncIterator[Any]:
        yield session

    app.dependency_overrides[get_session] = override
    # ASGITransport calls the app in-process: no socket, no server.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/health")


async def test_health_ok_when_database_answers(db_session: AsyncSession) -> None:
    response = await _get_health(db_session)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


class _DeadSession:
    async def execute(self, *args: object, **kwargs: object) -> None:
        raise ConnectionRefusedError("database is down")


async def test_health_503_when_database_is_down() -> None:
    response = await _get_health(_DeadSession())
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "down"}
