"""Read-only catalog endpoints for the web app. Thin: the queries live in services/catalog.py."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.db.session import get_session
from realdrop.schemas.catalog import Audience, ProductDetail, ProductList, SortOrder, StatsOut
from realdrop.services import catalog

router = APIRouter(tags=["catalog"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/stats", response_model=StatsOut)
async def stats(session: Session) -> StatsOut:
    """What has been collected: per-brand counts and the latest collection runs."""
    return await catalog.stats(session)


@router.get("/products", response_model=ProductList)
async def products(
    session: Session,
    q: Annotated[str | None, Query(max_length=100)] = None,
    brand: Annotated[str | None, Query(max_length=64)] = None,
    audience: Audience | None = None,
    sort: SortOrder = "recent",
    limit: Annotated[int, Query(ge=1, le=100)] = 48,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductList:
    return await catalog.list_products(
        session, q=q, brand=brand, audience=audience, sort=sort, limit=limit, offset=offset
    )


@router.get("/products/{product_id}", response_model=ProductDetail)
async def product(session: Session, product_id: uuid.UUID) -> ProductDetail:
    detail = await catalog.product_detail(session, product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="product not found")
    return detail
