"""DeFacto collector: the men's category listings, 24 products a page, one polite GET per page.

Until 30 Oct 2026 we fetched one product page per product (~20,000 pages). DeFacto answered 502
after about 650 pages in every run (25-29 Oct, at 1 and at 0.5 request/s, different pages each
time), so only the same ~650 products were ever refreshed. A listing card carries everything we
store (prices, campaign, sizes in stock, images), so about 230 listing pages cover all ~5,500 men's
products. Both shards read every listing page and keep their half of the products (by URL), like
the Shopify collector.

A listing page that keeps failing with 5xx after all retries is skipped (its products wait for the
next run); a few broken pages in a row, or a page without listing data (a challenge or maintenance
page), stop the run instead of hammering the site.
"""

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime

import httpx

from realdrop.collectors.base import BrandCollector, ItemFailure, RawProduct, Shard
from realdrop.collectors.defacto.parser import (
    BASE_URL,
    LISTINGS,
    listing_cards,
    listing_pages,
    listing_total,
    parse_card,
)
from realdrop.collectors.http import CollectorBlockedError, CollectorServerError, PoliteClient

CARDS_PER_PAGE = 24
MAX_BROKEN_PAGES_IN_A_ROW = 3
EXTRA_PAGES = 3  # read past the stated page count while pages still bring new products


class DefactoCollector(BrandCollector):
    slug = "defacto"
    name = "DeFacto"
    base_url = BASE_URL
    rate_limit_rps = 0.5

    def __init__(
        self,
        client: PoliteClient,
        *,
        shard: Shard | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        super().__init__(client, shard=shard)
        self._now = now
        self._broken_in_a_row = 0
        self._seen: set[str] = set()  # product ids, across listings and shards

    async def fetch_catalog(self) -> AsyncIterator[RawProduct | ItemFailure]:
        for path, category_root in LISTINGS:
            async for item in self._listing(f"{BASE_URL}/{path}", category_root):
                yield item

    async def _listing(
        self, url: str, category_root: str
    ) -> AsyncIterator[RawProduct | ItemFailure]:
        pages = 1
        number = 1
        while number <= pages + EXTRA_PAGES:
            page = await self._page(url, number)
            if isinstance(page, ItemFailure):
                yield page
                if number == 1:
                    return  # without the first page we do not know the listing's size; next run
                number += 1
                continue
            total = listing_total(page)
            if total is None:
                # Past the stated last page the site serves a page with no products and no total.
                if number > pages:
                    return
                raise CollectorBlockedError(
                    f"listing page without product data (challenge or maintenance page?): "
                    f"{url}?page={number}"
                )
            if number == 1:
                pages = listing_pages(total, CARDS_PER_PAGE)
            cards, items = self._products(page, f"{url}?page={number}", category_root)
            new = 0
            for item in items:
                if isinstance(item, RawProduct):
                    new += 1
                    if not self.shard.contains(str(item.url)):
                        continue
                yield item
            # The last page is short (5,225 = 217 x 24 + 17 on 30 Oct 2026). A full last page means
            # the listing grew during the run, so read on while pages bring new products.
            if number >= pages and (cards < CARDS_PER_PAGE or new == 0):
                return
            number += 1

    async def _page(self, url: str, number: int) -> str | ItemFailure:
        source = f"{url}?page={number}"
        try:
            response = await self.client.get(url, params={"page": number} if number > 1 else None)
        except CollectorServerError as exc:
            self._broken_in_a_row += 1
            if self._broken_in_a_row >= MAX_BROKEN_PAGES_IN_A_ROW:
                raise
            return ItemFailure(source=source, reason=str(exc))
        except httpx.HTTPStatusError as exc:
            return ItemFailure(source=source, reason=f"HTTP {exc.response.status_code}")
        self._broken_in_a_row = 0  # the site answered, so it is not down
        return response.text

    def _products(
        self, page: str, source: str, category_root: str
    ) -> tuple[int, list[RawProduct | ItemFailure]]:
        """How many product cards the page has, and its new products (each product once per run)
        plus failures for bad cards."""
        try:
            cards = listing_cards(page)
        except ValueError as exc:
            reason = f"cards do not decode: {exc}"[:500]
            return CARDS_PER_PAGE, [ItemFailure(source=source, reason=reason)]
        items: list[RawProduct | ItemFailure] = []
        for index, card in enumerate(cards):
            try:
                raw = parse_card(card, category_root, self._now())
            except (KeyError, TypeError, ValueError) as exc:
                reason = f"{type(exc).__name__}: {exc}"[:500]
                items.append(ItemFailure(source=f"{source}#{index}", reason=reason))
                continue
            if raw is None or raw.external_id in self._seen:
                continue
            self._seen.add(raw.external_id)
            items.append(raw)
        return len(cards), items
