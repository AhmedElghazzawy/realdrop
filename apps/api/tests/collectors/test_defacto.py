"""DeFacto parser and collector against real pages saved from the site (fixtures/): product pages
on 24 Oct 2026, men's listing pages on 30 Oct 2026."""

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from realdrop.collectors.base import ItemFailure, RawProduct, Shard
from realdrop.collectors.defacto import parser
from realdrop.collectors.defacto.collector import DefactoCollector
from realdrop.collectors.http import CollectorBlockedError, CollectorServerError, PoliteClient

FIXTURES = Path(__file__).resolve().parents[2] / "src/realdrop/collectors/defacto/fixtures"
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
BASE = "https://www.defacto.com.tr"
TROUSERS = f"{BASE}/regular-fit-normal-bel-duz-paca-uzun-boy-pantolon-3455834"
BRA = f"{BASE}/buzgulu-dantel-detayli-pamuklu-cikarilabilir-kap-sutyen-3518142"
BABY_SET = f"{BASE}/2li-takim-baskili-kisa-kollu-fitilli-kaskorse-tisort-beli-lastikli-sort-kiz-bebek-3272557"  # noqa: E501
GONE = f"{BASE}/silinmis-urun-3000001"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_campaign_price_is_what_you_pay_and_list_price_is_the_claim() -> None:
    product = parser.parse_product(load("product_campaign_waist_length.html"), TROUSERS, NOW)

    assert product.external_id == "3455834"
    assert product.title == "Regular Fıt Normal Bel Düz Paça Uzun Boy Pantolon"  # site's own text
    assert product.category_raw == "Erkek > Giyim > Pantolon"
    assert product.currency == "TRY"
    assert len(product.image_urls) > 1
    # "Sepette Net %40 İndirim": 1299.99 on the shelf, 779.99 at checkout for everyone.
    assert {v.price_minor for v in product.variants} == {77999}
    assert {v.original_price_minor for v in product.variants} == {129999}
    assert {v.color_raw for v in product.variants} == {"Açık Gri"}


def test_waist_and_length_sizes_and_per_size_stock() -> None:
    product = parser.parse_product(load("product_campaign_waist_length.html"), TROUSERS, NOW)
    by_size = {v.size_label: v for v in product.variants}

    assert len(product.variants) == 18
    assert by_size["28/30"].in_stock is True
    assert by_size["30/32"].in_stock is False
    assert by_size["28/30"].external_sku == "69897a43-9003-4a08-87f3-4b6d6849d28a"


def test_campaign_outside_its_dates_is_ignored() -> None:
    after_end = datetime(2026, 12, 1, tzinfo=UTC)  # campaign ends 30 Nov 23:59 Turkey time
    product = parser.parse_product(load("product_campaign_waist_length.html"), TROUSERS, after_end)
    assert {v.price_minor for v in product.variants} == {129999}
    assert {v.original_price_minor for v in product.variants} == {None}


def test_campaign_end_is_turkey_time() -> None:
    # 30 Nov 23:59 in Turkey is 20:59 UTC: one minute later the campaign is over.
    html = load("product_campaign_waist_length.html")
    last_minute = parser.parse_product(html, TROUSERS, datetime(2026, 11, 30, 20, 59, tzinfo=UTC))
    too_late = parser.parse_product(html, TROUSERS, datetime(2026, 11, 30, 21, 0, tzinfo=UTC))
    assert last_minute.variants[0].price_minor == 77999
    assert too_late.variants[0].price_minor == 129999


def test_product_without_campaign_has_no_claimed_price() -> None:
    product = parser.parse_product(load("product_no_campaign.html"), BRA, NOW)
    assert [v.size_label for v in product.variants] == ["S", "M", "L", "XL"]
    assert {v.price_minor for v in product.variants} == {49999}
    assert {v.original_price_minor for v in product.variants} == {None}
    assert all(v.in_stock for v in product.variants)


def test_mostly_sold_out_product_keeps_every_size() -> None:
    product = parser.parse_product(load("product_mostly_sold_out.html"), BABY_SET, NOW)
    assert [(v.size_label, v.in_stock) for v in product.variants] == [
        ("1-3 Ay (62cm)", True),
        ("3-6 Ay (68cm)", False),
        ("6-9 Ay (74cm)", False),
        ("9-12 Ay (80cm)", False),
        ("12-18 Ay (86cm)", False),
    ]
    assert product.variants[0].price_minor == 14999  # Sepette %70 of 499.99


def test_page_without_product_data_raises() -> None:
    html = "<html><body>Bakım çalışması</body></html>"
    assert parser.has_product_data(html) is False
    with pytest.raises(ValueError, match="DataLayer"):
        parser.parse_product(html, TROUSERS, NOW)


def test_sitemaps() -> None:
    assert parser.product_sitemaps(load("sitemap_index.xml")) == [
        f"{BASE}/sharedxml/tr-tr/product-3.xml",
        f"{BASE}/sharedxml/tr-tr/product.xml",
    ]
    assert parser.sitemap_locs(load("sitemap_product.xml")) == [TROUSERS, BRA]
    with pytest.raises(ValueError, match="no product id"):
        parser.product_id(f"{BASE}/kadin-giyim")


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
    product = parser.parse_product(load("product_campaign_waist_length.html"), TROUSERS, NOW)
    assert "779,99 TL (claimed 1.299,99 TL)" in describe(product)


async def test_shards_split_the_products_and_each_lands_once() -> None:
    halves = [_ids(await collect(_site(), shard=Shard(index, 2))) for index in range(2)]
    assert halves[0] and halves[1]
    assert sorted(halves[0] + halves[1]) == sorted(_ids(await collect(_site())))


def test_sitemap_with_stale_tail_after_the_root_still_parses() -> None:
    # Shape of DeFacto's product-5.xml on 24 Oct 2026.
    xml = load("sitemap_product.xml") + "let Yaka Kazak</image:title>\n  </url>\n</urlset>\n"
    assert parser.sitemap_locs(xml) == [TROUSERS, BRA]


def test_sitemap_that_is_not_xml_still_raises() -> None:
    with pytest.raises(ET.ParseError):
        parser.sitemap_locs("<html>Bakım</html")


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
