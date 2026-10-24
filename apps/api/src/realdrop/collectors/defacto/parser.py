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
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from realdrop.collectors.base import RawProduct, RawVariant
from realdrop.collectors.money import decimal_to_minor

BASE_URL = "https://www.defacto.com.tr"
# Turkey has used UTC+3 all year since 2016; campaign dates on the site are local, without offset.
TURKEY = timezone(timedelta(hours=3))

_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
_ROOT_ENDS = ("</urlset>", "</sitemapindex>")
_PRODUCT_SITEMAP = re.compile(r"/sharedxml/tr-tr/product(-\d+)?\.xml$")
_PRODUCT_ID = re.compile(r"-(\d{6,})/?$")
_WAIST_LENGTH = re.compile(r"^Beden (.+?) - Boy (.+)$")
_JSON_LD = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S)
_DECODER = json.JSONDecoder(parse_float=Decimal)


def sitemap_locs(xml_text: str) -> list[str]:
    """Every <loc> in a sitemap or sitemap index, in document order.

    DeFacto's product-5.xml (Oct 2026) has stale text after `</urlset>`, as if a shorter file was
    written over a longer one. Everything up to the first closing root tag is a complete document,
    so the tail is cut off; any other XML error still raises.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        end = min(
            (i + len(tag) for tag in _ROOT_ENDS if (i := xml_text.find(tag)) >= 0), default=-1
        )
        if end < 0:
            raise
        root = ET.fromstring(xml_text[:end])
    return [loc.text.strip() for loc in root.iter(f"{_SITEMAP_NS}loc") if loc.text]


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
    return RawProduct(
        external_id=product_id(url),
        url=url,
        title=data.get("ProductVariantName") or data["Name"],
        category_raw=_category_path(data),
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
