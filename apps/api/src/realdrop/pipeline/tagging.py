"""Keep `product_attributes` in step with the catalog, using the pure rules in pipeline/tagger.py.

A product is (re)tagged when it has no row yet, its `content_hash` changed since it was tagged, or
the rules changed (TAGGER_VERSION). Rows written by the LLM pass are only replaced when the product
itself changed: a new rules version never overwrites a model's answer for unchanged text.

collectors/run.py calls `refresh_attributes` for its own brand after each run (brands run in
parallel; their products never overlap). Run it for the whole catalog by hand with:

    uv run python -m realdrop.pipeline.tagging            # only what is missing or stale
    uv run python -m realdrop.pipeline.tagging --all      # re-tag every product with the rules
"""

import argparse
import asyncio
import time
import uuid
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.db.session import get_sessionmaker
from realdrop.models import Product, ProductAttributes, Variant
from realdrop.pipeline.tagger import TAGGER_VERSION, tag

BATCH_SIZE = 2_000


async def refresh_attributes(
    session: AsyncSession,
    brand_id: uuid.UUID | None = None,
    *,
    retag_all: bool = False,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Tag missing or stale products (one brand, or all when `brand_id` is None).

    Returns how many rows were written. The caller owns the transaction.
    """
    written = 0
    after: uuid.UUID | None = None
    while True:
        rows = (await session.execute(_stale(brand_id, after, retag_all, batch_size))).all()
        if not rows:
            return written
        values = []
        for product_id, title, category_raw, category, content_hash, colors in rows:
            attrs = tag(title, category_raw, category, [c for c in colors if c])
            values.append(
                {
                    "product_id": product_id,
                    "style_tags": list(attrs.style_tags),
                    "colors": list(attrs.colors),
                    "pattern": attrs.pattern,
                    "fit": attrs.fit,
                    "material": list(attrs.material),
                    "formality": attrs.formality,
                    "season": list(attrs.season),
                    "occasion": [],
                    "subcategory": attrs.subcategory,
                    "source": "rules",
                    "evidence": attrs.evidence,
                    "tagger_version": TAGGER_VERSION,
                    "content_hash": content_hash,
                }
            )
        stmt = insert(ProductAttributes).values(values)
        replace: dict[str, Any] = {c: stmt.excluded[c] for c in values[0] if c != "product_id"}
        replace["tagged_at"] = func.now()
        await session.execute(
            stmt.on_conflict_do_update(index_elements=["product_id"], set_=replace)
        )
        written += len(values)
        after = rows[-1][0]


def _stale(
    brand_id: uuid.UUID | None, after: uuid.UUID | None, retag_all: bool, limit: int
) -> Select[Any]:
    colors = (
        select(func.coalesce(func.array_agg(func.distinct(Variant.color_raw)), []))
        .where(Variant.product_id == Product.id)
        .scalar_subquery()
    )
    pa = ProductAttributes
    needs_tagging = or_(
        pa.product_id.is_(None),
        pa.content_hash != Product.content_hash,
        and_(pa.source == "rules", pa.tagger_version != TAGGER_VERSION),
    )
    stmt = (
        select(
            Product.id,
            Product.title_raw,
            Product.category_raw,
            Product.category,
            Product.content_hash,
            colors,
        )
        .outerjoin(pa, pa.product_id == Product.id)
        .order_by(Product.id)
        .limit(limit)
    )
    if not retag_all:
        stmt = stmt.where(needs_tagging)
    else:
        stmt = stmt.where(or_(pa.product_id.is_(None), pa.source == "rules", needs_tagging))
    if brand_id is not None:
        stmt = stmt.where(Product.brand_id == brand_id)
    if after is not None:
        stmt = stmt.where(Product.id > after)
    return stmt


async def _main(retag_all: bool) -> None:
    started = time.monotonic()
    async with get_sessionmaker()() as session, session.begin():
        written = await refresh_attributes(session, retag_all=retag_all)
    elapsed = time.monotonic() - started
    print(f"tagged {written} products in {elapsed:.0f}s (rules v{TAGGER_VERSION})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tag products with attributes and style tags.")
    parser.add_argument("--all", action="store_true", help="re-tag every rules-tagged product")
    asyncio.run(_main(parser.parse_args().all))
