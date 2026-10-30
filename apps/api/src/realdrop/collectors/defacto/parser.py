"""Pure parsing for DeFacto: listing-page HTML in, RawProduct out. No IO.

The collector reads the men's category listings (`/erkek-giyim?page=N`, 24 products a page).
Each product card carries a `data-documents='{...}'` JSON blob with the same fields as the
product page's `DataLayer` (name, colour, `Price`, `DiscountedPrice`, `CampaignDiscountedPrice`,
`CampaignBadge` with dates, `SubDivision`, and the sizes in stock with their barcodes), and
`window.productImageN=[...]` lists the card's images. See docs/brands/defacto.md.

Product pages (`parse_product`) carry three blobs we used before listings (until 30 Oct 2026):
- `DataLayer:{...}`: name, colour, category path, list price, and one entry per size with a stable
  `MatrixId` and `StockQuantity`.
- `CampaignBadge:{...}` or `null`: a basket campaign ("Sepette Net %50 İndirim") with its price and
  start/end dates. It needs no coupon or second item, so its price is what everyone pays.
- schema.org `Product` JSON-LD: image URLs.

Price meaning: `price_minor` is what a shopper pays today (campaign price if one is active, else the
shelf price); `original_price_minor` is the higher price the site shows next to it, if any. Numbers
are decoded as Decimal and converted with money.decimal_to_minor, never through float.
"""

import html
import json
import math
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

IMAGE_BASE = "https://dfcdn.defacto.com.tr/7/"  # the size the product page's JSON-LD links to
# Men only (owner decision, 30 Oct 2026): the listings we read and the category root each one adds.
LISTINGS: tuple[tuple[str, str], ...] = (
    ("erkek-giyim", "Erkek > Giyim"),
    ("erkek-ayakkabi", "Erkek > Ayakkabı"),
    ("erkek-aksesuar", "Erkek > Aksesuar"),
)
_TOTAL = re.compile(r"id=totalCount type=hidden value=(\d+)")
# The card's opening tag: data-type is empty for products ("freeItem" is a promo tile).
_CARD = re.compile(
    r"<div data-index=(\d+) class=product-card data-type=\"([^\"]*)\"[^>]*?data-documents='([^']*)'"
)
_CARD_IMAGES = re.compile(r"window\.productImage(\d+)=(\[.*?\]);")
_LETTER_SIZES = ("XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL", "6XL")


def product_sitemaps(index_xml: str) -> list[str]:
    return [url for url in sitemap_locs(index_xml) if _PRODUCT_SITEMAP.search(url)]


def product_id(url: str) -> str:
    match = _PRODUCT_ID.search(url)
    if match is None:
        raise ValueError(f"no product id in {url}")
    return match.group(1)


def listing_total(page: str) -> int | None:
    """The number of products in the whole listing, as the page states it; None if missing."""
    match = _TOTAL.search(page)
    return int(match.group(1)) if match else None


def listing_pages(total: int, per_page: int) -> int:
    return max(1, math.ceil(total / per_page))


def listing_cards(page: str) -> list[dict[str, Any]]:
    """The product cards on a listing page, each with its `images` (file names) added.
    Raises ValueError on a card whose JSON does not decode."""
    images = {int(i): _DECODER.decode(blob) for i, blob in _CARD_IMAGES.findall(page)}
    cards = []
    for index, kind, documents in _CARD.findall(page):
        if kind:  # a promo tile, not a product
            continue
        card: dict[str, Any] = _DECODER.decode(html.unescape(documents))
        card["images"] = [
            item["imagePath"] for item in images.get(int(index), []) if item.get("isProductImage")
        ]
        cards.append(card)
    return cards


def parse_card(card: dict[str, Any], category_root: str, now: datetime) -> RawProduct | None:
    """One listing card -> RawProduct, or None when it is not a men's product or has no size in
    stock (a listing shows only sizes in stock). Raises KeyError, TypeError or ValueError (incl.
    pydantic ValidationError) on bad input."""
    if card.get("SubDivision") != "Man":
        return None
    list_price = decimal_to_minor(card["Price"])
    shelf_price = decimal_to_minor(card["DiscountedPrice"])
    pay = shelf_price
    campaign = card.get("CampaignBadge")
    if _campaign_is_active(campaign, card, now):
        pay = min(pay, decimal_to_minor(campaign["DiscountPrice"]))  # type: ignore[index]
    claimed = max(list_price, shelf_price)
    original = claimed if claimed > pay else None

    sizes = {size["Barcode"]: size for size in card["Sizes"] if size.get("Barcode")}
    if not sizes:
        return None
    color = card.get("ColorName")
    variants = [
        RawVariant(
            external_sku=barcode,
            size_label=_size_label(size["SizeName"]),
            color_raw=color,
            price_minor=pay,
            original_price_minor=original,
            in_stock=True,
        )
        for barcode, size in sorted(
            sizes.items(), key=lambda item: _size_order(item[1]["SizeName"])
        )
    ]
    product_id = str(card["ProductVariantIndex"])
    pictures = card["images"] or ([card["PictureName"]] if card.get("PictureName") else [])
    leaf = card.get("CategoryName")
    return RawProduct(
        external_id=product_id,
        url=f"{BASE_URL}/{card['SeoName']}-{product_id}",
        title=card.get("ProductVariantName") or card["Name"],
        category_raw=f"{category_root} > {leaf}" if leaf else category_root,
        audience="men",
        image_urls=[f"{IMAGE_BASE}{name}" for name in pictures],
        currency="TRY",
        variants=variants,
    )


def _size_order(name: str) -> tuple[int, float, str]:
    """Cards list sizes in no order; sort them as a shop does: S, M, L, ... then 90, 100, ..."""
    label = _size_label(name)
    if label in _LETTER_SIZES:
        return (0, _LETTER_SIZES.index(label), label)
    number = re.match(r"\d+(?:[.,]\d+)?", label)
    if number:
        return (1, float(number.group().replace(",", ".")), label)
    return (2, 0.0, label)


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
