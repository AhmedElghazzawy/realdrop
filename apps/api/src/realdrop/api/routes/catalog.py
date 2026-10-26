"""Read-only catalog endpoints for the web app. Thin: the queries live in services/catalog.py."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.db.session import get_session
from realdrop.schemas.catalog import (
    Audience,
    Facets,
    ProductDetail,
    ProductList,
    SortOrder,
    StatsOut,
)
from realdrop.services import catalog

router = APIRouter(tags=["catalog"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/stats", response_model=StatsOut)
async def stats(session: Session) -> StatsOut:
    """What has been collected: per-brand counts and the latest collection runs."""
    return await catalog.stats(session)


def _filters(
    q: Annotated[str | None, Query(max_length=100)] = None,
    brand: Annotated[list[str], Query(max_length=20)] = [],  # noqa: B006 (FastAPI copies it)
    category: Annotated[str | None, Query(max_length=16)] = None,
    audience: Audience | None = None,
    min_price: Annotated[int | None, Query(ge=0, description="kurus")] = None,
    max_price: Annotated[int | None, Query(ge=0, description="kurus")] = None,
    on_sale: bool = False,
    in_stock: bool = False,
) -> catalog.Filters:
    """Query parameters shared by the list and its facets; `brand` may repeat."""
    return catalog.Filters(
        q=q,
        brands=tuple(b[:64] for b in brand),
        category=category,
        audience=audience,
        min_price=min_price,
        max_price=max_price,
        on_sale=on_sale,
        in_stock=in_stock,
    )


FiltersDep = Annotated[catalog.Filters, Depends(_filters)]


@router.get("/products", response_model=ProductList)
async def products(
    session: Session,
    filters: FiltersDep,
    sort: SortOrder = "recent",
    limit: Annotated[int, Query(ge=1, le=100)] = 48,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductList:
    return await catalog.list_products(session, filters, sort=sort, limit=limit, offset=offset)


@router.get("/products/facets", response_model=Facets)
async def product_facets(session: Session, filters: FiltersDep) -> Facets:
    """Counts per category and brand, and the price range, for the filter panel and menus."""
    return await catalog.facets(session, filters)


@router.get("/products/{product_id}", response_model=ProductDetail)
async def product(session: Session, product_id: uuid.UUID) -> ProductDetail:
    detail = await catalog.product_detail(session, product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="product not found")
    return detail
