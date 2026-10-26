"""Storing collector output: catalog upserts, change-only observations, glitch-filter statuses,
pending expiry, run rows."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.collectors.base import RawProduct, RawVariant
from realdrop.models import (
    CollectionRun,
    PriceObservation,
    PriceStatus,
    Product,
    RunStatus,
    Variant,
)
from realdrop.pipeline import store

T0 = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
DAY = timedelta(days=1)


def coat(
    price: int = 100_000, title: str = "Siyah Kaban", sizes: tuple[str, ...] = ("S", "M")
) -> RawProduct:
    return RawProduct(
        external_id="1001",
        url="https://shop.example.com/kaban-1001",
        title=title,
        currency="TRY",
        variants=[
            RawVariant(external_sku=f"1001-{s}", size_label=s, price_minor=price, in_stock=True)
            for s in sizes
        ],
    )


async def setup(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    brand = await store.get_or_create_brand(
        session, slug="shop", name="Shop", base_url="https://shop.example.com"
    )
    run = await store.start_run(session, brand.id)
    return brand.id, run.id


async def statuses(session: AsyncSession) -> list[tuple[int, PriceStatus]]:
    rows = await session.execute(
        select(PriceObservation.price_minor, PriceObservation.status)
        .join(Variant)
        .where(Variant.external_sku == "1001-S")
        .order_by(PriceObservation.observed_at)
    )
    return [(price, status) for price, status in rows]


async def test_first_run_creates_catalog_and_confirmed_prices(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    counts = await store.store_product(
        db_session, brand_id=brand_id, run_id=run_id, raw=coat(), observed_at=T0
    )
    assert counts == {PriceStatus.CONFIRMED: 2}
    product = await db_session.scalar(select(Product).where(Product.external_id == "1001"))
    assert product is not None and product.first_seen_at == T0
    assert len(product.content_hash) == 64


async def test_second_run_updates_catalog_and_keeps_first_seen(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    await store.store_product(
        db_session, brand_id=brand_id, run_id=run_id, raw=coat(), observed_at=T0
    )
    later = coat(title="Siyah Uzun Kaban", sizes=("S", "M", "L"))
    await store.store_product(
        db_session, brand_id=brand_id, run_id=run_id, raw=later, observed_at=T0 + DAY
    )

    product = await db_session.scalar(select(Product).where(Product.external_id == "1001"))
    assert product is not None
    assert (product.title_raw, product.first_seen_at, product.last_seen_at) == (
        "Siyah Uzun Kaban",
        T0,
        T0 + DAY,
    )
    skus = await db_session.scalars(
        select(Variant.external_sku).where(Variant.product_id == product.id)
    )
    assert sorted(skus) == ["1001-L", "1001-M", "1001-S"]


async def test_category_follows_the_latest_text(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    await store.store_product(
        db_session, brand_id=brand_id, run_id=run_id, raw=coat(), observed_at=T0
    )
    product = await db_session.scalar(select(Product).where(Product.external_id == "1001"))
    assert product is not None and product.category == "jackets"  # "Siyah Kaban"

    renamed = coat(title="Siyah Yün Blazer")
    await store.store_product(
        db_session, brand_id=brand_id, run_id=run_id, raw=renamed, observed_at=T0 + DAY
    )
    await db_session.refresh(product)
    assert product.category == "suits"


async def test_glitch_is_held_then_confirmed_by_the_next_run(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    for when, price in [(T0, 100_000), (T0 + DAY, 1_000), (T0 + 2 * DAY, 1_000)]:
        await store.store_product(
            db_session, brand_id=brand_id, run_id=run_id, raw=coat(price), observed_at=when
        )
    # A real 99% drop is believed once a second run sees it too; the repeat adds no row.
    assert await statuses(db_session) == [
        (100_000, PriceStatus.CONFIRMED),
        (1_000, PriceStatus.CONFIRMED),
    ]


async def test_one_off_glitch_is_rejected_after_48h(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    for when, price in [(T0, 100_000), (T0 + DAY, 1_000), (T0 + 2 * DAY, 100_000)]:
        await store.store_product(
            db_session, brand_id=brand_id, run_id=run_id, raw=coat(price), observed_at=when
        )
    assert await store.expire_pending(db_session, T0 + 2 * DAY) == 0  # not yet 48 h
    assert await store.expire_pending(db_session, T0 + 3 * DAY + timedelta(minutes=1)) == 2
    assert await statuses(db_session) == [
        (100_000, PriceStatus.CONFIRMED),
        (1_000, PriceStatus.REJECTED),
        (100_000, PriceStatus.CONFIRMED),
    ]
    reason = await db_session.scalar(
        select(PriceObservation.reject_reason).where(PriceObservation.price_minor == 1_000)
    )
    assert reason == "not confirmed in time (changed >= 70% vs last)"


async def test_impossible_price_is_stored_as_rejected(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    counts = await store.store_product(
        db_session, brand_id=brand_id, run_id=run_id, raw=coat(price=100), observed_at=T0
    )
    assert counts == {PriceStatus.REJECTED: 2}


async def test_finish_run_status(db_session: AsyncSession) -> None:
    _, run_id = await setup(db_session)
    status = await store.finish_run(
        db_session,
        run_id,
        finished_at=T0,
        items_seen=10,
        items_failed=1,
        stopped_by=None,
        notes="x",
    )
    assert status is RunStatus.PARTIAL
    run = await db_session.get(CollectionRun, run_id, populate_existing=True)
    assert run is not None and (run.status, run.items_seen, run.items_failed) == (
        RunStatus.PARTIAL,
        10,
        1,
    )


async def test_batch_of_new_and_known_products(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    await store.store_product(
        db_session, brand_id=brand_id, run_id=run_id, raw=coat(), observed_at=T0
    )
    jacket = RawProduct(
        external_id="2002",
        url="https://shop.example.com/ceket-2002",
        title="Ceket",
        currency="TRY",
        variants=[RawVariant(external_sku="2002-M", price_minor=50_000, in_stock=False)],
    )
    counts = await store.store_products(
        db_session,
        brand_id=brand_id,
        run_id=run_id,
        batch=[(coat(price=1_000), T0 + DAY), (jacket, T0 + DAY)],
    )
    assert counts == {PriceStatus.PENDING: 2, PriceStatus.CONFIRMED: 1}
    titles = await db_session.scalars(select(Product.title_raw).order_by(Product.external_id))
    assert list(titles) == ["Siyah Kaban", "Ceket"]


async def stretches(session: AsyncSession) -> list[tuple[int, bool, datetime, datetime]]:
    rows = await session.execute(
        select(
            PriceObservation.price_minor,
            PriceObservation.in_stock,
            PriceObservation.observed_at,
            PriceObservation.last_seen_at,
        )
        .join(Variant)
        .where(Variant.external_sku == "1001-S")
        .order_by(PriceObservation.observed_at)
    )
    return [tuple(row) for row in rows]  # type: ignore[misc]


async def test_unchanged_price_only_moves_last_seen(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    for day in range(3):
        counts = await store.store_product(
            db_session, brand_id=brand_id, run_id=run_id, raw=coat(), observed_at=T0 + day * DAY
        )
        assert counts == {PriceStatus.CONFIRMED: 2}
    assert await stretches(db_session) == [(100_000, True, T0, T0 + 2 * DAY)]


async def test_any_change_starts_a_new_stretch(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    sold_out = coat().model_copy(
        update={"variants": [v.model_copy(update={"in_stock": False}) for v in coat().variants]}
    )
    for when, raw in [(T0, coat()), (T0 + DAY, sold_out), (T0 + 2 * DAY, coat(90_000))]:
        await store.store_product(
            db_session, brand_id=brand_id, run_id=run_id, raw=raw, observed_at=when
        )
    assert await stretches(db_session) == [
        (100_000, True, T0, T0),
        (100_000, False, T0 + DAY, T0 + DAY),
        (90_000, True, T0 + 2 * DAY, T0 + 2 * DAY),
    ]


async def test_pending_seen_again_too_soon_stays_pending(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    soon = T0 + DAY + timedelta(minutes=10)
    for when, price in [(T0, 100_000), (T0 + DAY, 1_000), (soon, 1_000)]:
        await store.store_product(
            db_session, brand_id=brand_id, run_id=run_id, raw=coat(price), observed_at=when
        )
    assert await statuses(db_session) == [
        (100_000, PriceStatus.CONFIRMED),
        (1_000, PriceStatus.PENDING),
    ]


async def test_rejected_state_is_judged_again_not_extended(db_session: AsyncSession) -> None:
    brand_id, run_id = await setup(db_session)
    for when in [T0, T0 + DAY]:
        await store.store_product(
            db_session, brand_id=brand_id, run_id=run_id, raw=coat(price=100), observed_at=when
        )
    assert await statuses(db_session) == [
        (100, PriceStatus.REJECTED),
        (100, PriceStatus.REJECTED),
    ]
