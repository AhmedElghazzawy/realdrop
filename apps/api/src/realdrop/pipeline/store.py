"""Write collector output to the database: catalog upserts plus one validated price observation per
variant per run. The caller owns the transaction (one per product, so a crash loses at most one).

Observations are append-only. The only updates are glitch-filter status changes on pending rows:
confirmed by a later identical price, or rejected when they expire (pipeline/validate.py).
"""

import hashlib
import json
import uuid
from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.collectors.base import RawProduct
from realdrop.models import (
    Brand,
    CollectionRun,
    PriceObservation,
    PriceStatus,
    Product,
    RunStatus,
    Variant,
)
from realdrop.pipeline.validate import Held, classify, confirming
from realdrop.pricing import config


async def get_or_create_brand(
    session: AsyncSession, *, slug: str, name: str, base_url: str
) -> Brand:
    brand = await session.scalar(select(Brand).where(Brand.slug == slug))
    if brand is None:
        brand = Brand(slug=slug, name=name, base_url=base_url)
        session.add(brand)
        await session.flush()
    return brand


async def start_run(session: AsyncSession, brand_id: uuid.UUID) -> CollectionRun:
    run = CollectionRun(brand_id=brand_id, status=RunStatus.RUNNING)
    session.add(run)
    await session.flush()
    return run


async def finish_run(
    session: AsyncSession,
    run_id: uuid.UUID,
    *,
    finished_at: datetime,
    items_seen: int,
    items_failed: int,
    stopped_by: str | None,
    notes: str,
) -> RunStatus:
    """`failed` if the run stopped early, `partial` if some items failed, else `succeeded`."""
    if stopped_by is not None:
        status = RunStatus.FAILED
    elif items_failed:
        status = RunStatus.PARTIAL
    else:
        status = RunStatus.SUCCEEDED
    await session.execute(
        update(CollectionRun)
        .where(CollectionRun.id == run_id)
        .values(
            finished_at=finished_at,
            status=status,
            items_seen=items_seen,
            items_failed=items_failed,
            notes=notes,
        )
    )
    return status


def content_hash(raw: RawProduct) -> str:
    """Changes when the text or images change, so the extractor knows what to re-run."""
    payload = [raw.title, raw.description, raw.category_raw, [str(u) for u in raw.image_urls]]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


async def store_product(
    session: AsyncSession,
    *,
    brand_id: uuid.UUID,
    run_id: uuid.UUID,
    raw: RawProduct,
    observed_at: datetime,
) -> Counter[PriceStatus]:
    """Upsert the product and its variants, then add one observation per variant.
    Returns how many observations got each status."""
    product = await _upsert_product(session, brand_id, raw, observed_at)
    variants = await _upsert_variants(session, product, raw)
    ids = [v.id for v in variants.values()]

    last_confirmed = await _last_confirmed(session, ids)
    recent = await _confirmed_since(session, ids, observed_at - config.MEDIAN_WINDOW)
    held = await _held_since(session, ids, observed_at - config.PENDING_EXPIRY)

    counts: Counter[PriceStatus] = Counter()
    for raw_variant in raw.variants:
        variant = variants[raw_variant.external_sku]
        verdict = classify(
            raw_variant.price_minor,
            raw_variant.original_price_minor,
            last_confirmed.get(variant.id),
            recent[variant.id],
        )
        status, reason = verdict.status, verdict.reason
        if status is PriceStatus.PENDING:
            confirmed = confirming(raw_variant.price_minor, observed_at, held[variant.id])
            if confirmed:
                await session.execute(
                    update(PriceObservation)
                    .where(PriceObservation.id.in_([h.observation_id for h in confirmed]))
                    .values(status=PriceStatus.CONFIRMED, reject_reason=None)
                )
                status, reason = PriceStatus.CONFIRMED, None
        session.add(
            PriceObservation(
                variant_id=variant.id,
                run_id=run_id,
                observed_at=observed_at,
                price_minor=raw_variant.price_minor,
                original_price_minor=raw_variant.original_price_minor,
                currency=raw.currency,
                in_stock=raw_variant.in_stock,
                status=status,
                # Pending rows keep their reason too, so a held price can be explained.
                reject_reason=reason,
            )
        )
        counts[status] += 1
    await session.flush()
    return counts


async def expire_pending(session: AsyncSession, now: datetime) -> int:
    """Reject pending observations that no later run confirmed in time. Returns how many."""
    result = await session.execute(
        update(PriceObservation)
        .where(
            PriceObservation.status == PriceStatus.PENDING,
            PriceObservation.observed_at < now - config.PENDING_EXPIRY,
        )
        .values(
            status=PriceStatus.REJECTED,
            # Keeps why it was held: "not confirmed in time (changed >= 70% vs last)".
            reject_reason=func.concat(
                "not confirmed in time (", PriceObservation.reject_reason, ")"
            ),
        )
    )
    return int(result.rowcount)  # type: ignore[attr-defined]


async def _upsert_product(
    session: AsyncSession, brand_id: uuid.UUID, raw: RawProduct, observed_at: datetime
) -> Product:
    product = await session.scalar(
        select(Product).where(Product.brand_id == brand_id, Product.external_id == raw.external_id)
    )
    if product is None:
        product = Product(brand_id=brand_id, external_id=raw.external_id, first_seen_at=observed_at)
        session.add(product)
    product.url = str(raw.url)
    product.title_raw = raw.title
    product.description_raw = raw.description
    product.category_raw = raw.category_raw
    product.image_urls = [str(u) for u in raw.image_urls]
    product.content_hash = content_hash(raw)
    product.last_seen_at = observed_at
    product.is_active = True
    await session.flush()
    return product


async def _upsert_variants(
    session: AsyncSession, product: Product, raw: RawProduct
) -> dict[str, Variant]:
    existing = {
        v.external_sku: v
        for v in await session.scalars(select(Variant).where(Variant.product_id == product.id))
    }
    for raw_variant in raw.variants:
        variant = existing.get(raw_variant.external_sku)
        if variant is None:
            variant = Variant(product_id=product.id, external_sku=raw_variant.external_sku)
            session.add(variant)
            existing[raw_variant.external_sku] = variant
        variant.size_label = raw_variant.size_label
        variant.color_raw = raw_variant.color_raw
    await session.flush()
    return existing


async def _last_confirmed(session: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    rows = await session.execute(
        select(PriceObservation.variant_id, PriceObservation.price_minor)
        .where(
            PriceObservation.variant_id.in_(ids),
            PriceObservation.status == PriceStatus.CONFIRMED,
        )
        .order_by(PriceObservation.variant_id, PriceObservation.observed_at.desc())
        .ext(distinct_on(PriceObservation.variant_id))
    )
    return {variant_id: price for variant_id, price in rows}


async def _confirmed_since(
    session: AsyncSession, ids: list[uuid.UUID], since: datetime
) -> defaultdict[uuid.UUID, list[int]]:
    rows = await session.execute(
        select(PriceObservation.variant_id, PriceObservation.price_minor).where(
            PriceObservation.variant_id.in_(ids),
            PriceObservation.status == PriceStatus.CONFIRMED,
            PriceObservation.observed_at >= since,
        )
    )
    prices: defaultdict[uuid.UUID, list[int]] = defaultdict(list)
    for variant_id, price in rows:
        prices[variant_id].append(price)
    return prices


async def _held_since(
    session: AsyncSession, ids: list[uuid.UUID], since: datetime
) -> defaultdict[uuid.UUID, list[Held]]:
    rows = await session.execute(
        select(
            PriceObservation.variant_id,
            PriceObservation.id,
            PriceObservation.observed_at,
            PriceObservation.price_minor,
        ).where(
            PriceObservation.variant_id.in_(ids),
            PriceObservation.status == PriceStatus.PENDING,
            PriceObservation.observed_at > since,
        )
    )
    held: defaultdict[uuid.UUID, list[Held]] = defaultdict(list)
    for variant_id, observation_id, held_at, price in rows:
        held[variant_id].append(Held(observation_id, held_at, price))
    return held
