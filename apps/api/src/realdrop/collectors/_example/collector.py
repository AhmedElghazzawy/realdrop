"""Template collector for an imaginary shop with a paginated JSON API.

Copy this folder for a real brand (add-brand-collector skill). The shape stays the same: the
collector does IO through the PoliteClient, the parser stays pure, and one bad product becomes an
ItemFailure instead of ending the run.
"""

from collections.abc import AsyncIterator

from realdrop.collectors._example.parser import parse_listing, parse_product
from realdrop.collectors.base import BrandCollector, ItemFailure, RawProduct

MAX_PAGES = 500  # safety stop if the API ever loops


class ExampleCollector(BrandCollector):
    slug = "_example"
    base_url = "https://shop.example.com"
    rate_limit_rps = 1.0

    async def fetch_catalog(self) -> AsyncIterator[RawProduct | ItemFailure]:
        page: int | None = 1
        while page is not None and page <= MAX_PAGES:
            url = f"{self.base_url}/api/products"
            payload = await self.client.get_json(url, params={"page": page})
            items, page = parse_listing(payload)
            for item in items:
                try:
                    yield parse_product(item)
                except (KeyError, TypeError, ValueError) as exc:
                    source = str(item.get("id") or item.get("url") or "unknown")
                    yield ItemFailure(source=source, reason=f"{type(exc).__name__}: {exc}"[:500])
