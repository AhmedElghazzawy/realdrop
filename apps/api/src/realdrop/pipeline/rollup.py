"""Roll confirmed observations up into `price_daily`: one row per variant per Istanbul day.

A confirmed stretch (see pipeline/store.py) covers every Istanbul day from `observed_at` to
`last_seen_at`. Per day: close = the stretch seen last that day, low/high over all stretches that
touch the day. A day between two runs that both saw the same price counts as tracked at that
price. collectors/run.py rebuilds the last ROLLUP_LOOKBACK days after each run, so after a longer
outage the older gap days stay empty. A day no stretch covers has no row.

Rows are rebuilt, not patched: every variant seen since `since` gets its days from `since`'s day on
deleted and recomputed, so re-running is always safe.
"""

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_TOUCHED = """
    SELECT DISTINCT variant_id FROM price_observations
    WHERE status = 'confirmed' AND last_seen_at >= :since
"""

_DELETE = f"""
    DELETE FROM price_daily
    WHERE variant_id IN ({_TOUCHED})
      AND snapshot_date >= (CAST(:since AS timestamptz) AT TIME ZONE 'Europe/Istanbul')::date
"""

_INSERT = f"""
    INSERT INTO price_daily (variant_id, snapshot_date, close_price_minor, low_price_minor,
                             high_price_minor, claimed_original_minor, currency, in_stock_close)
    SELECT variant_id, day,
           (array_agg(price_minor ORDER BY observed_at DESC, id DESC))[1],
           min(price_minor),
           max(price_minor),
           (array_agg(original_price_minor ORDER BY observed_at DESC, id DESC))[1],
           (array_agg(currency ORDER BY observed_at DESC, id DESC))[1],
           (array_agg(in_stock ORDER BY observed_at DESC, id DESC))[1]
    FROM (
        SELECT o.*, d::date AS day
        FROM price_observations o
        CROSS JOIN LATERAL generate_series(
            (o.observed_at AT TIME ZONE 'Europe/Istanbul')::date,
            (o.last_seen_at AT TIME ZONE 'Europe/Istanbul')::date,
            interval '1 day'
        ) AS d
        WHERE o.status = 'confirmed'
          AND o.variant_id IN ({_TOUCHED})
          AND (o.last_seen_at AT TIME ZONE 'Europe/Istanbul')::date
              >= (CAST(:since AS timestamptz) AT TIME ZONE 'Europe/Istanbul')::date
    ) AS covered
    WHERE day >= (CAST(:since AS timestamptz) AT TIME ZONE 'Europe/Istanbul')::date
    GROUP BY variant_id, day
"""


async def refresh_daily(session: AsyncSession, since: datetime) -> int:
    """Rebuild `price_daily` for days from `since` on. Returns how many rows were written."""
    params = {"since": since}
    await session.execute(text(_DELETE), params)
    result = await session.execute(text(_INSERT), params)
    return int(result.rowcount)  # type: ignore[attr-defined]
