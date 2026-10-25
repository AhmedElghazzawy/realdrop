"""Price tables: collection runs, raw observations, daily roll-up (docs/DATA_MODEL.md, "Prices").

Money is integer kurus (`*_minor`) with the currency stored next to it (CLAUDE.md rule 5).
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from realdrop.db.base import Base
from realdrop.models.catalog import uuid_pk


class RunStatus(enum.StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"  # finished, but some items failed
    FAILED = "failed"  # stopped early: blocked (403), robots.txt, or too many errors


class PriceStatus(enum.StrEnum):
    """Glitch-filter outcome. Only CONFIRMED rows feed prices, the real-drop rule and alerts."""

    CONFIRMED = "confirmed"
    PENDING = "pending"
    REJECTED = "rejected"


def _pg_enum(enum_cls: type[enum.StrEnum], name: str) -> Enum:
    # Store the lowercase values ("confirmed"), not the Python member names ("CONFIRMED").
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[RunStatus] = mapped_column(
        _pg_enum(RunStatus, "run_status"), server_default=RunStatus.RUNNING.value
    )
    items_seen: Mapped[int] = mapped_column(Integer, server_default="0")
    items_failed: Mapped[int] = mapped_column(Integer, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)


class PriceObservation(Base):
    """One row per stretch of unchanged state (price, claimed original, stock, currency, status).

    A run that sees the same state again only moves `last_seen_at` forward; any change starts a new
    row. Besides that, only the glitch-filter status is ever updated (pipeline/store.py).
    """

    __tablename__ = "price_observations"
    __table_args__ = (
        Index("ix_price_observations_variant_id_observed_at", "variant_id", "observed_at"),
        CheckConstraint("last_seen_at >= observed_at", name="seen_order"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("variants.id", ondelete="RESTRICT")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(  # the run that first saw this state
        UUID(as_uuid=True), ForeignKey("collection_runs.id", ondelete="RESTRICT")
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # first seen
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # No CHECK on price here: impossible prices are stored as `rejected` with a reason, so the
    # glitch filter's decisions stay auditable.
    price_minor: Mapped[int] = mapped_column(BigInteger)
    original_price_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    in_stock: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[PriceStatus] = mapped_column(_pg_enum(PriceStatus, "price_status"))
    reject_reason: Mapped[str | None] = mapped_column(Text)


class PriceDaily(Base):
    """Derived from confirmed observations; `snapshot_date` is the Europe/Istanbul calendar day."""

    __tablename__ = "price_daily"
    __table_args__ = (
        CheckConstraint("low_price_minor > 0", name="low_positive"),
        CheckConstraint(
            "low_price_minor <= close_price_minor AND close_price_minor <= high_price_minor",
            name="low_close_high_order",
        ),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("variants.id", ondelete="RESTRICT"), primary_key=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    close_price_minor: Mapped[int] = mapped_column(BigInteger)
    low_price_minor: Mapped[int] = mapped_column(BigInteger)
    high_price_minor: Mapped[int] = mapped_column(BigInteger)
    claimed_original_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    in_stock_close: Mapped[bool] = mapped_column(Boolean)
