"""price_daily from change-only observations: days covered, close/low/high, rebuild safety."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.collectors.base import RawProduct, RawVariant
from realdrop.models import PriceDaily, Variant
from realdrop.pipeline import rollup, store

# 12:00 in Istanbul (UTC+3), so a few hours either way stay on the same Istanbul day.
T0 = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
DAY = timedelta(days=1)
HOUR = timedelta(hours=1)
D0 = date(2026, 10, 25)


def shirt(price: int, in_stock: bool = True) -> RawProduct:
    return RawProduct(
        external_id="3003",
        url="https://shop.example.com/gomlek-3003",
        title="Gömlek",
        currency="TRY",
        variants=[RawVariant(external_sku="3003-M", price_minor=price, in_stock=in_stock)],
    )


async def collect(session: AsyncSession, sightings: list[tuple[datetime, RawProduct]]) -> None:
    brand = await store.get_or_create_brand(
        session, slug="shop", name="Shop", base_url="https://shop.example.com"
    )
    run = await store.start_run(session, brand.id)
    for when, raw in sightings:
        await store.store_product(
            session, brand_id=brand.id, run_id=run.id, raw=raw, observed_at=when
        )


async def daily(session: AsyncSession) -> list[tuple[date, int, int, int, bool]]:
    rows = await session.execute(
        select(
            PriceDaily.snapshot_date,
            PriceDaily.close_price_minor,
            PriceDaily.low_price_minor,
            PriceDaily.high_price_minor,
            PriceDaily.in_stock_close,
        )
        .join(Variant, Variant.id == PriceDaily.variant_id)
        .where(Variant.external_sku == "3003-M")
        .order_by(PriceDaily.snapshot_date)
    )
    return [(d, c, lo, hi, s) for d, c, lo, hi, s in rows]


async def test_a_stretch_fills_every_day_it_covers(db_session: AsyncSession) -> None:
    await collect(db_session, [(T0, shirt(10_000)), (T0 + 2 * DAY, shirt(10_000))])
    assert await rollup.refresh_daily(db_session, T0 - DAY) == 3
    assert await daily(db_session) == [
        (D0, 10_000, 10_000, 10_000, True),
        (D0 + timedelta(days=1), 10_000, 10_000, 10_000, True),
        (D0 + timedelta(days=2), 10_000, 10_000, 10_000, True),
    ]


async def test_close_is_the_last_price_of_the_day(db_session: AsyncSession) -> None:
    await collect(
        db_session,
        [
            (T0, shirt(10_000)),
            (T0 + 2 * HOUR, shirt(8_000, in_stock=False)),
            (T0 + 4 * HOUR, shirt(9_000)),
        ],
    )
    await rollup.refresh_daily(db_session, T0)
    assert await daily(db_session) == [(D0, 9_000, 8_000, 10_000, True)]


async def test_days_without_a_sighting_have_no_row(db_session: AsyncSession) -> None:
    # Seen at 10,000 on day 0, then at 9,000 on day 3: the price change splits the stretches, and
    # nothing says what happened on days 1 and 2.
    await collect(db_session, [(T0, shirt(10_000)), (T0 + 3 * DAY, shirt(9_000))])
    await rollup.refresh_daily(db_session, T0 - DAY)
    assert [row[0] for row in await daily(db_session)] == [D0, D0 + timedelta(days=3)]


async def test_pending_prices_are_left_out(db_session: AsyncSession) -> None:
    await collect(db_session, [(T0, shirt(100_000)), (T0 + DAY, shirt(1_000))])  # 99% drop: held
    await rollup.refresh_daily(db_session, T0 - DAY)
    assert [row[:2] for row in await daily(db_session)] == [(D0, 100_000)]


async def test_rebuilding_twice_gives_the_same_rows(db_session: AsyncSession) -> None:
    await collect(db_session, [(T0, shirt(10_000)), (T0 + DAY, shirt(9_500))])
    await rollup.refresh_daily(db_session, T0 - DAY)
    first = await daily(db_session)
    await rollup.refresh_daily(db_session, T0 - DAY)
    assert await daily(db_session) == first


async def test_only_days_from_since_are_rebuilt(db_session: AsyncSession) -> None:
    await collect(db_session, [(T0, shirt(10_000)), (T0 + 2 * DAY, shirt(10_000))])
    await rollup.refresh_daily(db_session, T0 + 2 * DAY)
    assert [row[0] for row in await daily(db_session)] == [D0 + timedelta(days=2)]
