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
