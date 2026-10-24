"""Turn retailer price text and JSON numbers into integer kurus (CLAUDE.md rule 5).

Turkish formatting uses "." for thousands and "," for decimals: "1.299,90 TL" is 1299.90 TRY.
Anything ambiguous raises ValueError: a wrong price is worse than a missing one.
"""

import re
from decimal import Decimal, InvalidOperation

from realdrop.text import normalize, tr_lower

_CURRENCY_TOKENS = ("₺", "lira", "try", "tl")

_TR_DECIMAL = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+),(\d{1,2})")  # 1.299,90  1299,9
_THOUSANDS_ONLY = re.compile(r"\d{1,3}(?:\.\d{3})+")  # 1.299  12.500.000
_PLAIN = re.compile(r"(\d+)(?:\.(\d{1,2}))?")  # 1299  1299.90 (JSON-style)


def parse_tr_price(text: str) -> int:
    """Parse a displayed price into kurus: "1.299,90 TL" -> 129990, "₺899" -> 89900."""
    cleaned = tr_lower(normalize(text))
    for token in _CURRENCY_TOKENS:
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.replace(" ", "")

    if match := _TR_DECIMAL.fullmatch(cleaned):
        whole, fraction = match[1].replace(".", ""), match[2]
    elif _THOUSANDS_ONLY.fullmatch(cleaned):
        whole, fraction = cleaned.replace(".", ""), ""
    elif match := _PLAIN.fullmatch(cleaned):
        whole, fraction = match[1], match[2] or ""
    else:
        raise ValueError(f"unrecognised price: {text!r}")
    return int(whole) * 100 + int(fraction.ljust(2, "0"))


def decimal_to_minor(value: int | str | Decimal | float) -> int:
    """Convert a JSON price in major units (1299.9, "1299.90", 1299) to kurus.

    Floats are accepted only because JSON APIs send them; they go through str() first, because
    Decimal(0.1) would carry the binary float error into the price. More than 2 decimals raises.
    """
    if isinstance(value, bool):
        raise TypeError("a bool is not a price")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"unrecognised price: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError(f"unrecognised price: {value!r}")
    minor = amount * 100
    if minor != minor.to_integral_value():
        raise ValueError(f"price has more than 2 decimals: {value!r}")
    return int(minor)
