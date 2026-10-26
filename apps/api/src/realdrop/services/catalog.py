"""Queries behind the read-only catalog endpoints.

"Current" means each variant's latest *confirmed* stretch (observations are change-only, see
pipeline/store.py); pending and rejected prices are never shown. Price history comes from
`price_daily` (pipeline/rollup.py). This scans observations per request, which is fine for a few
brands; a `current_prices` table can replace these subqueries when it gets slow.
"""

import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Literal

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
    BrandCount,
    BrandStats,
    CategoryCount,
    Facets,
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
        "category": product.category,
        "category_raw": product.category_raw,
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


@dataclass(frozen=True)
class Filters:
    """What the shopper narrowed the catalog to. Prices are kurus; None means "any"."""

    q: str | None = None
    brands: tuple[str, ...] = ()
    category: str | None = None
    audience: Audience | None = None
    min_price: int | None = None
    max_price: int | None = None
    on_sale: bool = False  # the shop shows an old price above today's (a claim, not a verdict)
    in_stock: bool = False
    # Facet counting leaves out the facet's own filter (Facets docstring).
    skip: frozenset[Literal["brands", "category"]] = field(default_factory=frozenset)


NO_FILTERS = Filters()


def _filtered(filters: Filters) -> Select[*tuple[Any, ...]]:
    query = _cards_query()
    columns = query.selected_columns
    if filters.q:
        # Plain substring match until hybrid search lands (Phase 6). ILIKE is not Turkish-aware
        # for İ/ı; good enough to browse.
        query = query.where(Product.title_raw.ilike(f"%{_escape_like(filters.q)}%", escape="\\"))
    if filters.brands and "brands" not in filters.skip:
        query = query.where(Brand.slug.in_(filters.brands))
    if filters.category and "category" not in filters.skip:
        query = query.where(Product.category == filters.category)
    if filters.audience:
        # Set by each collector from what the shop says (collectors/base.py RawProduct.audience).
        query = query.where(Product.audience == filters.audience)
    if filters.min_price is not None:
        query = query.where(columns.price_minor >= filters.min_price)
    if filters.max_price is not None:
        query = query.where(columns.price_minor <= filters.max_price)
    if filters.on_sale:
        query = query.where(columns.original_price_minor > columns.price_minor)
    if filters.in_stock:
        query = query.where(columns.sizes_in_stock > 0)
    return query


async def list_products(
    session: AsyncSession,
    filters: Filters = NO_FILTERS,
    *,
    sort: SortOrder = "recent",
    limit: int = 48,
    offset: int = 0,
) -> ProductList:
    query = _filtered(filters)
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


async def facets(session: AsyncSession, filters: Filters = NO_FILTERS) -> Facets:
    everything = _filtered(filters).subquery()
    total = await session.scalar(select(func.count()).select_from(everything)) or 0
    low, high = (
        await session.execute(
            select(func.min(everything.c.price_minor), func.max(everything.c.price_minor))
        )
    ).one()

    by_category = _filtered(replace(filters, skip=frozenset({"category"}))).subquery()
    category_rows = await session.execute(
        select(by_category.c.category, func.count())
        .where(by_category.c.category.is_not(None))
        .group_by(by_category.c.category)
    )
    # One photo per category: the most recently checked product that is in stock and has one.
    image_rows = await session.execute(
        select(by_category.c.category, by_category.c.image_urls[1])
        .where(
            by_category.c.category.is_not(None),
            by_category.c.sizes_in_stock > 0,
            func.cardinality(by_category.c.image_urls) > 0,
        )
        .order_by(by_category.c.category, by_category.c.observed_at.desc(), by_category.c.id)
        .ext(distinct_on(by_category.c.category))
    )
    images: dict[str, str] = {key: url for key, url in image_rows}

    by_brand = _filtered(replace(filters, skip=frozenset({"brands"}))).subquery()
    brand_rows = await session.execute(
        select(by_brand.c.slug, by_brand.c.name, func.count())
        .group_by(by_brand.c.slug, by_brand.c.name)
        .order_by(by_brand.c.name)
    )
    return Facets(
        total=total,
        categories=[
            CategoryCount(key=key, count=count, image_url=images.get(key))
            for key, count in category_rows
        ],
        brands=[BrandCount(slug=slug, name=name, count=count) for slug, name, count in brand_rows],
        min_price_minor=low,
        max_price_minor=high,
    )


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
