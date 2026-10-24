from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.models import (
    Brand,
    CollectionRun,
    PriceDaily,
    PriceObservation,
    PriceStatus,
    Product,
    RunStatus,
    Variant,
)


async def _variant(session: AsyncSession) -> tuple[Brand, Variant]:
    brand = Brand(slug="test-brand", name="Test Brand", base_url="https://example.com")
    product = Product(
        brand=brand,
        external_id="p1",
        url="https://example.com/p1",
        title_raw="Siyah Kaban",
        content_hash="0" * 64,
    )
    variant = Variant(product=product, external_sku="p1-M", size_label="M")
    session.add_all([brand, product, variant])
    await session.flush()
    return brand, variant


async def test_catalog_and_price_round_trip(db_session: AsyncSession) -> None:
    brand, variant = await _variant(db_session)
    run = CollectionRun(brand_id=brand.id)
    db_session.add(run)
    await db_session.flush()
    db_session.add(
        PriceObservation(
            variant_id=variant.id,
            run_id=run.id,
            observed_at=datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            price_minor=249990,
            original_price_minor=329990,
            currency="TRY",
            in_stock=True,
            status=PriceStatus.CONFIRMED,
        )
    )
    await db_session.commit()

    obs = (await db_session.scalars(select(PriceObservation))).one()
    assert obs.price_minor == 249990
    assert obs.status is PriceStatus.CONFIRMED
    assert obs.id > 0  # bigint identity, not a UUID

    await db_session.refresh(brand)
    await db_session.refresh(run)
    assert brand.country == "TR" and brand.currency == "TRY"  # server defaults
    assert brand.collector_config == {}
    assert run.status is RunStatus.RUNNING
    assert run.started_at.tzinfo is not None  # timestamptz

    # Enums are stored as their lowercase values, which is what raw SQL and reports will see.
    stored = await db_session.scalar(text("SELECT status::text FROM price_observations"))
    assert stored == "confirmed"


async def test_variant_sku_unique_per_product(db_session: AsyncSession) -> None:
    _, variant = await _variant(db_session)
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(Variant(product_id=variant.product_id, external_sku="p1-M"))


async def test_price_daily_rejects_inconsistent_low_close_high(db_session: AsyncSession) -> None:
    _, variant = await _variant(db_session)
    with pytest.raises(IntegrityError, match="low_close_high_order"):
        async with db_session.begin_nested():
            db_session.add(
                PriceDaily(
                    variant_id=variant.id,
                    snapshot_date=date(2026, 10, 25),
                    close_price_minor=100000,
                    low_price_minor=120000,  # low above close: impossible
                    high_price_minor=130000,
                    currency="TRY",
                    in_stock_close=True,
                )
            )


async def test_catalog_rows_cannot_be_deleted_while_history_exists(
    db_session: AsyncSession,
) -> None:
    brand, _ = await _variant(db_session)
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(text("DELETE FROM brands WHERE id = :id"), {"id": brand.id})
