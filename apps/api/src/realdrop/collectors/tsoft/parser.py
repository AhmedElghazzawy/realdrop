"""Pure parsing for T-Soft product pages: HTML in, RawProduct out. No IO.

Checked on Lufian, TommyLife and Hatemoğlu (27 Oct 2026); the three use different themes but the
same data. A product page is one colour (other colours are other pages). Every colour and size
choice is an element with `data-subproduct-id` and, among others:

- `data-type`: the label ("Vizon", "XL", "48");
- `data-price` / `data-not-discounted`: the price and the shop's "old" price, both **without VAT**;
- `data-vat`: the VAT rate in percent;
- `data-instock`: "1" or "0".

The first button is the colour; it reuses one size's subproduct id (TommyLife and Lufian mark the
groups with `data-group-id` 1 and 2, Hatemoğlu does not). A page without sizes still has the
colour button, which then is its only variant (its label, a colour name, becomes the size label:
one button alone cannot tell which it is).

Prices are what the page shows: price without VAT * (1 + VAT), rounded to kurus. Each page also
holds its main price both ways (`product-price`, `product-price-vat-include`), so every parse
checks the formula against the shop's own figure. JSON-LD prices are not used: Hatemoğlu's
include a "Sepette EKSTRA %10" basket offer, which is conditional and ignored, like every
conditional offer.
"""

import html as html_lib
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from html.parser import HTMLParser
from typing import Any

from realdrop.collectors.base import Audience, RawProduct, RawVariant
from realdrop.collectors.money import decimal_to_minor, parse_tr_price
from realdrop.text import tr_lower

_JSON_LD = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S)
_HIDDEN = re.compile(r'<input type="hidden" id="(product-[\w-]+)" value="([^"]*)"')
_AUDIENCE_ROOTS: dict[str, Audience] = {"erkek": "men", "kadın": "women"}
_CENT = Decimal("0.01")


class _Buttons(HTMLParser):
    """Collects the data-* attributes of every element with data-subproduct-id."""

    def __init__(self) -> None:
        super().__init__()
        self.found: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k.removeprefix("data-"): v or "" for k, v in attrs if k.startswith("data-")}
        if "subproduct-id" in data:
            self.found.append(data)


def has_product_data(html: str) -> bool:
    return 'id="product-price-vat-include"' in html


def parse_product(html: str, url: str) -> RawProduct:
    """Raises KeyError, TypeError or ValueError on a page that is not a usable product page."""
    hidden = dict(_HIDDEN.findall(html))
    ld = _product_ld(html)
    buttons = _buttons(html)
    if not buttons:
        raise ValueError("no variant buttons")

    vat = Decimal(buttons[0]["vat"])
    shown = parse_tr_price(hidden["product-price-vat-include"])
    if _with_vat(hidden["product-price"], vat) != shown:
        raise ValueError(f"VAT check failed: {hidden['product-price']} + {vat}% != {shown}")

    first, rest = buttons[0], buttons[1:]
    is_color = any(b["subproduct-id"] == first["subproduct-id"] for b in rest)
    color = first["type"] if is_color else None
    sizes = rest if is_color else buttons
    variants = []
    for button in _last_per_subproduct(sizes):
        price = _with_vat(button["price"], Decimal(button["vat"]))
        old = _with_vat(button["not-discounted"], Decimal(button["vat"]))
        variants.append(
            RawVariant(
                external_sku=button["subproduct-id"],
                size_label=button["type"] or None,
                color_raw=color,
                price_minor=price,
                original_price_minor=old if old > price else None,
                in_stock=button["instock"] == "1",
            )
        )
    category = ld.get("category")
    images = ld.get("image") or []
    return RawProduct(
        external_id=hidden["product-id"],
        url=url,
        title=html_lib.unescape(hidden.get("product-name") or ld["name"]),
        category_raw=category,
        audience=_audience(category),
        image_urls=[images] if isinstance(images, str) else images,
        currency=ld["offers"]["priceCurrency"],
        variants=variants,
    )


def _buttons(html: str) -> list[dict[str, str]]:
    parser = _Buttons()
    parser.feed(html)
    return parser.found


def _last_per_subproduct(buttons: list[dict[str, str]]) -> list[dict[str, str]]:
    by_id = {b["subproduct-id"]: b for b in buttons}
    return list(by_id.values())


def _with_vat(net: str, vat: Decimal) -> int:
    gross = (Decimal(net) * (100 + vat) / 100).quantize(_CENT, rounding=ROUND_HALF_UP)
    return decimal_to_minor(gross)


def _product_ld(html: str) -> dict[str, Any]:
    for block in _JSON_LD.findall(html):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        items = data.get("@graph", [data]) if isinstance(data, dict) else data
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Product":
                return item
    raise ValueError("no JSON-LD Product")


def _audience(category: str | None) -> Audience | None:
    """The category's root: "Erkek > Üst Giyim > ..." is men. "Koleksiyon > ..." says nothing."""
    if not category:
        return None
    root = category.split(">")[0].strip()
    return _AUDIENCE_ROOTS.get(tr_lower(root))
