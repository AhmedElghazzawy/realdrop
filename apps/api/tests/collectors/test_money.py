from decimal import Decimal

import pytest

from realdrop.collectors.money import decimal_to_minor, parse_tr_price


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.299,90 TL", 129990),
        ("1.299,9 TL", 129990),
        ("1.299 TL", 129900),
        ("12.500.000 TL", 1250000000),
        ("299,99", 29999),
        ("₺899", 89900),
        ("₺ 1.049,50", 104950),
        ("2.499,90 TL", 249990),  # non-breaking space, common in HTML
        ("899 TRY", 89900),
        ("1500 lira", 150000),
        ("1.500 Lira", 150000),
        ("1299.90", 129990),  # JSON-style decimal point
        ("1299", 129900),
        ("0", 0),  # parsed; the glitch filter rejects it later
    ],
)
def test_parse_tr_price(text: str, expected: int) -> None:
    assert parse_tr_price(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "TL", "Fiyat için tıklayın", "1,299.90", "12,345", "1.2.3", "-100 TL", "1.299,999"],
)
def test_parse_tr_price_rejects_ambiguous_or_garbage(text: str) -> None:
    with pytest.raises(ValueError, match="unrecognised price"):
        parse_tr_price(text)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1299, 129900),
        ("1299.90", 129990),
        (Decimal("1299.9"), 129990),
        (1299.9, 129990),
        (0.1 + 0.2, None),  # 0.30000000000000004: more than 2 decimals, must not be rounded away
    ],
)
def test_decimal_to_minor(value: int | str | Decimal | float, expected: int | None) -> None:
    if expected is None:
        with pytest.raises(ValueError, match="more than 2 decimals"):
            decimal_to_minor(value)
    else:
        assert decimal_to_minor(value) == expected


@pytest.mark.parametrize("value", ["abc", "NaN", "Infinity"])
def test_decimal_to_minor_rejects_garbage(value: str) -> None:
    with pytest.raises(ValueError, match="unrecognised price"):
        decimal_to_minor(value)


def test_decimal_to_minor_rejects_bool() -> None:
    with pytest.raises(TypeError):
        decimal_to_minor(True)
