"""change_only_observations

Price observations become stretches: one row per unchanged state (price, claimed original, stock,
currency, status) with `observed_at` (first seen) and `last_seen_at` (latest run that saw it).
Owner decision 25 Oct 2026, to fit 3-6 brands in Neon's free 0.5 GB (docs/DATA_MODEL.md).

Existing rows are merged: each run of identical consecutive rows of a variant keeps its first row,
with `last_seen_at` set to the last row's `observed_at`; the rest are deleted. Downgrade drops the
column but cannot split merged rows again (a Neon backup branch was taken before upgrading prod).

Revision ID: 5e1f0c3a9b27
Revises: cc0bdde53854
Create Date: 2026-10-25 01:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5e1f0c3a9b27"
down_revision: str | Sequence[str] | None = "cc0bdde53854"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "price_observations",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Gaps and islands: a row starts a new stretch when its state differs from the previous row
    # of the same variant; a running sum of those starts numbers the stretches.
    op.execute(
        """
        CREATE TEMP TABLE stretch ON COMMIT DROP AS
        WITH marked AS (
            SELECT id, variant_id, observed_at,
                   CASE WHEN lag((price_minor, original_price_minor, in_stock, currency, status))
                             OVER w IS NOT DISTINCT FROM
                             (price_minor, original_price_minor, in_stock, currency, status)
                        THEN 0 ELSE 1 END AS starts
            FROM price_observations
            WINDOW w AS (PARTITION BY variant_id ORDER BY observed_at, id)
        ), numbered AS (
            SELECT id, variant_id, observed_at,
                   sum(starts) OVER (PARTITION BY variant_id ORDER BY observed_at, id) AS n
            FROM marked
        )
        SELECT id,
               first_value(id) OVER s AS keep_id,
               max(observed_at) OVER s AS last_seen_at
        FROM numbered
        WINDOW s AS (PARTITION BY variant_id, n ORDER BY observed_at, id
                     ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
        """
    )
    op.execute(
        """
        UPDATE price_observations p SET last_seen_at = s.last_seen_at
        FROM stretch s WHERE p.id = s.id AND s.id = s.keep_id
        """
    )
    op.execute(
        "DELETE FROM price_observations p USING stretch s WHERE p.id = s.id AND s.id <> s.keep_id"
    )
    op.alter_column("price_observations", "last_seen_at", nullable=False)
    op.create_check_constraint(
        op.f("ck_price_observations_seen_order"),
        "price_observations",
        "last_seen_at >= observed_at",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_price_observations_seen_order"), "price_observations", type_="check"
    )
    op.drop_column("price_observations", "last_seen_at")
