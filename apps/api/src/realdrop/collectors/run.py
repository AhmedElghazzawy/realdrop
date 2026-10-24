"""Run one brand's collector by hand.

    uv run python -m realdrop.collectors.run --brand defacto --limit 20 --dry-run

--dry-run prints what was collected and stores nothing. Storing (glitch filter + pipeline/store.py)
is the next roadmap step; until it exists, a run without --dry-run refuses to start.
"""

import argparse
import asyncio
import sys
import time

from realdrop.collectors.base import ItemFailure, RawProduct
from realdrop.collectors.http import CollectorError
from realdrop.collectors.registry import get_collector_class


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


async def dry_run(slug: str, limit: int) -> int:
    collector_class = get_collector_class(slug)
    products = failures = 0
    started = time.monotonic()
    async with collector_class.make_client() as client:
        catalog = collector_class(client).fetch_catalog()
        try:
            async for item in catalog:
                if isinstance(item, ItemFailure):
                    failures += 1
                    print(f"FAILED  {item.source}: {item.reason}")
                else:
                    products += 1
                    print(describe(item))
                if products + failures >= limit:
                    break
        except CollectorError as exc:
            print(f"RUN STOPPED: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        finally:
            await catalog.aclose()  # type: ignore[attr-defined]
    elapsed = time.monotonic() - started
    print(f"\n{products} products, {failures} failures in {elapsed:.0f}s (nothing stored)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else None)
    parser.add_argument("--brand", required=True, help="collector slug, e.g. defacto")
    parser.add_argument("--limit", type=int, default=20, help="stop after this many items")
    parser.add_argument("--dry-run", action="store_true", help="print only, store nothing")
    args = parser.parse_args()
    if not args.dry_run:
        parser.error("storing is not built yet (pipeline/store.py); use --dry-run")
    return asyncio.run(dry_run(args.brand, args.limit))


if __name__ == "__main__":
    sys.exit(main())
