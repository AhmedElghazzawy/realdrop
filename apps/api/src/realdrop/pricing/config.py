"""Tunable thresholds for price validation and (later) the real-drop rule. docs/DATA_MODEL.md.

Percentages are integers so every comparison stays in integer arithmetic (no floats near money).
"""

from datetime import timedelta
from typing import Final

# Glitch filter (pipeline/validate.py)
MIN_PRICE_MINOR: Final = 500  # 5 TRY; anything cheaper is a parsing or data error
BIG_CHANGE_PCT: Final = 70  # a jump or fall of >= 70% vs the last confirmed price is held
MEDIAN_FLOOR_PCT: Final = 20  # a price below 20% of the 30-day median is held
MEDIAN_WINDOW: Final = timedelta(days=30)
CONFIRM_AFTER: Final = timedelta(minutes=30)  # a repeat this much later confirms a held price
PENDING_EXPIRY: Final = timedelta(hours=48)  # held prices not confirmed by then are rejected

# Real-drop rule (pricing/real_drop.py)
MIN_HISTORY_DAYS: Final = 14  # fewer tracked days than this: no real-discount claim at all
REFERENCE_WINDOW_DAYS: Final = 30  # the reference price is the median of this many previous days
RECENT_LOW_DAYS: Final = 7  # a real drop must also be at or below the low of these days
REAL_DROP_PCT: Final = 10
SMALL_DROP_PCT: Final = 3  # also the width of the "normal" band in both directions
CLAIM_INFLATED_PCT: Final = 20  # a claimed discount at least this big...
CLAIM_GAP_PCT: Final = 15  # ...and this much bigger than the real one is flagged as inflated
