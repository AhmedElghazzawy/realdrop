"""Derived product attributes and style tags.

Schema doc: docs/architecture/data-model.md, "product_attributes".

One row per product, written by pipeline/tagging.py from the pure rules in pipeline/tagger.py
(later refined by the LLM pass). Derived data: it can be rebuilt from `products` at any time, and
it is rebuilt whenever the product's `content_hash` or TAGGER_VERSION changes.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, text

from realdrop.db.base import Base

_EMPTY = text("'{}'::text[]")


class ProductAttributes(Base):
    __tablename__ = "product_attributes"
    __table_args__ = (
        CheckConstraint("source IN ('rules', 'llm')", name="source_values"),
        Index("ix_product_attributes_style_tags", "style_tags", postgresql_using="gin"),
        Index("ix_product_attributes_colors", "colors", postgresql_using="gin"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True
    )
    style_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=_EMPTY)
    colors: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=_EMPTY)
    pattern: Mapped[str | None] = mapped_column(String(16))
    fit: Mapped[str | None] = mapped_column(String(16))
    material: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=_EMPTY)
    formality: Mapped[str | None] = mapped_column(String(16))
    season: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=_EMPTY)
    occasion: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=_EMPTY)
    subcategory: Mapped[str | None] = mapped_column(String(24))
    source: Mapped[str] = mapped_column(String(8))
    # Per field, where the value came from ("title", "color", "inferred", "llm").
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    tagger_version: Mapped[int] = mapped_column(SmallInteger)
    # The product's content_hash when it was tagged: a different hash means re-tag.
    content_hash: Mapped[str] = mapped_column(String(64))
    tagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
