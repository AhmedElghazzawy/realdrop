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
    """Store one product; see store_products."""
    return await store_products(
        session, brand_id=brand_id, run_id=run_id, batch=[(raw, observed_at)]
    )


async def store_products(
    session: AsyncSession,
    *,
    brand_id: uuid.UUID,
    run_id: uuid.UUID,
    batch: list[tuple[RawProduct, datetime]],
) -> Counter[PriceStatus]:
    """Upsert a batch of products and their variants, then add one observation per variant.
    Returns how many observations got each status.

    Set-based on purpose: about ten database round trips per batch instead of per product. Against
    a remote database (~0.1 s per round trip) that is the difference between a 7 h and a 3 h run.
    """
    if not batch:
        return Counter()
    products = await _upsert_products(session, brand_id, batch)
    variants = await _upsert_variants(session, products, [raw for raw, _ in batch])
    ids = [v.id for v in variants.values()]

    # One history window for the whole batch: its items were observed seconds apart.
    earliest = min(observed_at for _, observed_at in batch)
    last_confirmed = await _last_confirmed(session, ids)
    recent = await _confirmed_since(session, ids, earliest - config.MEDIAN_WINDOW)
    held = await _held_since(session, ids, earliest - config.PENDING_EXPIRY)

    counts: Counter[PriceStatus] = Counter()
    now_confirmed: list[int] = []
    observations: list[PriceObservation] = []
    for raw, observed_at in batch:
        for raw_variant in raw.variants:
            variant = variants[(raw.external_id, raw_variant.external_sku)]
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
                    now_confirmed += [h.observation_id for h in confirmed]
                    status, reason = PriceStatus.CONFIRMED, None
            observations.append(
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
    if now_confirmed:
        await session.execute(
            update(PriceObservation)
            .where(PriceObservation.id.in_(now_confirmed))
            .values(status=PriceStatus.CONFIRMED, reject_reason=None)
        )
    session.add_all(observations)
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


async def _upsert_products(
    session: AsyncSession, brand_id: uuid.UUID, batch: list[tuple[RawProduct, datetime]]
) -> dict[str, Product]:
    external_ids = [raw.external_id for raw, _ in batch]
    products = {
        p.external_id: p
        for p in await session.scalars(
            select(Product).where(
                Product.brand_id == brand_id, Product.external_id.in_(external_ids)
            )
        )
    }
    for raw, observed_at in batch:
        product = products.get(raw.external_id)
        if product is None:
            product = Product(
                brand_id=brand_id, external_id=raw.external_id, first_seen_at=observed_at
            )
            session.add(product)
            products[raw.external_id] = product
        product.url = str(raw.url)
        product.title_raw = raw.title
        product.description_raw = raw.description
        product.category_raw = raw.category_raw
        product.image_urls = [str(u) for u in raw.image_urls]
        product.content_hash = content_hash(raw)
        product.last_seen_at = observed_at
        product.is_active = True
    await session.flush()
    return products


async def _upsert_variants(
    session: AsyncSession, products: dict[str, Product], raws: list[RawProduct]
) -> dict[tuple[str, str], Variant]:
    """Variants keyed by (product external_id, variant external_sku)."""
    by_product_id = {p.id: external_id for external_id, p in products.items()}
    existing = {
        (by_product_id[v.product_id], v.external_sku): v
        for v in await session.scalars(
            select(Variant).where(Variant.product_id.in_(list(by_product_id)))
        )
    }
    for raw in raws:
        product = products[raw.external_id]
        for raw_variant in raw.variants:
            key = (raw.external_id, raw_variant.external_sku)
            variant = existing.get(key)
            if variant is None:
                variant = Variant(product_id=product.id, external_sku=raw_variant.external_sku)
                session.add(variant)
                existing[key] = variant
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
