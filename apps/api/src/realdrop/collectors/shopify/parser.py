"""Pure parsing for Shopify's public catalog JSON: one `/products.json` product in, RawProducts out.

Every Shopify shop answers `/products.json?limit=250&page=N` with
`{"products": [{id, title, handle, product_type, tags, options, variants, images}]}`
(checked on Les Benjamins and Ramsey, 26 Oct 2026). Each variant is one option combination
("Black / M", "Antrasit / 6 DROP / 46") with its own `price`, `compare_at_price` (the shop's "old"
price; "0.00" or null when there is none) and `available`.

Our product is one colour, like on the other brands, so a Shopify product with several colours
becomes several RawProducts. The JSON carries no currency: the collector checks it per run.
"""

from typing import Any

from realdrop.collectors.base import Audience, RawProduct, RawVariant
from realdrop.collectors.money import decimal_to_minor
from realdrop.text import tr_lower

_COLOR_OPTIONS = {"color", "colour", "renk"}
_NO_OPTION = "Default Title"  # Shopify's value for a product without options
_GENDER_TAGS: dict[str, Audience] = {
    "men": "men",
    "erkek": "men",
    "women": "women",
    "kadın": "women",
}


def parse_product(product: dict[str, Any], base_url: str, currency: str) -> list[RawProduct]:
    """One RawProduct per colour. Raises KeyError, TypeError or ValueError on bad input."""
    options = [o["name"] for o in sorted(product["options"], key=lambda o: o["position"])]
    color_index = next(
        (i for i, name in enumerate(options) if tr_lower(name) in _COLOR_OPTIONS), None
    )
    by_color: dict[str | None, list[dict[str, Any]]] = {}
    for variant in product["variants"]:
        values = [variant.get(f"option{i + 1}") for i in range(len(options))]
        color = values[color_index] if color_index is not None else None
        by_color.setdefault(color, []).append(variant)

    images = product.get("images") or []
    results = []
    for color, variants in by_color.items():
        ids = {v["id"] for v in variants}
        linked = [i["src"] for i in images if ids & set(i.get("variant_ids") or [])]
        results.append(
            RawProduct(
                external_id=f"{product['id']}-{color}" if color else str(product["id"]),
                # ?variant= opens the page on this colour.
                url=f"{base_url}/products/{product['handle']}?variant={variants[0]['id']}",
                title=product["title"],
                category_raw=product.get("product_type") or None,
                audience=_audience(product.get("tags") or []),
                image_urls=linked or [i["src"] for i in images],
                currency=currency,
                variants=[_variant(v, len(options), color_index, color) for v in variants],
            )
        )
    return results


def _variant(
    variant: dict[str, Any], option_count: int, color_index: int | None, color: str | None
) -> RawVariant:
    values = [variant.get(f"option{i + 1}") for i in range(option_count)]
    # Everything but the colour is the size: "M", or Ramsey's fit and size "6 DROP/46".
    size = [str(v) for i, v in enumerate(values) if i != color_index and v and v != _NO_OPTION]
    price = decimal_to_minor(variant["price"])
    compare = variant.get("compare_at_price")
    original = decimal_to_minor(compare) if compare else None
    return RawVariant(
        external_sku=str(variant["id"]),
        size_label="/".join(size) or None,
        color_raw=color,
        price_minor=price,
        original_price_minor=original if original is not None and original > price else None,
        in_stock=bool(variant["available"]),
    )


def _audience(tags: list[str]) -> Audience | None:
    """Exact tags only ("men", not "x-men" or "unisex"); a product tagged both is neither."""
    found = {_GENDER_TAGS[t] for t in (tr_lower(t.strip()) for t in tags) if t in _GENDER_TAGS}
    return found.pop() if len(found) == 1 else None
