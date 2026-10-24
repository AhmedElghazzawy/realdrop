"""Every model, imported here so `Base.metadata` knows all tables (Alembic autogenerate)."""

from realdrop.models.catalog import Brand, Product, Variant
from realdrop.models.prices import (
    CollectionRun,
    PriceDaily,
    PriceObservation,
    PriceStatus,
    RunStatus,
)

__all__ = [
    "Brand",
    "CollectionRun",
    "PriceDaily",
    "PriceObservation",
    "PriceStatus",
    "Product",
    "RunStatus",
    "Variant",
]
