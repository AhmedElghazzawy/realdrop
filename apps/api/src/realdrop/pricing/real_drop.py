"""The real-drop rule: is today's price really lower than usual? docs/DATA_MODEL.md.

Pure functions over one variant's confirmed daily close prices; no database, no LLM. This is the
only place a discount is computed (CLAUDE.md rule 1).

Percentages are exact Fractions (no float near money): `real_discount` 0.25 means 25% below the
reference price; negative means the price went up.
"""

import enum
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction
from statistics import median

from realdrop.pricing import config


class DropStatus(enum.StrEnum):
    REAL_DROP = "real_drop"
    SMALL_DROP = "small_drop"
    NORMAL = "normal"
    PRICE_UP = "price_up"
    INSUFFICIENT_HISTORY = "insufficient_history"


@dataclass(frozen=True)
class Verdict:
    status: DropStatus
    reference_minor: Fraction | None  # median of the window; None without enough history
    real_discount: Fraction | None
    claimed_discount: Fraction | None  # what the shop says, whatever our history says
    claim_inflated: bool
    all_time_low: bool


def _pct(value: int) -> Fraction:
    return Fraction(value, 100)


def claimed_discount(price_minor: int, claimed_original_minor: int | None) -> Fraction | None:
    if claimed_original_minor is None or claimed_original_minor <= price_minor:
        return None
    return Fraction(claimed_original_minor - price_minor, claimed_original_minor)


def evaluate(
    *,
    day: date,
    price_minor: int,
    in_stock: bool,
    claimed_original_minor: int | None,
    history: Mapping[date, int],
) -> Verdict:
    """Verdict for a variant's confirmed close price `price_minor` on `day`.

    `history` maps earlier Istanbul days to that day's confirmed close price; days the variant was
    not tracked are simply missing. Entries for `day` or later are ignored.
    """
    past = {d: p for d, p in history.items() if d < day}
    window = [p for d, p in past.items() if d >= day - timedelta(days=config.REFERENCE_WINDOW_DAYS)]
    claimed = claimed_discount(price_minor, claimed_original_minor)

    if len(window) < config.MIN_HISTORY_DAYS:
        # No claim of our own, so nothing to call inflated either.
        return Verdict(DropStatus.INSUFFICIENT_HISTORY, None, None, claimed, False, False)

    # Median of exact Fractions stays exact (an even count averages the middle two).
    reference = median(Fraction(p) for p in window)
    real = (reference - price_minor) / reference
    recent = [p for d, p in past.items() if d >= day - timedelta(days=config.RECENT_LOW_DAYS)]

    if real >= _pct(config.REAL_DROP_PCT):
        # A big drop that is not at the recent low (or not buyable) is still only a small drop:
        # we only say "real drop" when all three hold.
        is_real = in_stock and bool(recent) and price_minor <= min(recent)
        status = DropStatus.REAL_DROP if is_real else DropStatus.SMALL_DROP
    elif real >= _pct(config.SMALL_DROP_PCT):
        status = DropStatus.SMALL_DROP
    elif real > -_pct(config.SMALL_DROP_PCT):
        status = DropStatus.NORMAL
    else:
        status = DropStatus.PRICE_UP

    inflated = (
        claimed is not None
        and claimed >= _pct(config.CLAIM_INFLATED_PCT)
        and claimed - real >= _pct(config.CLAIM_GAP_PCT)
    )
    return Verdict(
        status=status,
        reference_minor=reference,
        real_discount=real,
        claimed_discount=claimed,
        claim_inflated=inflated,
        all_time_low=price_minor <= min(past.values()),
    )
