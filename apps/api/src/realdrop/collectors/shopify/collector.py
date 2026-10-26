"""One collector for every Shopify shop; brands.py configures it per brand.

The whole catalog comes from `/products.json`, 250 products per request (a 2,000-product shop is
8 requests), so there are no per-product pages to fetch. Both shards read every catalog page and
keep their half of the products (by URL), which costs only a few extra requests.

The catalog JSON has no currency, and a shop can show converted prices to a visitor abroad (our
GitHub runners are in the US). So each run first reads the currency the shop's home page is
showing (`Shopify.currency.active`) and stops unless it is the brand's currency.
"""

import re
from collections.abc import AsyncIterator
from typing import Any, ClassVar

from realdrop.collectors.base import Audience, BrandCollector, ItemFailure, RawProduct
from realdrop.collectors.http import CollectorError
from realdrop.collectors.shopify.parser import parse_product

PAGE_SIZE = 250  # Shopify's maximum
MAX_PAGES = 200  # a safety stop: 50,000 products, far above any shop we collect
_ACTIVE_CURRENCY = re.compile(r'Shopify\.currency\s*=\s*\{\s*"active"\s*:\s*"([A-Z]{3})"')


class ShopifyCollector(BrandCollector):
    """Subclass per brand (see brands.py)."""

    currency: ClassVar[str] = "TRY"
    # For a brand whose products carry no gender tag (a men's-only brand).
    default_audience: ClassVar[Audience | None] = None
    # Owner decision 27 Oct 2026: new brands store men only. None keeps everything.
    only_audience: ClassVar[Audience | None] = "men"

    async def fetch_catalog(self) -> AsyncIterator[RawProduct | ItemFailure]:
        await self._check_currency()
        for page in range(1, MAX_PAGES + 1):
            response = await self.client.get(
                f"{self.base_url}/products.json", params={"limit": PAGE_SIZE, "page": page}
            )
            products: list[dict[str, Any]] = response.json()["products"]
            if not products:
                return
            for product in products:
                for item in self._parse(product):
                    yield item
        raise CollectorError(f"{self.slug}: more than {MAX_PAGES} catalog pages; raise MAX_PAGES?")

    async def _check_currency(self) -> None:
        home = await self.client.get(f"{self.base_url}/")
        match = _ACTIVE_CURRENCY.search(home.text)
        active = match.group(1) if match else None
        if active != self.currency:
            raise CollectorError(
                f"{self.base_url} shows prices in {active or 'an unknown currency'}, "
                f"expected {self.currency}; nothing collected"
            )

    def _parse(self, product: dict[str, Any]) -> list[RawProduct | ItemFailure]:
        source = f"{self.base_url}/products/{product.get('handle')}"
        try:
            parsed = parse_product(product, self.base_url, self.currency)
        except (KeyError, TypeError, ValueError) as exc:
            return [ItemFailure(source=source, reason=f"{type(exc).__name__}: {exc}"[:500])]
        results: list[RawProduct | ItemFailure] = []
        for raw in parsed:
            if not self.shard.contains(str(raw.url)):
                continue
            if raw.audience is None and self.default_audience is not None:
                raw = raw.model_copy(update={"audience": self.default_audience})
            if self.only_audience is None or raw.audience == self.only_audience:
                results.append(raw)
        return results
