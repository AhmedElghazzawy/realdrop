"""Glitch filter rules (docs/DATA_MODEL.md). Pure: no database."""

from datetime import UTC, datetime, timedelta

import pytest

from realdrop.models import PriceStatus
from realdrop.pipeline.validate import classify, confirms

CONFIRMED, PENDING, REJECTED = PriceStatus.CONFIRMED, PriceStatus.PENDING, PriceStatus.REJECTED


@pytest.mark.parametrize("price", [0, -100, 499])
def test_impossible_prices_are_rejected(price: int) -> None:
    assert classify(price, None, None, []).status is REJECTED


def test_first_sighting_is_confirmed() -> None:
    assert classify(500, None, None, []).status is CONFIRMED


@pytest.mark.parametrize(
    ("price", "status"),
    [
        (100_000, CONFIRMED),  # unchanged
        (50_000, CONFIRMED),  # -50%: a big sale, but believable
        (30_001, CONFIRMED),  # just under -70%
        (30_000, PENDING),  # exactly -70%
        (1_000, PENDING),  # "10,00 TL" for a 1.000 TL coat
        (169_999, CONFIRMED),  # +69.999%
        (170_000, PENDING),  # +70%
    ],
)
def test_big_moves_against_last_confirmed_are_held(price: int, status: PriceStatus) -> None:
    assert classify(price, None, 100_000, [100_000]).status is status


def test_below_a_fifth_of_the_median_is_held_even_if_last_price_was_low() -> None:
    # The last confirmed price was already low, so the 70% rule alone would let this through.
    verdict = classify(15_000, None, 20_000, [100_000, 100_000, 100_000, 20_000])
    assert verdict.status is PENDING
    assert verdict.reason is not None and "median" in verdict.reason


def test_claimed_original_below_price_is_held() -> None:
    verdict = classify(100_000, 90_000, 100_000, [100_000])
    assert verdict == classify(100_000, 90_000, None, [])
    assert verdict.status is PENDING


def test_claimed_original_above_price_is_fine() -> None:
    assert classify(64_999, 129_999, 64_999, [64_999]).status is CONFIRMED


T0 = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)


def test_seen_again_later_confirms() -> None:
    assert not confirms(T0, T0 + timedelta(minutes=29))  # too soon
    assert confirms(T0, T0 + timedelta(minutes=30))
    assert confirms(T0, T0 + timedelta(hours=24))
    assert not confirms(T0, T0 + timedelta(hours=48))  # expired
