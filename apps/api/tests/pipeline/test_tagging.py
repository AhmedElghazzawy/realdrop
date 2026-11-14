"""product_attributes kept in step with the catalog: first tag, no-op re-runs, re-tag on change,
LLM rows respected, brand scope."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.collectors.base import RawProduct, RawVariant
from realdrop.models import Product, ProductAttributes
from realdrop.pipeline import store, tagging
from realdrop.pipeline.tagger import TAGGER_VERSION

T0 = datetime(2026, 11, 14, 9, 0, tzinfo=UTC)


def knit(title: str = "Tüylenme Yapmayan Yünlü Balıkçı Yaka Regular Fit Kazak") -> RawProduct:
    return RawProduct(
        external_id="k1",
        url="https://shop.example.com/kazak-k1",
        title=title,
        category_raw="Erkek > Triko",
        currency="TRY",
        variants=[
            RawVariant(external_sku="k1-M", price_minor=99_900, color_raw="Lacivert", in_stock=True)
        ],
    )


async def collect(session: AsyncSession, raw: RawProduct, slug: str = "shop") -> Product:
    brand = await store.get_or_create_brand(
        session, slug=slug, name=slug.title(), base_url=f"https://{slug}.example.com"
    )
    run = await store.start_run(session, brand.id)
    await store.store_product(session, brand_id=brand.id, run_id=run.id, raw=raw, observed_at=T0)
    return await session.scalar(select(Product).where(Product.brand_id == brand.id)) or Product()


async def attributes(session: AsyncSession, product: Product) -> ProductAttributes | None:
    return await session.get(ProductAttributes, product.id, populate_existing=True)


async def test_new_products_are_tagged_once(db_session: AsyncSession) -> None:
    product = await collect(db_session, knit())
    assert await tagging.refresh_attributes(db_session) == 1
    row = await attributes(db_session, product)
    assert row is not None
    assert row.colors == ["navy"]
    assert row.fit == "regular"
    assert row.material == ["wool"]
    assert row.subcategory == "turtleneck"
    assert {"old_money", "smart_casual"} <= set(row.style_tags)
    assert row.source == "rules"
    assert row.tagger_version == TAGGER_VERSION
    assert row.content_hash == product.content_hash
    assert await tagging.refresh_attributes(db_session) == 0  # nothing changed


async def test_a_changed_product_is_retagged(db_session: AsyncSession) -> None:
    product = await collect(db_session, knit())
    await tagging.refresh_attributes(db_session)
    await collect(db_session, knit("Oversize Baskılı Pamuklu Sweatshirt"))
    assert await tagging.refresh_attributes(db_session) == 1
    row = await attributes(db_session, product)
    assert row is not None and "streetwear" in row.style_tags


async def test_new_rules_retag_rule_rows_but_not_llm_rows(db_session: AsyncSession) -> None:
    product = await collect(db_session, knit())
    await tagging.refresh_attributes(db_session)
    await db_session.execute(
        update(ProductAttributes).values(tagger_version=TAGGER_VERSION - 1, source="llm")
    )
    assert await tagging.refresh_attributes(db_session) == 0  # the model's answer stays
    await db_session.execute(update(ProductAttributes).values(source="rules"))
    assert await tagging.refresh_attributes(db_session) == 1
    row = await attributes(db_session, product)
    assert row is not None and row.tagger_version == TAGGER_VERSION


async def test_retag_all_redoes_rule_rows(db_session: AsyncSession) -> None:
    await collect(db_session, knit())
    await tagging.refresh_attributes(db_session)
    assert await tagging.refresh_attributes(db_session, retag_all=True) == 1


async def test_brand_scope_and_batches(db_session: AsyncSession) -> None:
    mine = await collect(db_session, knit(), slug="mine")
    other = await collect(db_session, knit(), slug="other")
    assert await tagging.refresh_attributes(db_session, mine.brand_id, batch_size=1) == 1
    assert await attributes(db_session, other) is None
    assert await tagging.refresh_attributes(db_session, batch_size=1) == 1
    assert await attributes(db_session, other) is not None
