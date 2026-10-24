"""The real-drop rule, on synthetic price series (docs/DATA_MODEL.md, docs/EVALS.md pricing suite).

The property-style tests run each check over many seeded random series, so a failure is
reproducible from the seed in the assertion message.
"""

import random
from datetime import date, timedelta
from fractions import Fraction

import pytest

from realdrop.pricing import config
from realdrop.pricing.real_drop import DropStatus, claimed_discount, evaluate

TODAY = date(2026, 11, 27)


def flat(price: int, days: int = 30) -> dict[date, int]:
    return {TODAY - timedelta(days=d): price for d in range(1, days + 1)}


def run(price: int, history: dict[date, int], *, claimed: int | None = None, in_stock: bool = True):
    return evaluate(
        day=TODAY,
        price_minor=price,
        in_stock=in_stock,
        claimed_original_minor=claimed,
        history=history,
    )


def random_series(rng: random.Random, days: int = 30) -> dict[date, int]:
    base = rng.randint(10_000, 500_000)
    return {
        TODAY - timedelta(days=d): max(500, base + rng.randint(-base // 10, base // 10))
        for d in range(1, days + 1)
        if rng.random() > 0.2  # some days untracked
    }


# --- no claim without enough history ---------------------------------------------------------


def test_thirteen_days_is_not_enough() -> None:
    verdict = run(5_000, flat(10_000, days=13), claimed=20_000)
    assert verdict.status is DropStatus.INSUFFICIENT_HISTORY
    assert verdict.real_discount is None
    assert verdict.reference_minor is None
    assert not verdict.claim_inflated
    assert not verdict.all_time_low
    # The shop's own claim is still reported, as a claim.
    assert verdict.claimed_discount == Fraction(3, 4)


def test_fourteen_days_is_enough() -> None:
    assert run(8_000, flat(10_000, days=14)).status is DropStatus.REAL_DROP


def test_days_older_than_the_window_do_not_count_towards_history() -> None:
    old = {TODAY - timedelta(days=d): 10_000 for d in range(31, 60)}
    assert run(8_000, old).status is DropStatus.INSUFFICIENT_HISTORY


def test_today_and_later_in_history_are_ignored() -> None:
    history = flat(10_000, days=13) | {TODAY: 10_000, TODAY + timedelta(days=1): 10_000}
    assert run(8_000, history).status is DropStatus.INSUFFICIENT_HISTORY


# --- statuses at their boundaries --------------------------------------------------------------


@pytest.mark.parametrize(
    ("price", "status"),
    [
        (9_000, DropStatus.REAL_DROP),  # exactly 10% below
        (9_001, DropStatus.SMALL_DROP),
        (9_700, DropStatus.SMALL_DROP),  # exactly 3% below
        (9_701, DropStatus.NORMAL),
        (10_000, DropStatus.NORMAL),
        (10_299, DropStatus.NORMAL),
        (10_300, DropStatus.PRICE_UP),  # exactly 3% above
    ],
)
def test_status_boundaries(price: int, status: DropStatus) -> None:
    assert run(price, flat(10_000)).status is status


def test_big_drop_out_of_stock_is_only_small() -> None:
    assert run(5_000, flat(10_000), in_stock=False).status is DropStatus.SMALL_DROP


def test_big_drop_above_last_weeks_low_is_only_small() -> None:
    # Usually 10,000, but it was 7,000 three days ago: 8,000 today is no new low.
    history = flat(10_000) | {TODAY - timedelta(days=3): 7_000}
    verdict = run(8_000, history)
    assert verdict.real_discount == Fraction(1, 5)
    assert verdict.status is DropStatus.SMALL_DROP


def test_big_drop_with_no_tracked_day_in_the_last_week_is_only_small() -> None:
    history = {d: p for d, p in flat(10_000).items() if d < TODAY - timedelta(days=7)}
    assert run(8_000, history).status is DropStatus.SMALL_DROP


# --- the reference price -----------------------------------------------------------------------


def test_one_day_spike_does_not_move_the_reference() -> None:
    history = flat(10_000) | {TODAY - timedelta(days=5): 90_000}
    assert run(10_000, history).reference_minor == 10_000
    assert run(10_000, history).status is DropStatus.NORMAL


def test_inflate_then_discount_is_not_a_real_drop() -> None:
    # The classic trick: raise the price for a few days, then "discount" back to the old price.
    history = flat(10_000) | {TODAY - timedelta(days=d): 15_000 for d in range(1, 4)}
    verdict = run(10_000, history, claimed=15_000)
    assert verdict.status is DropStatus.NORMAL
    assert verdict.claim_inflated


def test_even_window_median_is_exact() -> None:
    history = {TODAY - timedelta(days=d): (10_000 if d % 2 else 10_001) for d in range(1, 15)}
    assert run(10_000, history).reference_minor == Fraction(20_001, 2)


# --- flags --------------------------------------------------------------------------------------


def test_claim_inflated_needs_a_big_claim() -> None:
    # Claims 19% off a price that is really normal: not big enough to flag.
    assert not run(10_000, flat(10_000), claimed=12_346).claim_inflated
    assert run(10_000, flat(10_000), claimed=12_500).claim_inflated  # claims 20%


def test_honest_claim_is_not_inflated() -> None:
    verdict = run(7_000, flat(10_000), claimed=10_000)
    assert verdict.claimed_discount == verdict.real_discount == Fraction(3, 10)
    assert not verdict.claim_inflated


def test_all_time_low_uses_all_history_not_just_the_window() -> None:
    history = flat(10_000) | {TODAY - timedelta(days=200): 6_000}
    assert not run(8_000, history).all_time_low
    assert run(6_000, history).all_time_low


def test_claimed_discount_ignores_claims_at_or_below_the_price() -> None:
    assert claimed_discount(10_000, None) is None
    assert claimed_discount(10_000, 10_000) is None
    assert claimed_discount(10_000, 9_000) is None
    assert claimed_discount(7_500, 10_000) == Fraction(1, 4)


# --- properties over random series --------------------------------------------------------------

SEEDS = range(300)


@pytest.mark.parametrize("seed", SEEDS)
def test_lower_price_never_gets_a_worse_verdict(seed: int) -> None:
    """Monotonic: dropping the price never lowers the real discount or the status rank."""
    rank = [
        DropStatus.PRICE_UP,
        DropStatus.NORMAL,
        DropStatus.SMALL_DROP,
        DropStatus.REAL_DROP,
    ]
    rng = random.Random(seed)
    history = random_series(rng)
    if len(history) < config.MIN_HISTORY_DAYS:
        return
    high = rng.randint(1_000, 600_000)
    low = rng.randint(500, high)
    a, b = run(high, history), run(low, history)
    assert a.real_discount is not None and b.real_discount is not None
    assert b.real_discount >= a.real_discount, seed
    assert rank.index(b.status) >= rank.index(a.status), seed


@pytest.mark.parametrize("seed", SEEDS)
def test_flags_do_not_change_the_status(seed: int) -> None:
    """The shop's claim never changes our status; it only sets the claim flags."""
    rng = random.Random(seed)
    history = random_series(rng)
    price = rng.randint(500, 600_000)
    claimed = price + rng.randint(1, 600_000)
    with_claim, without = run(price, history, claimed=claimed), run(price, history)
    assert with_claim.status is without.status, seed
    assert with_claim.real_discount == without.real_discount, seed
    assert not without.claim_inflated


@pytest.mark.parametrize("seed", SEEDS)
def test_real_drop_always_meets_every_condition(seed: int) -> None:
    rng = random.Random(seed)
    history = random_series(rng)
    price = rng.randint(500, 600_000)
    verdict = run(price, history, in_stock=rng.random() > 0.3)
    if verdict.status is DropStatus.REAL_DROP:
        recent = [p for d, p in history.items() if d >= TODAY - timedelta(days=7)]
        assert verdict.real_discount is not None
        assert verdict.real_discount >= Fraction(config.REAL_DROP_PCT, 100), seed
        assert recent and price <= min(recent), seed
