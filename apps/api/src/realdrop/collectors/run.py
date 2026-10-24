"""Run one brand's collector.

    uv run python -m realdrop.collectors.run --brand defacto --limit 20 --dry-run
    uv run python -m realdrop.collectors.run --brand defacto            # full run, stored
    uv run python -m realdrop.collectors.run --brand defacto --shard 0/2  # first half only

--dry-run prints what was collected and stores nothing. A stored run records a `collection_runs`
row, writes products in batches of 20 per transaction (a crash loses one batch at most), runs every
price through the glitch filter, and finally expires pending prices nobody confirmed in time.
"""

import argparse
import asyncio
import sys
import time
from collections import Counter
from datetime import UTC, datetime

from realdrop.collectors.base import BrandCollector, ItemFailure, RawProduct, Shard
from realdrop.collectors.http import CollectorError
from realdrop.collectors.registry import get_collector_class
from realdrop.db.session import get_sessionmaker
from realdrop.models import PriceStatus
from realdrop.pipeline import store

MAX_FAILURES_IN_NOTES = 20
BATCH_SIZE = 20  # products per transaction; see store.store_products


def format_try(minor: int) -> str:
    """129999 -> '1.299,99 TL' (display only)."""
    lira, kurus = divmod(minor, 100)
    return f"{lira:,}".replace(",", ".") + f",{kurus:02d} TL"


def describe(product: RawProduct) -> str:
    first = product.variants[0]
    price = format_try(first.price_minor)
    if first.original_price_minor is not None:
        price += f" (claimed {format_try(first.original_price_minor)})"
    in_stock = sum(v.in_stock for v in product.variants)
    sizes = ", ".join(v.size_label or "?" for v in product.variants if v.in_stock)
    return (
        f"{product.external_id}  {product.title}\n"
        f"    {price} | {in_stock}/{len(product.variants)} sizes in stock: {sizes or '-'}\n"
        f"    {product.category_raw or '-'} | {product.url}"
    )


async def dry_run(slug: str, limit: int | None, shard: Shard) -> int:
    collector_class = get_collector_class(slug)
    products = failures = 0
    started = time.monotonic()
    async with collector_class.make_client() as client:
        catalog = collector_class(client, shard=shard).fetch_catalog()
        try:
            async for item in catalog:
                if isinstance(item, ItemFailure):
                    failures += 1
                    print(f"FAILED  {item.source}: {item.reason}")
                else:
                    products += 1
                    print(describe(item))
                if limit is not None and products + failures >= limit:
                    break
        except CollectorError as exc:
            print(f"RUN STOPPED: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        finally:
            await catalog.aclose()  # type: ignore[attr-defined]
    elapsed = time.monotonic() - started
    print(f"\n{products} products, {failures} failures in {elapsed:.0f}s (nothing stored)")
    return 0


async def stored_run(slug: str, limit: int | None, shard: Shard) -> int:
    collector_class: type[BrandCollector] = get_collector_class(slug)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session, session.begin():
        brand = await store.get_or_create_brand(
            session,
            slug=collector_class.slug,
            name=collector_class.name,
            base_url=collector_class.base_url,
        )
        run = await store.start_run(session, brand.id)
        brand_id, run_id = brand.id, run.id

    products = failures = 0
    statuses: Counter[PriceStatus] = Counter()
    failure_notes: list[str] = []
    stopped_by: str | None = None
    started = time.monotonic()
    pending: list[tuple[RawProduct, datetime]] = []

    async def flush() -> Counter[PriceStatus]:
        """Store the buffered products in one transaction (a crash loses at most one batch)."""
        if not pending:
            return Counter()
        async with sessionmaker() as session, session.begin():
            counts = await store.store_products(
                session, brand_id=brand_id, run_id=run_id, batch=pending
            )
        pending.clear()
        return counts

    try:
        async with collector_class.make_client() as client:
            catalog = collector_class(client, shard=shard).fetch_catalog()
            try:
                async for item in catalog:
                    if isinstance(item, ItemFailure):
                        failures += 1
                        if len(failure_notes) < MAX_FAILURES_IN_NOTES:
                            failure_notes.append(f"{item.source}: {item.reason}")
                    else:
                        pending.append((item, datetime.now(UTC)))
                        products += 1
                        if len(pending) >= BATCH_SIZE:
                            statuses += await flush()
                    if limit is not None and products + failures >= limit:
                        break
            finally:
                await catalog.aclose()  # type: ignore[attr-defined]
        statuses += await flush()
    except CollectorError as exc:
        stopped_by = f"{type(exc).__name__}: {exc}"
        statuses += await flush()  # keep what was collected before the stop
    except BaseException as exc:  # a bug or Ctrl-C: still close the run row, then re-raise
        stopped_by = f"crashed: {type(exc).__name__}: {exc}"
        raise
    finally:
        async with sessionmaker() as session, session.begin():
            expired = await store.expire_pending(session, datetime.now(UTC))
            summary = (
                f"shard {shard.index}/{shard.count}; "
                f"prices: {dict((s.value, n) for s, n in statuses.items())}; "
                f"expired pending: {expired}"
            )
            notes = "\n".join(filter(None, [stopped_by, summary, *failure_notes]))
            status = await store.finish_run(
                session,
                run_id,
                finished_at=datetime.now(UTC),
                items_seen=products + failures,
                items_failed=failures,
                stopped_by=stopped_by,
                notes=notes,
            )
        elapsed = time.monotonic() - started
        print(
            f"run {run_id}: {status.value}, {products} products, {failures} failures, "
            f"{elapsed:.0f}s\n{notes}"
        )
    return 1 if stopped_by else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else None)
    parser.add_argument("--brand", required=True, help="collector slug, e.g. defacto")
    parser.add_argument("--limit", type=int, default=None, help="stop after this many items")
    parser.add_argument("--dry-run", action="store_true", help="print only, store nothing")
    parser.add_argument(
        "--shard", type=Shard.parse, default=Shard(), help="part of the catalog, e.g. 0/2"
    )
    args = parser.parse_args()
    if args.dry_run:
        return asyncio.run(dry_run(args.brand, args.limit, args.shard))
    return asyncio.run(stored_run(args.brand, args.limit, args.shard))


if __name__ == "__main__":
    sys.exit(main())
