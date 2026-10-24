"""Pure parsing for the example brand: raw JSON in, RawProduct out. No IO, so it is trivially
testable against stored fixtures."""

from typing import Any

from realdrop.collectors.base import RawProduct, RawVariant
from realdrop.collectors.money import parse_tr_price


def parse_listing(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
    """Split one listing page into its raw product items and the next page number (or None)."""
    return list(payload["products"]), payload.get("next_page")


def parse_product(item: dict[str, Any]) -> RawProduct:
    """Raises KeyError, TypeError or ValueError (incl. pydantic ValidationError) on bad input."""
    return RawProduct(
        external_id=str(item["id"]),
        url=item["url"],
        title=item["name"],
        description=item.get("description"),
        category_raw=item.get("category"),
        image_urls=item.get("images") or [],
        currency="TRY",
        variants=[_parse_variant(v) for v in item["variants"]],
    )


def _parse_variant(raw: dict[str, Any]) -> RawVariant:
    old_price = raw.get("old_price")
    return RawVariant(
        external_sku=str(raw["sku"]),
        size_label=raw.get("size"),
        color_raw=raw.get("color"),
        price_minor=parse_tr_price(raw["price"]),
        original_price_minor=parse_tr_price(old_price) if old_price else None,
        in_stock=int(raw["stock"]) > 0,
    )
