"""T-Soft parser and collector, on real product pages trimmed to the JSON-LD, the hidden price
inputs and the variant buttons (collectors/tsoft/fixtures). Sitemaps are built in the tests."""

from pathlib import Path

import httpx
import pytest

from realdrop.collectors.base import ItemFailure, RawProduct
from realdrop.collectors.http import CollectorBlockedError, PoliteClient
from realdrop.collectors.tsoft import parser
from realdrop.collectors.tsoft.brands import HatemogluCollector, LufianCollector

FIXTURES = Path(parser.__file__).parent / "fixtures"
URL = "https://www.lufian.com/river-erkek-kazak-vizon-8423"


def page(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


def sizes(product: RawProduct) -> list[tuple[str | None, bool]]:
    return [(v.size_label, v.in_stock) for v in product.variants]


def test_lufian_sold_out_sweater() -> None:
    product = parser.parse_product(page("lufian_men_sold_out"), URL)
    assert product.external_id == "8423"
    assert product.title == "Rıver Erkek Kazak Vizon"
    assert product.audience == "men"  # "Erkek > Üst Giyim > ..."
    assert product.category_raw == "Erkek > Üst Giyim > Erkek Kazak >Erkek Triko Kazak"
    assert product.currency == "TRY"
    # The colour button (Vizon) is not a size; 8 sizes, all sold out.
    assert [label for label, _ in sizes(product)] == [
        "XS",
        "S",
        "M",
        "L",
        "XL",
        "XXL",
        "3XL",
        "4XL",
    ]
    assert not any(v.in_stock for v in product.variants)
    assert {v.color_raw for v in product.variants} == {"Vizon"}
    # 2545.4455 without VAT + 10% = the page's 2.799,99.
    assert {(v.price_minor, v.original_price_minor) for v in product.variants} == {(279999, None)}
    assert len(product.image_urls) == 2


def test_tommylife_old_price_is_shown_with_vat() -> None:
    product = parser.parse_product(page("tommylife_men_discounted"), URL)
    assert product.audience == "men"  # "ERKEK > ÜST GİYİM > T-Shirt"
    # 477.18 + 10% = 524,90; the struck-through 1.069,21 is 972.01 + 10%.
    assert {(v.price_minor, v.original_price_minor) for v in product.variants} == {(52490, 106921)}
    assert sizes(product) == [
        ("S", False),
        ("M", False),
        ("L", True),
        ("XL", False),
        ("XXL", False),
    ]


def test_hatemoglu_ignores_the_basket_offer_in_json_ld() -> None:
    # JSON-LD says 559.93 (with "Sepette EKSTRA" off); the page's price is 799,90.
    product = parser.parse_product(page("hatemoglu_suit_basket_offer"), URL)
    assert {v.price_minor for v in product.variants} == {79990}
    assert {v.original_price_minor for v in product.variants} == {135000}
    assert [label for label, _ in sizes(product)] == ["48", "50", "52", "54", "56"]
    assert {v.color_raw for v in product.variants} == {"Lacivert"}  # no data-group-id here
    assert product.audience is None  # "Koleksiyon > ..."; the collector's default applies


def test_one_size_product() -> None:
    product = parser.parse_product(page("hatemoglu_one_size"), URL)
    assert sizes(product) == [("STD", True)]
    assert product.variants[0].price_minor == 59800


def test_a_page_whose_vat_does_not_add_up_is_rejected() -> None:
    html = page("tommylife_men_discounted").replace(
        'id="product-price-vat-include" value="524,90"',
        'id="product-price-vat-include" value="499,90"',
    )
    with pytest.raises(ValueError, match="VAT check failed"):
        parser.parse_product(html, URL)


@pytest.mark.parametrize(
    ("category", "audience"),
    [
        ("Erkek > Kazak", "men"),
        ("ERKEK > ÜST GİYİM", "men"),
        ("Kadın > Elbise", "women"),
        ("KADIN > Elbise", "women"),
        ("Erkek Çocuk > Tişört", None),
        ("Koleksiyon > Takı", None),
        (None, None),
    ],
)
def test_audience_from_category_root(category: str | None, audience: str | None) -> None:
    assert parser._audience(category) == audience


# --- collector ---------------------------------------------------------------------------------


def sitemap(urls: list[str]) -> str:
    locs = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    return f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{locs}</urlset>'


def site(base: str, pages: dict[str, str], gone: tuple[str, ...] = ()) -> httpx.MockTransport:
    """Every page and every `gone` path is in the sitemap; `gone` paths answer 404."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /uyelik-sozlesmesi\n")
        if path == "/xml/sitemap/product.xml":
            return httpx.Response(200, text=sitemap([f"{base}{p}" for p in [*pages, *gone]]))
        if path in pages:
            return httpx.Response(200, text=pages[path])
        return httpx.Response(404)

    return httpx.MockTransport(handler)


async def no_sleep(seconds: float) -> None:
    return None


async def collect(
    collector_class: type[LufianCollector] | type[HatemogluCollector],
    transport: httpx.MockTransport,
) -> list[RawProduct | ItemFailure]:
    client = PoliteClient(user_agent="realdrop-bot/test", transport=transport, sleep=no_sleep)
    async with client:
        return [item async for item in collector_class(client).fetch_catalog()]


async def test_men_only_and_failures() -> None:
    base = LufianCollector.base_url
    women = (
        page("tommylife_men_discounted")
        .replace("ERKEK &gt;", "KADIN &gt;")
        .replace("ERKEK >", "KADIN >")
    )
    pages = {
        "/sweater-8423": page("lufian_men_sold_out"),
        "/dress-1": women,
        "/broken-2": "<html>Bakımdayız</html>",
    }
    transport = site(base, pages, gone=("/gone-3",))
    results = await collect(LufianCollector, transport)
    assert [r.external_id for r in results if isinstance(r, RawProduct)] == ["8423"]
    failures = {r.source.rsplit("/", 1)[1]: r.reason for r in results if isinstance(r, ItemFailure)}
    assert failures == {"broken-2": "no product data", "gone-3": "HTTP 404"}


async def test_menswear_brand_gets_its_default_audience() -> None:
    base = HatemogluCollector.base_url
    results = await collect(
        HatemogluCollector, site(base, {"/suit": page("hatemoglu_suit_basket_offer")})
    )
    (product,) = results
    assert isinstance(product, RawProduct)
    assert product.audience == "men"


async def test_many_pages_without_data_stop_the_run() -> None:
    base = LufianCollector.base_url
    pages = {f"/p-{n}": "<html>Lütfen bekleyin</html>" for n in range(25)}
    with pytest.raises(CollectorBlockedError, match=r"2[01] product pages in a row"):
        await collect(LufianCollector, site(base, pages))
