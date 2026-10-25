"""Catalog tables: brands, products, variants (docs/DATA_MODEL.md, "Catalog").

Catalog rows are never deleted, only marked inactive: price history points at them and is the
product's main asset. Foreign keys therefore use RESTRICT.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from realdrop.db.base import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(Text)
    country: Mapped[str] = mapped_column(String(2), server_default="TR")
    currency: Mapped[str] = mapped_column(String(3), server_default="TRY")
    base_url: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    collector_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )

    products: Mapped[list["Product"]] = relationship(back_populates="brand")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("brand_id", "external_id"),
        CheckConstraint("audience IN ('men', 'women')", name="audience_values"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"))
    external_id: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    title_raw: Mapped[str] = mapped_column(Text)
    description_raw: Mapped[str | None] = mapped_column(Text)
    image_urls: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'::text[]"))
    category_raw: Mapped[str | None] = mapped_column(Text)
    # 'men' | 'women' when the shop says so plainly (collectors/base.py); kids and unclear: NULL.
    audience: Mapped[str | None] = mapped_column(String(8), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    brand: Mapped[Brand] = relationship(back_populates="products")
    variants: Mapped[list["Variant"]] = relationship(back_populates="product")


class Variant(Base):
    __tablename__ = "variants"
    __table_args__ = (UniqueConstraint("product_id", "external_sku"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    external_sku: Mapped[str] = mapped_column(Text)
    size_label: Mapped[str | None] = mapped_column(Text)
    size_normalized: Mapped[str | None] = mapped_column(Text)
    color_raw: Mapped[str | None] = mapped_column(Text)
    color_normalized: Mapped[str | None] = mapped_column(Text)

    product: Mapped[Product] = relationship(back_populates="variants")
