"""Read-only catalog views for the web app: collection status, product list, product detail.

Prices are integer kurus with their currency; the web app formats them (DESIGN_SYSTEM.md).
Only confirmed observations are shown (glitch filter, DATA_MODEL.md).
"""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from realdrop.models import RunStatus

SortOrder = Literal["recent", "price_asc", "price_desc", "claimed_discount"]
Audience = Literal["men", "women"]


class BrandStats(BaseModel):
    slug: str
    name: str
    products: int
    variants: int
    observations: int
    tracking_since: datetime | None


class RunOut(BaseModel):
    id: uuid.UUID
    brand_slug: str
    started_at: datetime
    finished_at: datetime | None
    status: RunStatus
    items_seen: int
    items_failed: int
    notes: str | None


class StatsOut(BaseModel):
    brands: list[BrandStats]
    runs: list[RunOut]


class ProductCard(BaseModel):
    id: uuid.UUID
    brand_slug: str
    brand_name: str
    title: str
    url: str
    image_url: str | None
    category: str | None
    # Lowest confirmed price among the product's sizes right now, and the claim shown next to it.
    price_minor: int
    original_price_minor: int | None
    currency: str
    sizes_in_stock: int
    sizes_total: int
    first_seen_at: datetime
    observed_at: datetime


class ProductList(BaseModel):
    items: list[ProductCard]
    total: int


class VariantOut(BaseModel):
    size_label: str | None
    in_stock: bool
    price_minor: int
    original_price_minor: int | None


class PricePoint(BaseModel):
    day: date  # Europe/Istanbul calendar day (CLAUDE.md rule 7)
    price_minor: int  # lowest confirmed price that day across sizes
    original_price_minor: int | None


class ProductDetail(ProductCard):
    image_urls: list[str]
    variants: list[VariantOut]
    history: list[PricePoint]
