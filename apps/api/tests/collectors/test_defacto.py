"""DeFacto parser and collector against real men's listing pages saved from the site on 30 Oct 2026
(fixtures/)."""

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from realdrop.collectors.base import ItemFailure, RawProduct, RawVariant, Shard
from realdrop.collectors.defacto import parser
from realdrop.collectors.defacto.collector import DefactoCollector
from realdrop.collectors.http import CollectorBlockedError, CollectorServerError, PoliteClient

FIXTURES = Path(__file__).resolve().parents[2] / "src/realdrop/collectors/defacto/fixtures"
BASE = "https://www.defacto.com.tr"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


LISTING_NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
CLOTHING = load("listing_men_clothing.html")  # page 1 of /erkek-giyim: 5,206 products
ACCESSORIES = load("listing_men_accessories.html")  # page 1 of /erkek-aksesuar: 253, 1 promo tile


def card(page: str, product_id: int) -> dict[str, object]:
    return next(c for c in parser.listing_cards(page) if c["ProductVariantIndex"] == product_id)


def test_listing_card_has_prices_sizes_images_and_category() -> None:
    raw = parser.parse_card(card(CLOTHING, 3430455), "Erkek > Giyim", LISTING_NOW)
    assert raw is not None
    assert raw.external_id == "3430455"
    assert str(raw.url) == f"{BASE}/sicak-tutan-su-itici-kapusonlu-mont-3430455"
    assert raw.title == "Sıcak Tutan Su İtici Kapüşonlu Mont"
    assert raw.category_raw == "Erkek > Giyim > Mont"
    assert raw.audience == "men"
    assert str(raw.image_urls[0]) == "https://dfcdn.defacto.com.tr/7/F1149AX_26WN_BK27_01_03.jpg"
    assert len(raw.image_urls) == 4
    # The card lists XL, S, L, M, XXL; a shop shows S to XXL. Only sizes in stock are listed.
    assert [v.size_label for v in raw.variants] == ["S", "M", "L", "XL", "XXL"]
    assert all(v.in_stock for v in raw.variants)
    assert raw.variants[0].external_sku == "8684585182447"  # the barcode
    assert {(v.price_minor, v.original_price_minor) for v in raw.variants} == {(349999, None)}


def test_listing_card_campaign_price_is_what_you_pay() -> None:
    raw = parser.parse_card(card(CLOTHING, 3430169), "Erkek > Giyim", LISTING_NOW)
    assert raw is not None
    assert (raw.variants[0].price_minor, raw.variants[0].original_price_minor) == (125999, 179999)
    after = datetime(2026, 12, 1, tzinfo=UTC)  # the campaign ends 30 Nov 2026, 23:59 Turkey time
    ended = parser.parse_card(card(CLOTHING, 3430169), "Erkek > Giyim", after)
    assert ended is not None
    assert (ended.variants[0].price_minor, ended.variants[0].original_price_minor) == (179999, None)


def test_listing_skips_promo_tiles_and_sorts_numeric_sizes() -> None:
    cards = parser.listing_cards(ACCESSORIES)
    assert len(cards) == 23  # 24 tiles, one of them a promo
    belt = parser.parse_card(card(ACCESSORIES, 3536706), "Erkek > Aksesuar", LISTING_NOW)
    assert belt is not None
    assert [v.size_label for v in belt.variants] == ["90", "100", "110"]
    assert parser.listing_total(ACCESSORIES) == 253
    assert parser.listing_total("<html>Bakım çalışması</html>") is None


def test_card_that_is_not_men_or_has_no_size_in_stock_is_left_out() -> None:
    women = {**card(CLOTHING, 3430455), "SubDivision": "Woman"}
    sold_out = {**card(CLOTHING, 3430455), "Sizes": []}
    assert parser.parse_card(women, "Erkek > Giyim", LISTING_NOW) is None
    assert parser.parse_card(sold_out, "Erkek > Giyim", LISTING_NOW) is None


END_OF_LISTING = "<html><div class=catalog-products id=product-fill></div></html>"


def _clothing_page(number: int) -> str:
    """A 2-page clothing listing: page 1 is the real page with its total set to 30, page 2 reuses
    the accessories cards (23, a short last page), and past it there is no total and no cards, as
    on the real site (seen 30 Oct 2026)."""
    if number > 2:
        return END_OF_LISTING
    if number == 1:
        return CLOTHING.replace(
            "id=totalCount type=hidden value=5206", "id=totalCount type=hidden value=30"
        )
    return ACCESSORIES


def _site(
    broken: frozenset[str] = frozenset(), robots: str = "User-agent: *\nDisallow: *q=*\n"
) -> httpx.MockTransport:
    """Fake DeFacto. `broken` holds "path?page=N" keys that always answer 502."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        number = int(request.url.params.get("page", "1"))
        if path == "/robots.txt":
            return httpx.Response(200, text=robots)
        if f"{path}?page={number}" in broken:
            return httpx.Response(502)
        if path == "/erkek-giyim":
            return httpx.Response(200, text=_clothing_page(number))
        if path == "/erkek-aksesuar":  # the same products as clothing page 2: deduplicated
            return httpx.Response(200, text=ACCESSORIES.replace("value=253", "value=20"))
        return httpx.Response(404)  # /erkek-ayakkabi: missing this run

    return httpx.MockTransport(handler)


async def no_sleep(seconds: float) -> None:
    return None


async def collect(
    transport: httpx.MockTransport, shard: Shard | None = None
) -> list[RawProduct | ItemFailure]:
    client = PoliteClient(user_agent="realdrop-bot/test", transport=transport, sleep=no_sleep)
    async with client:
        collector = DefactoCollector(client, shard=shard, now=lambda: LISTING_NOW)
        return [item async for item in collector.fetch_catalog()]


def _ids(results: list[RawProduct | ItemFailure]) -> list[str]:
    return [r.external_id for r in results if isinstance(r, RawProduct)]


async def test_collector_reads_every_page_once_and_each_product_once() -> None:
    results = await collect(_site())
    ids = _ids(results)
    assert len(ids) == len(set(ids)) == 24 + 23  # clothing page 1 + page 2; aksesuar adds nothing
    failures = [r for r in results if isinstance(r, ItemFailure)]
    assert failures == [ItemFailure(source=f"{BASE}/erkek-ayakkabi?page=1", reason="HTTP 404")]


async def test_one_broken_listing_page_is_skipped_not_the_whole_run() -> None:
    results = await collect(_site(broken=frozenset({"/erkek-giyim?page=2"})))
    failures = [r for r in results if isinstance(r, ItemFailure)]
    assert any(
        f.source == f"{BASE}/erkek-giyim?page=2" and "HTTP 502" in f.reason for f in failures
    )
    # The run goes on: the accessories listing (the same cards as page 2 here) still comes.
    assert len(_ids(results)) == 24 + 23


async def test_broken_pages_in_a_row_stop_the_run() -> None:
    broken = frozenset({"/erkek-giyim?page=2", "/erkek-giyim?page=3", "/erkek-giyim?page=4"})
    with pytest.raises(CollectorServerError, match="HTTP 502"):
        await collect(_site(broken=broken))


async def test_page_without_listing_data_stops_the_run() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text="<html>Lütfen bekleyin...</html>")  # challenge-like

    with pytest.raises(CollectorBlockedError, match="without product data"):
        await collect(httpx.MockTransport(handler))


async def test_listing_robots_disallows_stops_the_run() -> None:
    with pytest.raises(CollectorBlockedError):
        await collect(_site(robots="User-agent: *\nDisallow: /erkek-giyim\n"))


def test_dry_run_formats_prices_turkish_style() -> None:
    from realdrop.collectors.run import describe, format_try

    assert format_try(129999) == "1.299,99 TL"
    assert format_try(5) == "0,05 TL"
    product = RawProduct(
        external_id="1",
        url=f"{BASE}/pantolon-1",
        title="Pantolon",
        currency="TRY",
        variants=[
            RawVariant(
                external_sku="1-M", price_minor=77999, original_price_minor=129999, in_stock=True
            )
        ],
    )
    assert "779,99 TL (claimed 1.299,99 TL)" in describe(product)


async def test_shards_split_the_products_and_each_lands_once() -> None:
    halves = [_ids(await collect(_site(), shard=Shard(index, 2))) for index in range(2)]
    assert halves[0] and halves[1]
    assert sorted(halves[0] + halves[1]) == sorted(_ids(await collect(_site())))


@pytest.mark.parametrize(
    ("category", "audience"),
    [
        ("Erkek > Giyim > Mont", "men"),
        ("Kadın > İç Giyim > Sütyen", "women"),
        ("Erkek Çocuk - Genç Erkek > Giyim", None),
        ("Erkek Bebek > Giyim", None),
        (None, None),
    ],
)
def test_audience_from_category_root(category: str | None, audience: str | None) -> None:
    assert parser._audience(category) == audience


async def test_a_listing_that_grew_during_the_run_is_read_to_its_new_end() -> None:
    """Page 1 says 24 products (1 page) but is full, so the listing may have grown: page 2 is read
    too, and the end-of-listing page after it finishes the listing without stopping the run."""

    def handler(request: httpx.Request) -> httpx.Response:
        number = int(request.url.params.get("page", "1"))
        if request.url.path != "/erkek-giyim":
            return httpx.Response(404)
        pages = {1: CLOTHING.replace("value=5206", "value=24"), 2: ACCESSORIES}
        return httpx.Response(200, text=pages.get(number, END_OF_LISTING))

    assert len(_ids(await collect(httpx.MockTransport(handler)))) == 24 + 23
