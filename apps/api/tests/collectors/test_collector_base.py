from typing import Any

import pytest
from pydantic import ValidationError

from realdrop.collectors.base import RawProduct, RawVariant
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
