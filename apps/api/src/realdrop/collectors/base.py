"""What every brand collector produces, and the interface it implements.

A collector only fetches and parses. It never writes to the database and never decides whether a
price is plausible: storage is `pipeline/store.py`, plausibility is the glitch filter
(`pipeline/validate.py`). Retailer text is untrusted data (CLAUDE.md rule 9): it is normalized and
validated here, never interpreted.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Annotated, ClassVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictBool,
    StrictInt,
    model_validator,
)

from realdrop.collectors.http import PoliteClient
from realdrop.config import get_settings
from realdrop.text import normalize


def _non_empty(text: str) -> str:
    if not text:
        raise ValueError("must not be empty")
    return text


Text = Annotated[str, AfterValidator(normalize)]
NonEmptyText = Annotated[str, AfterValidator(normalize), AfterValidator(_non_empty)]


class RawVariant(BaseModel):
    """One sellable size/color of a product, with its price as seen right now."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    external_sku: NonEmptyText
    size_label: Text | None = None
    color_raw: Text | None = None
    # StrictInt: a float price (12.99) is a parser bug and must fail loudly, not be truncated.
    price_minor: StrictInt
    # Only when the site shows a strike-through or "old price"; otherwise None.
    original_price_minor: StrictInt | None = None
    in_stock: StrictBool


class RawProduct(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    external_id: NonEmptyText
    url: HttpUrl
    title: NonEmptyText
    description: Text | None = None
    category_raw: Text | None = None
    image_urls: list[HttpUrl] = Field(default_factory=list)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    variants: list[RawVariant] = Field(min_length=1)

    @model_validator(mode="after")
    def _skus_unique(self) -> "RawProduct":
        skus = [v.external_sku for v in self.variants]
        if len(skus) != len(set(skus)):
            raise ValueError(f"duplicate variant SKUs in product {self.external_id}")
        return self


class ItemFailure(BaseModel):
    """One product that could not be parsed. Counted in `collection_runs.items_failed`."""

    model_config = ConfigDict(frozen=True)

    source: str  # product id or URL, whatever identifies it best
    reason: str


class BrandCollector(ABC):
    """Subclass per brand in `collectors/<slug>/collector.py`; see the add-brand-collector skill."""

    slug: ClassVar[str]
    name: ClassVar[str]  # display name for the brands table
    base_url: ClassVar[str]
    rate_limit_rps: ClassVar[float] = 1.0

    def __init__(self, client: PoliteClient) -> None:
        self.client = client

    @classmethod
    def make_client(cls) -> PoliteClient:
        return PoliteClient(
            user_agent=get_settings().collector_user_agent, rate_limit_rps=cls.rate_limit_rps
        )

    @abstractmethod
    def fetch_catalog(self) -> AsyncIterator[RawProduct | ItemFailure]:
        """Yield every tracked product. A product that fails to parse becomes an ItemFailure and
        the run continues; CollectorBlockedError / CollectorGaveUpError end the run."""
