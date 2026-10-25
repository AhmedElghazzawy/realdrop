"""Glitch filter: decide whether a newly observed price can be trusted. docs/DATA_MODEL.md.

Pure functions, no database: pipeline/store.py loads the history and applies the verdict.

- Reject: price <= 0 or below MIN_PRICE_MINOR.
- Hold as pending: >= BIG_CHANGE_PCT away from the last confirmed price, below MEDIAN_FLOOR_PCT of
  the 30-day median, or a claimed original price below the price (an impossible claim).
- A pending price is confirmed when a later run sees the same state again at least CONFIRM_AFTER
  after it was first seen, and rejected if that does not happen within PENDING_EXPIRY.

A one-off glitch ("1,00 TL" for a coat) therefore never reaches price history, alerts or the
real-drop rule; a real, large price change is only delayed until the next run sees it again.
"""

from dataclasses import dataclass
from datetime import datetime
from statistics import median_low

from realdrop.models import PriceStatus
from realdrop.pricing import config


@dataclass(frozen=True)
class Verdict:
    status: PriceStatus
    reason: str | None = None


def classify(
    price_minor: int,
    original_price_minor: int | None,
    last_confirmed_minor: int | None,
    recent_confirmed_minor: list[int],
) -> Verdict:
    """Verdict for one new observation, before looking at earlier pending ones."""
    if price_minor <= 0 or price_minor < config.MIN_PRICE_MINOR:
        return Verdict(PriceStatus.REJECTED, f"price {price_minor} below minimum")
    if original_price_minor is not None and original_price_minor < price_minor:
        return Verdict(PriceStatus.PENDING, "claimed original below price")
    if last_confirmed_minor is not None:
        change = abs(price_minor - last_confirmed_minor)
        if change * 100 >= config.BIG_CHANGE_PCT * last_confirmed_minor:
            return Verdict(PriceStatus.PENDING, f"changed >= {config.BIG_CHANGE_PCT}% vs last")
    if recent_confirmed_minor:
        median = median_low(recent_confirmed_minor)  # an observed value, so stays an int
        if price_minor * 100 < config.MEDIAN_FLOOR_PCT * median:
            return Verdict(PriceStatus.PENDING, f"below {config.MEDIAN_FLOOR_PCT}% of median")
    return Verdict(PriceStatus.CONFIRMED)


def confirms(first_seen: datetime, seen_again: datetime) -> bool:
    """Does seeing a pending state again at `seen_again` confirm it? Not too soon, not expired."""
    return config.CONFIRM_AFTER <= seen_again - first_seen < config.PENDING_EXPIRY
