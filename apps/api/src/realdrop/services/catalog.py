"""Queries behind the read-only catalog endpoints.

"Current" means each variant's latest *confirmed* stretch (observations are change-only, see
pipeline/store.py); pending and rejected prices are never shown. Price history comes from
`price_daily` (pipeline/rollup.py). Only sizes seen in the product's latest collection count (see
`_current_variants`). This scans observations per request, which is fine for a few
brands; a `current_prices` table can replace these subqueries when it gets slow.
"""

import uuid
from dataclasses import dataclass, field, replace
from datetime import timedelta
from typing import Any, Literal

from sqlalchemy import ColumnClause, Select, Text, case, cast, func, literal_column, select
from sqlalchemy.dialects.postgresql import ARRAY, array, distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.models import (
    Brand,
    CollectionRun,
    PriceDaily,
    PriceObservation,
    PriceStatus,
    Product,
    ProductAttributes,
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
    TagCount,
    VariantOut,
)

# Sizes of one product are collected together, seconds apart; the same product is collected at
# most twice a day. Anything older than this, relative to the product's newest size, is a size the
# shop no longer lists.
SAME_COLLECTION = timedelta(hours=6)


def _current_variants() -> Select[*tuple[Any, ...]]:
    """Variants seen in their product's latest collection. A listing shows only the sizes in stock
    (DeFacto since 30 Oct 2026), so a size that sells out just stops appearing; and a shop that
    re-keys its sizes leaves the old ones behind. Either way the old row must not count as a
    size that is in stock now, nor set the product's price. "Seen" counts pending and rejected
    rows too, so a size whose new price is still waiting for confirmation stays."""
    obs = PriceObservation
    seen = (
        select(obs.variant_id, func.max(obs.last_seen_at).label("seen_at"))
        .group_by(obs.variant_id)
        .subquery()
    )
    ranked = (
        select(
            seen.c.variant_id,
            seen.c.seen_at,
            func.max(seen.c.seen_at).over(partition_by=Variant.product_id).label("product_seen_at"),
        )
        .join(Variant, Variant.id == seen.c.variant_id)
        .subquery()
    )
    return select(ranked.c.variant_id).where(
        ranked.c.seen_at >= ranked.c.product_seen_at - SAME_COLLECTION
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
        .where(obs.status == PriceStatus.CONFIRMED, obs.variant_id.in_(_current_variants()))
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
    attrs = ProductAttributes
    return (
        select(
            Product,
            Brand.slug,
            Brand.name,
            per_product,
            func.coalesce(attrs.style_tags, EMPTY_TEXT_ARRAY).label("style_tags"),
            func.coalesce(attrs.colors, EMPTY_TEXT_ARRAY).label("colors"),
            attrs.fit,
            attrs.formality,
        )
        .join(Brand, Brand.id == Product.brand_id)
        .join(per_product, per_product.c.product_id == Product.id)
        .outerjoin(attrs, attrs.product_id == Product.id)
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
        "style_tags": row["style_tags"],
        "colors": row["colors"],
        "fit": row["fit"],
        "formality": row["formality"],
    }


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


FacetName = Literal["brands", "category", "styles", "colors"]
EMPTY_TEXT_ARRAY = cast(array([], type_=Text), ARRAY(Text))
# Garments that can stand for a style in a photo (pipeline/categorize.py keys).
STYLE_PHOTO_CATEGORIES = (
    "tshirts",
    "shirts",
    "knitwear",
    "sweatshirts",
    "jackets",
    "suits",
    "trousers",
    "jeans",
    "tracksuits",
)
STYLE_PHOTO_PREFERENCE = {
    "old_money": "knitwear",
    "streetwear": "sweatshirts",
    "minimal": "tshirts",
    "smart_casual": "shirts",
    "classic_tailoring": "suits",
    "sporty": "tracksuits",
    "workwear": "jackets",
    "preppy": "knitwear",
    "techwear": "jackets",
    "y2k": "jeans",
}
EMPTY_JSON_ARRAY: ColumnClause[Any] = literal_column("'[]'::json")


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
    # Style tags and colours (pipeline/tagger.py vocabularies): a product matches if it has any.
    styles: tuple[str, ...] = ()
    colors: tuple[str, ...] = ()
    # Facet counting leaves out the facet's own filter (Facets docstring).
    skip: frozenset[FacetName] = field(default_factory=frozenset)


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
    if filters.styles and "styles" not in filters.skip:
        query = query.where(ProductAttributes.style_tags.overlap(list(filters.styles)))
    if filters.colors and "colors" not in filters.skip:
        query = query.where(ProductAttributes.colors.overlap(list(filters.colors)))
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
    # The total rides along as a window count, so a page is one scan of the base set, not two.
    rows = (
        await session.execute(
            query.add_columns(func.count().over().label("total_count"))
            .order_by(*order, Product.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    if rows:
        total = rows[0].total_count
    elif offset:  # past the last page: count separately so the pager still knows the size
        total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    else:
        total = 0
    items = [
        ProductCard.model_validate(_card(row[0], row[1], row[2], row._mapping)) for row in rows
    ]
    return ProductList(items=items, total=total)


async def facets(session: AsyncSession, filters: Filters = NO_FILTERS) -> Facets:
    """Counts for every facet in one round trip.

    The expensive part is the base set (each variant's current price, then one row per product).
    It is built once, as a materialised CTE, with every filter except the facet filters; each
    count then applies the facet filters on that set, leaving out its own (see Facets).
    """
    loose = replace(filters, brands=(), category=None, styles=(), colors=(), skip=frozenset())
    base = _filtered(loose).cte("base").prefix_with("MATERIALIZED")

    def where(skip: FacetName | None = None) -> list[Any]:
        conditions: list[Any] = []
        if filters.brands and skip != "brands":
            conditions.append(base.c.slug.in_(filters.brands))
        if filters.category and skip != "category":
            conditions.append(base.c.category == filters.category)
        if filters.styles and skip != "styles":
            conditions.append(base.c.style_tags.op("&&")(_text_array(filters.styles)))
        if filters.colors and skip != "colors":
            conditions.append(base.c.colors.op("&&")(_text_array(filters.colors)))
        return conditions

    def as_json(rows: Select[Any], *columns: str) -> Any:
        sub = rows.subquery()
        pair = func.json_build_array(*(sub.c[name] for name in columns))
        return (
            select(func.coalesce(func.json_agg(pair), EMPTY_JSON_ARRAY))
            .select_from(sub)
            .scalar_subquery()
        )

    totals = select(
        func.count().label("total"),
        func.min(base.c.price_minor).label("low"),
        func.max(base.c.price_minor).label("high"),
    ).where(*where())
    categories = (
        select(base.c.category, func.count().label("n"))
        .where(base.c.category.is_not(None), *where("category"))
        .group_by(base.c.category)
    )
    # One photo per category: the most recently checked product that is in stock and has one.
    images = (
        select(base.c.category, base.c.image_urls[1].label("url"))
        .where(
            base.c.category.is_not(None),
            base.c.sizes_in_stock > 0,
            func.cardinality(base.c.image_urls) > 0,
            *where("category"),
        )
        .order_by(base.c.category, base.c.observed_at.desc(), base.c.id)
        .ext(distinct_on(base.c.category))
    )
    brands = (
        select(base.c.slug, base.c.name, func.count().label("n"))
        .where(*where("brands"))
        .group_by(base.c.slug, base.c.name)
        .order_by(base.c.name)
    )

    def tag_counts(column: str, skip: FacetName) -> Select[Any]:
        values = select(func.unnest(base.c[column]).label("value")).where(*where(skip)).subquery()
        return (
            select(values.c.value, func.count().label("n"))
            .group_by(values.c.value)
            .order_by(func.count().desc(), values.c.value)
        )

    # One photo per style, like categories: the newest in-stock garment carrying the tag. Small
    # items (socks, ties, belts) make poor pictures of a style, so only clothing qualifies.
    tagged = (
        select(
            func.unnest(base.c.style_tags).label("style"),
            base.c.category,
            base.c.image_urls,
            base.c.observed_at,
            base.c.id,
        )
        .where(
            base.c.sizes_in_stock > 0,
            func.cardinality(base.c.image_urls) > 0,
            base.c.category.in_(STYLE_PHOTO_CATEGORIES),
            *where("styles"),
        )
        .subquery()
    )
    style_images = (
        select(tagged.c.style, tagged.c.image_urls[1].label("url"))
        .order_by(
            tagged.c.style,
            # The garment that says the style best first (a cardigan for old money, a hoodie
            # for streetwear), then the newest.
            case(
                *(
                    ((tagged.c.style == style) & (tagged.c.category == category), 0)
                    for style, category in STYLE_PHOTO_PREFERENCE.items()
                ),
                else_=1,
            ),
            tagged.c.observed_at.desc(),
            tagged.c.id,
        )
        .ext(distinct_on(tagged.c.style))
    )

    totals_sub = totals.subquery()
    row = (
        await session.execute(
            select(
                select(totals_sub.c.total).scalar_subquery(),
                select(totals_sub.c.low).scalar_subquery(),
                select(totals_sub.c.high).scalar_subquery(),
                as_json(categories, "category", "n"),
                as_json(images, "category", "url"),
                as_json(brands, "slug", "name", "n"),
                as_json(tag_counts("style_tags", "styles"), "value", "n"),
                as_json(tag_counts("colors", "colors"), "value", "n"),
                as_json(style_images, "style", "url"),
            )
        )
    ).one()
    (
        total,
        low,
        high,
        category_rows,
        image_rows,
        brand_rows,
        style_rows,
        color_rows,
        style_photos,
    ) = row
    image_by_key: dict[str, str] = dict(image_rows)
    photo_by_style: dict[str, str] = dict(style_photos)
    return Facets(
        total=total or 0,
        styles=[
            TagCount(key=key, count=count, image_url=photo_by_style.get(key))
            for key, count in style_rows
        ],
        colors=[TagCount(key=key, count=count) for key, count in color_rows],
        categories=[
            CategoryCount(key=key, count=count, image_url=image_by_key.get(key))
            for key, count in category_rows
        ],
        brands=[BrandCount(slug=slug, name=name, count=count) for slug, name, count in brand_rows],
        min_price_minor=low,
        max_price_minor=high,
    )


def _text_array(values: tuple[str, ...]) -> Any:
    return cast(array(list(values), type_=Text), ARRAY(Text))


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
