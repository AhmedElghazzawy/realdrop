"""Pure parsing for Colin's: product-page HTML in, RawProduct out. No IO.

What a product page carries (see docs/brands/colins.md):
- schema.org `Product` JSON-LD: name, price paid (`offers.price`), currency, images.
- `.product-detail-old-price` ("1399,90 TL"), only when the site shows a strike-through price.
- One size `<select>` whose `<option value="<variant id>" class="have-stock|no-stock">` lists every
  size; sold-out ones get " - STOĞA GELİNCE HABER VER" appended to the label.
- `data-variant-name` (colour) and a JS `Breadcrumb: "Leaf<Parent<Tüm Ürünler"` string.

Product URLs come from /SitemapProducts, a plain sitemap (collectors/sitemap.py).
"""

import html as html_lib
import json
import re
from decimal import Decimal
from typing import Any

from realdrop.collectors.base import Audience, RawProduct, RawVariant
from realdrop.collectors.money import decimal_to_minor, parse_tr_price

BASE_URL = "https://www.colins.com.tr"
SITEMAP = f"{BASE_URL}/SitemapProducts"

_PRODUCT_ID = re.compile(r"/p/[^/?#]*-(\d+)/?$")
_JSON_LD = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S)
_OLD_PRICE = re.compile(r'<div class="product-detail-old-price[ "][^>]*>\s*([^<]+?)\s*</div>')
_SIZE_SELECT = re.compile(r"<select[^>]*size-select-list[^>]*>(.*?)</select>", re.S)
_SIZE_OPTION = re.compile(
    r'<option\s+value="(\d+)"\s+class="(have-stock|no-stock)"[^>]*>\s*(.*?)\s*</option>', re.S
)
_SOLD_OUT_SUFFIX = re.compile(r"\s*-\s*STOĞA GELİNCE HABER VER\s*$")
_COLOR = re.compile(r'data-variant-name="([^"]*)"')
_BREADCRUMB = re.compile(r'Breadcrumb:\s*"((?:[^"\\]|\\.)*)"')
_ALL_PRODUCTS = "Tüm "  # "Tüm Ürünler", "Tüm Kadın Ürünleri": catalog-wide levels, not categories
_AUDIENCE_ROOTS: dict[str, Audience] = {"Erkek Giyim": "men", "Kadın Giyim": "women"}
_AUDIENCE_WORDS: dict[str, Audience] = {"Erkek": "men", "Kadın": "women"}
_DECODER = json.JSONDecoder(parse_float=Decimal)


def product_id(url: str) -> str:
    match = _PRODUCT_ID.search(url)
    if match is None:
        raise ValueError(f"no product id in {url}")
    return match.group(1)


def has_product_data(html: str) -> bool:
    """False for anything that is not a product page (error page, challenge, maintenance)."""
    return _product_ld(html) is not None and _SIZE_SELECT.search(html) is not None


def parse_product(html: str, url: str) -> RawProduct:
    """Raises KeyError, TypeError or ValueError (incl. pydantic ValidationError) on bad input."""
    ld = _product_ld(html)
    if ld is None:
        raise ValueError("no Product JSON-LD")
    offers = ld["offers"]
    price = decimal_to_minor(offers["price"])
    old = _OLD_PRICE.search(html)
    claimed = parse_tr_price(html_lib.unescape(old.group(1))) if old else None
    original = claimed if claimed is not None and claimed > price else None

    select = _SIZE_SELECT.search(html)
    if select is None:
        raise ValueError("no size list")
    color = _COLOR.search(html)
    variants = [
        RawVariant(
            external_sku=variant_id,
            size_label=_SOLD_OUT_SUFFIX.sub("", html_lib.unescape(label)),
            color_raw=html_lib.unescape(color.group(1)) if color else None,
            price_minor=price,
            original_price_minor=original,
            in_stock=stock == "have-stock",
        )
        for variant_id, stock, label in _SIZE_OPTION.findall(select.group(1))
    ]
    title = html_lib.unescape(ld["name"])
    category = _category_path(html)
    images = ld.get("image") or []
    return RawProduct(
        external_id=product_id(url),
        url=url,
        title=title,
        description=html_lib.unescape(ld["description"]) if ld.get("description") else None,
        category_raw=category,
        audience=_audience(category, title),
        image_urls=[images] if isinstance(images, str) else list(images),
        currency=offers["priceCurrency"],
        variants=variants,
    )


def _product_ld(html: str) -> dict[str, Any] | None:
    for block in _JSON_LD.findall(html):
        try:
            item, _ = _DECODER.raw_decode(block.strip())
        except ValueError:
            continue
        if isinstance(item, dict) and item.get("@type") == "Product":
            return item
    return None


def _category_path(html: str) -> str | None:
    """'Erkek Pantolon<Erkek Giyim<Tüm Ürünler' -> 'Erkek Giyim > Erkek Pantolon'."""
    match = _BREADCRUMB.search(html)
    if match is None:
        return None
    # A JS string literal: \\u003c escapes first, then HTML entities (&#252;).
    raw = html_lib.unescape(json.loads(f'"{match.group(1)}"'))
    levels = [level.strip() for level in reversed(raw.split("<"))]
    return " > ".join(lv for lv in levels if lv and not lv.startswith(_ALL_PRODUCTS)) or None


def _audience(category: str | None, title: str) -> Audience | None:
    """From the category root when it is a men's/women's one, else from the title's words.
    Campaign-only categories ("Öğretmenler Günü Hediyesi") say nothing; the title always does."""
    root = category.split(" > ")[0] if category else None
    if root in _AUDIENCE_ROOTS:
        return _AUDIENCE_ROOTS[root]
    found = {_AUDIENCE_WORDS[w] for w in re.findall(r"\w+", title) if w in _AUDIENCE_WORDS}
    return found.pop() if len(found) == 1 else None
