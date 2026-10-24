import asyncio
from typing import Any

import pytest
from pydantic import ValidationError

from realdrop.collectors.base import RawProduct, RawVariant, Shard, in_flight
from realdrop.collectors.registry import get_collector_class


def _variant(**overrides: Any) -> dict[str, Any]:
    return {"external_sku": "1-M", "price_minor": 129990, "in_stock": True} | overrides


def _product(**overrides: Any) -> dict[str, Any]:
    return {
        "external_id": "1",
        "url": "https://shop.example.com/p/1",
        "title": "Kaban",
        "currency": "TRY",
        "variants": [_variant()],
    } | overrides


def test_text_is_nfc_normalized_and_whitespace_collapsed() -> None:
    decomposed = "İSTANBUL  Kaban\n"  # "İ" written as I + combining dot
    product = RawProduct.model_validate(_product(title=decomposed))
    assert product.title == "İSTANBUL Kaban"


def test_float_price_is_rejected_not_truncated() -> None:
    with pytest.raises(ValidationError):
        RawVariant.model_validate(_variant(price_minor=1299.9))


def test_numeric_string_price_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawVariant.model_validate(_variant(price_minor="129990"))


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": "   "},
        {"currency": "TL"},
        {"variants": []},
        {"variants": [_variant(), _variant()]},  # duplicate SKU
        {"url": "not a url"},
        {"unexpected_field": 1},
    ],
)
def test_invalid_products_are_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        RawProduct.model_validate(_product(**overrides))


def test_registry_explains_unknown_brand() -> None:
    with pytest.raises(KeyError, match="unknown brand 'nope'"):
        get_collector_class("nope")


def test_shards_split_a_catalog_without_overlap() -> None:
    urls = [f"https://shop.example.com/p-{n}" for n in range(1000)]
    halves = [Shard(0, 2), Shard.parse("1/2")]
    sizes = [sum(s.contains(u) for u in urls) for s in halves]
    assert sum(sizes) == 1000  # every product in exactly one shard
    assert all(400 < n < 600 for n in sizes)  # roughly even
    assert all(Shard().contains(u) for u in urls)
    with pytest.raises(ValueError, match="invalid shard"):
        Shard.parse("2/2")


async def test_in_flight_respects_the_limit_and_yields_everything() -> None:
    running = peak = 0

    async def fetch(n: int) -> int:
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.001 * (n % 3))
        running -= 1
        return n * 10

    results = [r async for r in in_flight(range(10), fetch, limit=3)]
    assert sorted(results) == [n * 10 for n in range(10)]
    assert peak == 3


async def test_in_flight_error_cancels_the_rest() -> None:
    cancelled = 0

    async def fetch(n: int) -> int:
        nonlocal cancelled
        if n == 0:
            raise RuntimeError("blocked")
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled += 1
            raise
        return n

    with pytest.raises(RuntimeError, match="blocked"):
        _ = [r async for r in in_flight(range(5), fetch, limit=3)]
    assert cancelled == 2
