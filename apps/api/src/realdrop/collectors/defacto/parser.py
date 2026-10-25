"""Pure parsing for DeFacto: sitemap XML and product-page HTML in, RawProduct out. No IO.

A product page carries three blobs we use (see docs/brands/defacto.md):
- `DataLayer:{...}`: name, colour, category path, list price, and one entry per size with a stable
  `MatrixId` and `StockQuantity`.
- `CampaignBadge:{...}` or `null`: a basket campaign ("Sepette Net %50 İndirim") with its price and
  start/end dates. It needs no coupon or second item, so its price is what everyone pays.
- schema.org `Product` JSON-LD: image URLs.

Price meaning: `price_minor` is what a shopper pays today (campaign price if one is active, else the
shelf price); `original_price_minor` is the higher price the site shows next to it, if any. Numbers
are decoded as Decimal and converted with money.decimal_to_minor, never through float.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from realdrop.collectors.base import Audience, RawProduct, RawVariant
from realdrop.collectors.money import decimal_to_minor
from realdrop.collectors.sitemap import sitemap_locs

BASE_URL = "https://www.defacto.com.tr"
# Turkey has used UTC+3 all year since 2016; campaign dates on the site are local, without offset.
TURKEY = timezone(timedelta(hours=3))

_PRODUCT_SITEMAP = re.compile(r"/sharedxml/tr-tr/product(-\d+)?\.xml$")
_PRODUCT_ID = re.compile(r"-(\d{6,})/?$")
_WAIST_LENGTH = re.compile(r"^Beden (.+?) - Boy (.+)$")
_JSON_LD = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S)
_DECODER = json.JSONDecoder(parse_float=Decimal)
_AUDIENCE_ROOTS: dict[str, Audience] = {"Erkek": "men", "Kadın": "women"}


def product_sitemaps(index_xml: str) -> list[str]:
    return [url for url in sitemap_locs(index_xml) if _PRODUCT_SITEMAP.search(url)]


def product_id(url: str) -> str:
    match = _PRODUCT_ID.search(url)
    if match is None:
        raise ValueError(f"no product id in {url}")
    return match.group(1)


def has_product_data(html: str) -> bool:
    """False for anything that is not a product page (error page, challenge, maintenance)."""
    return "DataLayer:" in html and "CampaignBadge:" in html


def parse_product(html: str, url: str, now: datetime) -> RawProduct:
    """Raises KeyError, TypeError or ValueError (incl. pydantic ValidationError) on bad input."""
    data = _js_value(html, "DataLayer:")
    campaign = _js_value(html, "CampaignBadge:")

    list_price = decimal_to_minor(data["Price"])
    shelf_price = decimal_to_minor(data["DiscountedPrice"])
    pay = shelf_price
    if _campaign_is_active(campaign, data, now):
        pay = min(pay, decimal_to_minor(campaign["DiscountPrice"]))
    claimed = max(list_price, shelf_price)
    original = claimed if claimed > pay else None

    color = data.get("ColorName")
    variants = [
        RawVariant(
            external_sku=size["MatrixId"],
            size_label=_size_label(size["SizeName"]),
            color_raw=color,
            price_minor=pay,
            original_price_minor=original,
            in_stock=int(size["StockQuantity"]) > 0,
        )
        for size in data["Sizes"]
    ]
    category = _category_path(data)
    return RawProduct(
        external_id=product_id(url),
        url=url,
        title=data.get("ProductVariantName") or data["Name"],
        category_raw=category,
        audience=_audience(category),
        image_urls=_images(html),
        currency="TRY",
        variants=variants,
    )


def _js_value(html: str, marker: str) -> Any:
    """Decode the JSON value that follows `marker` inside an inline script."""
    start = html.find(marker)
    if start < 0:
        raise ValueError(f"{marker!r} not found")
    value, _ = _DECODER.raw_decode(html, start + len(marker))
    return value


def _campaign_is_active(
    campaign: dict[str, Any] | None, data: dict[str, Any], now: datetime
) -> bool:
    # The DataLayer repeats the campaign price (rounded); requiring both guards against picking up
    # a badge that belongs to something else on the page.
    if not campaign or data.get("CampaignDiscountedPrice") is None:
        return False
    starts = datetime.fromisoformat(campaign["StartDate"]).replace(tzinfo=TURKEY)
    ends = datetime.fromisoformat(campaign["EndDate"]).replace(tzinfo=TURKEY)
    return starts <= now <= ends


def _size_label(name: str) -> str:
    """'Beden 30 - Boy 32' -> '30/32' (waist/length); everything else stays as the site shows it."""
    match = _WAIST_LENGTH.match(name.strip())
    return f"{match.group(1)}/{match.group(2)}" if match else name


def _category_path(data: dict[str, Any]) -> str | None:
    names = [
        level["CategoryName"]
        for key in ("CategoriesLvl1", "CategoriesLvl2", "CategoriesLvl3")
        if (level := data.get(key)) and level.get("CategoryName")
    ]
    return " > ".join(names) or None


def _audience(category: str | None) -> Audience | None:
    """'Erkek > Giyim > Mont' is men. Boys ('Erkek Çocuk - Genç Erkek > ...') and babies ('Erkek
    Bebek > ...') are not: the root segment must match exactly."""
    root = category.split(" > ")[0] if category else None
    return _AUDIENCE_ROOTS.get(root) if root else None


def _images(html: str) -> list[str]:
    for block in _JSON_LD.findall(html):
        try:
            item, _ = _DECODER.raw_decode(block.strip())
        except ValueError:
            continue
        if isinstance(item, dict) and item.get("@type") == "Product":
            images = item.get("image") or []
            return [images] if isinstance(images, str) else list(images)
    return []
