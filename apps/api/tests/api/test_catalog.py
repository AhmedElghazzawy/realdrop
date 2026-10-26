"""Read-only catalog endpoints against the test database, seeded through the real store pipeline."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.collectors.base import RawProduct, RawVariant
from realdrop.db.session import get_session
from realdrop.main import create_app
from realdrop.pipeline import rollup, store

T0 = datetime(2026, 10, 25, 0, 30, tzinfo=UTC)  # 03:30 in Istanbul
DAY = timedelta(days=1)


def product(
    external_id: str,
    title: str,
    price: int,
    original: int | None = None,
    category: str = "Kadın > Giyim",
) -> RawProduct:
    # As the DeFacto parser sets it: only an exact "Erkek"/"Kadın" category root counts.
    audience = {"Erkek": "men", "Kadın": "women"}.get(category.split(" > ")[0])
    return RawProduct(
        external_id=external_id,
        url=f"https://shop.example.com/p-{external_id}",
        title=title,
        image_urls=[f"https://img.example.com/{external_id}.jpg"],
        category_raw=category,
        audience=audience,
        currency="TRY",
        variants=[
            RawVariant(
                external_sku=f"{external_id}-{size}",
                size_label=size,
                price_minor=price,
                original_price_minor=original,
                in_stock=size != "L",
            )
            for size in ("S", "M", "L")
        ],
    )


async def seed(session: AsyncSession) -> None:
    brand = await store.get_or_create_brand(
        session, slug="shop", name="Shop", base_url="https://shop.example.com"
    )
    run = await store.start_run(session, brand.id)
    day1 = [
        (product("1", "Siyah Kaban", 200_000, 400_000), T0),
        (product("2", "Beyaz Gömlek", 50_000), T0),
        (product("3", "Erkek Mont", 300_000, category="Erkek > Giyim > Mont"), T0),
        (product("4", "Erkek Çocuk Mont", 90_000, category="Erkek Çocuk - Genç Erkek > Giyim"), T0),
    ]
    day2 = [
        (product("1", "Siyah Kaban", 180_000, 400_000), T0 + DAY),
        (product("2", "Beyaz Gömlek", 1_000), T0 + DAY),  # glitch: held as pending, never shown
    ]
    for batch in (day1, day2):
        await store.store_products(session, brand_id=brand.id, run_id=run.id, batch=batch)
    await rollup.refresh_daily(session, T0 - DAY)


async def get(session: AsyncSession, path: str) -> httpx.Response:
    app = create_app()

    async def override() -> AsyncIterator[Any]:
        yield session

    app.dependency_overrides[get_session] = override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def test_stats(db_session: AsyncSession) -> None:
    await seed(db_session)
    body = (await get(db_session, "/stats")).json()
    (brand,) = [b for b in body["brands"] if b["slug"] == "shop"]
    assert (brand["products"], brand["variants"], brand["observations"]) == (4, 12, 18)
    assert body["runs"][0]["brand_slug"] == "shop"


async def test_list_shows_confirmed_prices_only(db_session: AsyncSession) -> None:
    await seed(db_session)
    body = (await get(db_session, "/products?sort=price_asc&audience=women")).json()
    assert body["total"] == 2
    shirt, coat = body["items"]
    assert (shirt["title"], shirt["price_minor"]) == (
        "Beyaz Gömlek",
        50_000,
    )  # not the 1_000 glitch
    assert (coat["price_minor"], coat["original_price_minor"]) == (180_000, 400_000)
    assert (coat["sizes_in_stock"], coat["sizes_total"]) == (2, 3)
    assert coat["image_url"] == "https://img.example.com/1.jpg"


async def test_search_and_sort_by_claimed_discount(db_session: AsyncSession) -> None:
    await seed(db_session)
    found = (await get(db_session, "/products?q=kaban")).json()
    assert [p["title"] for p in found["items"]] == ["Siyah Kaban"]
    assert (await get(db_session, "/products?q=50%25")).json()["total"] == 0  # % is literal
    claimed = (await get(db_session, "/products?sort=claimed_discount")).json()
    assert claimed["items"][0]["title"] == "Siyah Kaban"


async def test_detail_has_sizes_and_daily_history(db_session: AsyncSession) -> None:
    await seed(db_session)
    coat_id = (await get(db_session, "/products?q=kaban")).json()["items"][0]["id"]
    body = (await get(db_session, f"/products/{coat_id}")).json()
    assert [(v["size_label"], v["in_stock"]) for v in body["variants"]] == [
        ("S", True),
        ("M", True),
        ("L", False),
    ]
    assert body["history"] == [
        {"day": "2026-10-25", "price_minor": 200_000, "original_price_minor": 400_000},
        {"day": "2026-10-26", "price_minor": 180_000, "original_price_minor": 400_000},
    ]


async def test_unknown_product_is_404(db_session: AsyncSession) -> None:
    response = await get(db_session, "/products/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_audience_men_excludes_boys(db_session: AsyncSession) -> None:
    await seed(db_session)
    body = (await get(db_session, "/products?audience=men")).json()
    assert [p["title"] for p in body["items"]] == ["Erkek Mont"]
    assert (await get(db_session, "/products")).json()["total"] == 4
    assert (await get(db_session, "/products?audience=kids")).status_code == 422


async def seed_second_brand(session: AsyncSession) -> None:
    brand = await store.get_or_create_brand(
        session, slug="other", name="Other", base_url="https://other.example.com"
    )
    run = await store.start_run(session, brand.id)
    jeans = product(
        "9", "Slim Fit Jean Pantolon", 120_000, 150_000, category="Erkek > Giyim > Jean"
    )
    await store.store_products(session, brand_id=brand.id, run_id=run.id, batch=[(jeans, T0)])


async def titles(session: AsyncSession, query: str) -> list[str]:
    body = (await get(session, f"/products?sort=price_asc&{query}")).json()
    return [p["title"] for p in body["items"]]


async def test_filters(db_session: AsyncSession) -> None:
    await seed(db_session)
    await seed_second_brand(db_session)
    assert await titles(db_session, "category=shirts") == ["Beyaz Gömlek"]
    assert await titles(db_session, "category=jackets&audience=men") == ["Erkek Mont"]
    assert await titles(db_session, "brand=other") == ["Slim Fit Jean Pantolon"]
    assert len(await titles(db_session, "brand=other&brand=shop")) == 5
    assert await titles(db_session, "on_sale=true") == ["Slim Fit Jean Pantolon", "Siyah Kaban"]
    assert await titles(db_session, "min_price=100000&max_price=200000") == [
        "Slim Fit Jean Pantolon",
        "Siyah Kaban",
    ]
    assert len(await titles(db_session, "in_stock=true")) == 5  # size L is the sold-out one
    assert (await get(db_session, "/products?min_price=-1")).status_code == 422


async def test_card_has_our_category_and_the_shops(db_session: AsyncSession) -> None:
    await seed(db_session)
    (card,) = (await get(db_session, "/products?audience=men")).json()["items"]
    assert (card["category"], card["category_raw"]) == ("jackets", "Erkek > Giyim > Mont")


async def test_facets_count_each_list_without_its_own_filter(db_session: AsyncSession) -> None:
    await seed(db_session)
    await seed_second_brand(db_session)
    body = (await get(db_session, "/products/facets?category=jackets&brand=shop")).json()
    assert body["total"] == 3
    categories = {c["key"]: c["count"] for c in body["categories"]}
    assert categories == {"jackets": 3, "shirts": 1}  # the brand filter still applies
    assert {b["slug"]: b["count"] for b in body["brands"]} == {"shop": 3}  # jackets only
    assert (body["min_price_minor"], body["max_price_minor"]) == (90_000, 300_000)
    jackets = next(c for c in body["categories"] if c["key"] == "jackets")
    assert jackets["image_url"].startswith("https://img.example.com/")


async def test_facets_without_filters_list_every_brand(db_session: AsyncSession) -> None:
    await seed(db_session)
    await seed_second_brand(db_session)
    body = (await get(db_session, "/products/facets?audience=men")).json()
    assert {b["slug"]: b["count"] for b in body["brands"]} == {"other": 1, "shop": 1}
    assert {c["key"] for c in body["categories"]} == {"jackets", "jeans"}
