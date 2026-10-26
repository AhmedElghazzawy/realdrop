"""Pure parsing for Akinon storefronts: product JSON in, RawProduct out. No IO.

A classic Akinon storefront answers a product URL requested with `Accept: application/json` with
the page's data (checked on Koton, Mudo, GAP, Marks & Spencer and Damat Tween, 27 Oct 2026):

- `product`: the product the URL points at, which is one size of one colour. Its `base_code`
  (model) and `listing_code` (colour) identify the colour, which is our product.
- `variants`: one entry per dimension ("Renk", "Beden", Koton's "Boy" for leg length). Each
  option carries the full `product` of that choice, with its own `price`, `retail_price` (the
  shop's "old" price) and `in_stock`. Size options can point at another colour's product (Koton,
  when the page's colour lacks that size), so only options in the page's colour are its sizes.
- `product.basket_offers`: coupon-style offers ("KTN20 KODU İLE %20"). Not what everyone pays,
  so ignored, like every conditional offer.

Attribute names differ per brand (gender is `filterable_gender`, `cinsiyet` or `gender`), so the
parser looks for each in a short list of known keys.
"""

import re
from typing import Any

from realdrop.collectors.base import Audience, RawProduct, RawVariant
from realdrop.collectors.money import decimal_to_minor
from realdrop.text import tr_lower

_COLOR_DIMENSIONS = {"Renk", "RENK", "Color"}
_SIZE_DIMENSIONS = {"Beden", "BEDEN", "Size"}
_LENGTH_DIMENSIONS = {"Boy", "BOY"}  # Koton jeans: leg length, a second size dimension
_GENDER_KEYS = ("filterable_gender", "filterable_cinsiyet", "cinsiyet", "gender")
_CATEGORY_KEYS = (
    "filterable_category",
    "filterable_kategori",
    "morhipo_kategori",
    "productType",  # GAP: "Eşofman Alt"
    "integration_MalSinifAdi",  # Mudo: "SWEATSHIRT"
)
_GENDERS: dict[str, Audience] = {"erkek": "men", "kadın": "women", "kadin": "women"}
_TRAILING_CODE = re.compile(r"\s*\(\d+\)$")  # Damat Tween: "ESOFMAN ÜST (159)"


def parse_product(data: dict[str, Any], url: str) -> RawProduct:
    """Raises KeyError, TypeError or ValueError (incl. pydantic ValidationError) on bad input."""
    page = data["product"]
    dimensions = {v["attribute_name"]: v for v in data.get("variants") or []}
    color_key = _first_key(dimensions, _COLOR_DIMENSIONS)
    length_key = _first_key(dimensions, _LENGTH_DIMENSIONS)
    page_color = page["attributes"].get(color_key) if color_key else None
    # The attribute holds a code ("741"); the colour option with that value has the name.
    color_names = {
        o["value"]: o["label"]
        for name in _COLOR_DIMENSIONS
        if name in dimensions
        for o in dimensions[name]["options"]
    }
    color_name = color_names.get(page_color, page_color)

    size = next((dimensions[n] for n in _SIZE_DIMENSIONS if n in dimensions), None)
    if size is None:
        sized = [(None, page)]  # one-size product (a bag, a belt)
    else:
        # Every size and length option points at one size's product; together they cover more
        # waist/length pairs than the size options alone (Koton jeans). Same product, same pk.
        size_key = size["attribute_key"]
        labels = {o["value"]: o["label"] for o in size["options"]}
        options = size["options"] + (
            dimensions[_length_name(dimensions)]["options"] if length_key else []
        )
        products = {o["product"]["pk"]: o["product"] for o in options}
        # When the page's colour is sold out, every size option can point at other colours (Damat
        # Tween). The page itself is always one size of its colour, so the colour stays tracked.
        products.setdefault(page["pk"], page)
        sized = [
            (labels.get(p["attributes"].get(size_key), p["attributes"].get(size_key)), p)
            for p in products.values()
        ]
    variants = []
    for label, product in sized:
        # When the colour cannot be compared (GAP names it differently per size), keep them all.
        if page_color is not None and product["attributes"].get(color_key) != page_color:
            continue
        length = product["attributes"].get(length_key) if length_key else None
        price = decimal_to_minor(product["price"])
        retail = decimal_to_minor(product["retail_price"])
        variants.append(
            RawVariant(
                external_sku=str(product["pk"]),
                size_label=f"{label}/{length}" if label and length else label,
                color_raw=color_name,
                price_minor=price,
                original_price_minor=retail if retail > price else None,
                in_stock=bool(product["in_stock"]),
            )
        )
    return RawProduct(
        external_id=f"{page['base_code']}-{page['listing_code']}",
        url=url,
        title=page["name"],
        category_raw=_category(page["attributes"]),
        audience=_audience(page["attributes"]),
        image_urls=[i["image"] for i in page.get("productimage_set") or [] if i.get("image")],
        currency=page["currency_type"].upper(),
        variants=variants,
    )


def audience_of(attributes: dict[str, Any]) -> Audience | None:
    """Public for listing pages, whose items carry the same attributes."""
    return _audience(attributes)


def _length_name(dimensions: dict[str, Any]) -> str:
    return next(n for n in _LENGTH_DIMENSIONS if n in dimensions)


def _first_key(dimensions: dict[str, Any], names: set[str]) -> str | None:
    for name in names:
        if name in dimensions:
            return str(dimensions[name]["attribute_key"])
    return None


def _audience(attributes: dict[str, Any]) -> Audience | None:
    """'Erkek' / 'erkek' is men; 'Kız Çocuk', 'kiz_bebek', 'Erkek Çocuk' are not (exact match)."""
    for key in _GENDER_KEYS:
        value = attributes.get(key)
        if isinstance(value, str) and value.strip():
            return _GENDERS.get(tr_lower(value.strip()))
    return None


def _category(attributes: dict[str, Any]) -> str | None:
    for key in _CATEGORY_KEYS:
        value = attributes.get(key)
        if isinstance(value, str) and value.strip():
            return _TRAILING_CODE.sub("", value.strip())
    return None
