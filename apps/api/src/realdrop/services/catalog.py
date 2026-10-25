"""Queries behind the read-only catalog endpoints.

"Current" means each variant's latest *confirmed* stretch (observations are change-only, see
pipeline/store.py); pending and rejected prices are never shown. Price history comes from
`price_daily` (pipeline/rollup.py). This scans observations per request, which is fine for a few
brands; a `current_prices` table can replace these subqueries when it gets slow.
"""

import uuid
from typing import Any

from sqlalchemy import Select, case, func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.models import (
    Brand,
    CollectionRun,
    PriceDaily,
    PriceObservation,
    PriceStatus,
    Product,
    Variant,
)
from realdrop.schemas.catalog import (
    Audience,
    BrandStats,
    PricePoint,
    ProductCard,
    ProductDetail,
    ProductList,
    RunOut,
    SortOrder,
    StatsOut,
    VariantOut,
)


def _latest_per_variant() -> Select[*tuple[Any, ...]]:
    obs = PriceObservation
    return (
        select(
            obs.variant_id,
            obs.price_minor,
            obs.original_price_minor,
            obs.currency,
            obs.in_stock,
            obs.last_seen_at.label("observed_at"),  # when we last checked, for "last checked"
        )
        .where(obs.status == PriceStatus.CONFIRMED)
        .order_by(obs.variant_id, obs.observed_at.desc())
        .ext(distinct_on(obs.variant_id))
    )


async def stats(session: AsyncSession, *, runs_limit: int = 20) -> StatsOut:
    observations = (
        select(Variant.product_id, func.count(PriceObservation.id).label("n"))
        .join(PriceObservation, PriceObservation.variant_id == Variant.id)
        .group_by(Variant.product_id)
        .subquery()
    )
    variants = (
        select(Variant.product_id, func.count(Variant.id).label("n"))
        .group_by(Variant.product_id)
        .subquery()
    )
    brand_rows = await session.execute(
        select(
            Brand.slug,
            Brand.name,
            func.count(Product.id),
            func.coalesce(func.sum(variants.c.n), 0),
            func.coalesce(func.sum(observations.c.n), 0),
            func.min(Product.first_seen_at),
        )
        .outerjoin(Product, Product.brand_id == Brand.id)
        .outerjoin(variants, variants.c.product_id == Product.id)
        .outerjoin(observations, observations.c.product_id == Product.id)
        .group_by(Brand.id)
        .order_by(Brand.name)
    )
    run_rows = await session.execute(
        select(CollectionRun, Brand.slug)
        .join(Brand, Brand.id == CollectionRun.brand_id)
        .order_by(CollectionRun.started_at.desc())
        .limit(runs_limit)
    )
    return StatsOut(
        brands=[
            BrandStats(
                slug=slug,
                name=name,
                products=products,
                variants=int(n_variants),
                observations=int(n_obs),
                tracking_since=since,
            )
            for slug, name, products, n_variants, n_obs, since in brand_rows
        ],
        runs=[
            RunOut(
                id=run.id,
                brand_slug=slug,
                started_at=run.started_at,
                finished_at=run.finished_at,
                status=run.status,
                items_seen=run.items_seen,
                items_failed=run.items_failed,
                notes=run.notes,
            )
            for run, slug in run_rows
        ],
    )


def _cards_query() -> Select[*tuple[Any, ...]]:
    latest = _latest_per_variant().subquery()
    per_product = (
        select(
            Variant.product_id,
            func.min(latest.c.price_minor).label("price_minor"),
            func.max(latest.c.original_price_minor).label("original_price_minor"),
            func.min(latest.c.currency).label("currency"),
            func.count().filter(latest.c.in_stock).label("sizes_in_stock"),
            func.count().label("sizes_total"),
            func.max(latest.c.observed_at).label("observed_at"),
        )
        .join(latest, latest.c.variant_id == Variant.id)
        .group_by(Variant.product_id)
        .subquery()
    )
    return (
        select(Product, Brand.slug, Brand.name, per_product)
        .join(Brand, Brand.id == Product.brand_id)
        .join(per_product, per_product.c.product_id == Product.id)
    )


def _card(product: Product, slug: str, name: str, row: Any) -> dict[str, Any]:
    return {
        "id": product.id,
        "brand_slug": slug,
        "brand_name": name,
        "title": product.title_raw,
        "url": product.url,
        "image_url": product.image_urls[0] if product.image_urls else None,
        "category": product.category_raw,
        "price_minor": row["price_minor"],
        "original_price_minor": row["original_price_minor"],
        "currency": row["currency"],
        "sizes_in_stock": row["sizes_in_stock"],
        "sizes_total": row["sizes_total"],
        "first_seen_at": product.first_seen_at,
        "observed_at": row["observed_at"],
    }


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def list_products(
    session: AsyncSession,
    *,
    q: str | None = None,
    brand: str | None = None,
    audience: Audience | None = None,
    sort: SortOrder = "recent",
    limit: int = 48,
    offset: int = 0,
) -> ProductList:
    query = _cards_query()
    if q:
        # Plain substring match until hybrid search lands (Phase 6). ILIKE is not Turkish-aware
        # for İ/ı; good enough to browse.
        query = query.where(Product.title_raw.ilike(f"%{_escape_like(q)}%", escape="\\"))
    if brand:
        query = query.where(Brand.slug == brand)
    if audience:
        # Set by each collector from what the shop says (collectors/base.py RawProduct.audience).
        query = query.where(Product.audience == audience)
    columns = query.selected_columns
    claimed = case(
        (
            columns.original_price_minor > columns.price_minor,
            (columns.original_price_minor - columns.price_minor)
            * 1000
            / columns.original_price_minor,
        ),
        else_=0,
    )
    order = {
        "recent": [columns.observed_at.desc()],
        "price_asc": [columns.price_minor.asc()],
        "price_desc": [columns.price_minor.desc()],
        "claimed_discount": [claimed.desc()],
    }[sort]
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await session.execute(query.order_by(*order, Product.id).limit(limit).offset(offset))
    items = [
        ProductCard.model_validate(_card(row[0], row[1], row[2], row._mapping)) for row in rows
    ]
    return ProductList(items=items, total=total)


async def product_detail(session: AsyncSession, product_id: uuid.UUID) -> ProductDetail | None:
    row = (await session.execute(_cards_query().where(Product.id == product_id))).first()
    if row is None:
        return None
    product, slug, name = row[0], row[1], row[2]

    latest = _latest_per_variant().subquery()
    # Sizes in the order the site lists them, i.e. the order we first stored them.
    first_seen = (
        select(PriceObservation.variant_id, func.min(PriceObservation.id).label("first_id"))
        .group_by(PriceObservation.variant_id)
        .subquery()
    )
    variant_rows = await session.execute(
        select(
            Variant.size_label,
            latest.c.in_stock,
            latest.c.price_minor,
            latest.c.original_price_minor,
        )
        .join(latest, latest.c.variant_id == Variant.id)
        .join(first_seen, first_seen.c.variant_id == Variant.id)
        .where(Variant.product_id == product_id)
        .order_by(first_seen.c.first_id)
    )

    # Per day, the cheapest any size could be bought for, next to the highest claimed original.
    history_rows = await session.execute(
        select(
            PriceDaily.snapshot_date,
            func.min(PriceDaily.low_price_minor),
            func.max(PriceDaily.claimed_original_minor),
        )
        .join(Variant, Variant.id == PriceDaily.variant_id)
        .where(Variant.product_id == product_id)
        .group_by(PriceDaily.snapshot_date)
        .order_by(PriceDaily.snapshot_date)
    )
    return ProductDetail.model_validate(
        {
            **_card(product, slug, name, row._mapping),
            "image_urls": product.image_urls,
            "variants": [
                VariantOut(
                    size_label=size, in_stock=stock, price_minor=price, original_price_minor=orig
                )
                for size, stock, price, orig in variant_rows
            ],
            "history": [
                PricePoint(day=d, price_minor=price, original_price_minor=orig)
                for d, price, orig in history_rows
            ],
        }
    )
