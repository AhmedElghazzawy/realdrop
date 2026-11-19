"""The LLM style pass: only style-less rule rows, resumable, never overwrites a changed product."""

import json
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.ai.llm import LLMClient
from realdrop.ai.style_tagger import STYLE_TAGGER_VERSION
from realdrop.collectors.base import RawProduct, RawVariant
from realdrop.models import Product, ProductAttributes
from realdrop.pipeline import llm_styles, store, tagging

T0 = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


def knit() -> RawProduct:
    """A product the rules give a style (old money)."""
    return RawProduct(
        external_id="k1",
        url="https://shop.example.com/kazak-k1",
        title="Tüylenme Yapmayan Yünlü Balıkçı Yaka Regular Fit Kazak",
        category_raw="Erkek > Triko",
        currency="TRY",
        variants=[
            RawVariant(external_sku="k1-M", price_minor=99_900, color_raw="Lacivert", in_stock=True)
        ],
    )


def plain(external_id: str = "s1") -> RawProduct:
    """A product the rules give no style (plain socks)."""
    return RawProduct(
        external_id=external_id,
        url=f"https://shop.example.com/{external_id}",
        title="Pamuklu Çorap",
        category_raw="Erkek > Çorap",
        currency="TRY",
        variants=[RawVariant(external_sku=f"{external_id}-1", price_minor=9_900, in_stock=True)],
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


def model(answers: list[str] | str) -> tuple[LLMClient, list[dict[str, Any]]]:
    queue = [answers] if isinstance(answers, str) else list(answers)
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        content = queue.pop(0) if len(queue) > 1 else queue[0]
        if content == "ERROR":
            return httpx.Response(500, text="boom")
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = LLMClient(
        base_url="http://llm.test/v1", model="m", transport=httpx.MockTransport(handler)
    )
    return client, seen


async def test_only_rule_rows_without_a_style_are_candidates(db_session: AsyncSession) -> None:
    await collect(db_session, knit())  # the rules find old money: not a candidate
    socks = await collect(db_session, plain(), slug="socks")
    await tagging.refresh_attributes(db_session)
    assert await llm_styles.count_pending(db_session) == 1
    batch = await llm_styles.next_batch(db_session, None)
    assert [c.product_id for c in batch] == [socks.id]
    assert batch[0].brand == "Socks"


async def test_styled_rule_rows_are_the_second_pass(db_session: AsyncSession) -> None:
    knitwear = await collect(db_session, knit())
    await collect(db_session, plain(), slug="socks")
    await tagging.refresh_attributes(db_session)
    assert await llm_styles.count_pending(db_session, styled=True) == 1
    batch = await llm_styles.next_batch(db_session, None, styled=True)
    assert [c.product_id for c in batch] == [knitwear.id]
    assert await llm_styles.save(db_session, batch, {knitwear.id: ("classic_tailoring",)}, "m") == 1
    row = await attributes(db_session, knitwear)
    assert row is not None and row.style_tags == ["classic_tailoring"]  # the model's call wins
    assert await llm_styles.count_pending(db_session, styled=True) == 0


async def test_answers_are_stored_as_llm_rows_and_not_asked_again(
    db_session: AsyncSession,
) -> None:
    product = await collect(db_session, plain())
    await tagging.refresh_attributes(db_session)
    batch = await llm_styles.next_batch(db_session, None)
    client, seen = model('{"style_tags": ["minimal", "not_a_style"]}')
    async with client:
        answers = await llm_styles.ask_model(client, batch)
    assert await llm_styles.save(db_session, batch, answers, "m") == 1
    row = await attributes(db_session, product)
    assert row is not None
    assert row.style_tags == ["minimal"]
    assert row.source == "llm"
    assert row.tagger_version == STYLE_TAGGER_VERSION
    assert row.evidence["style_tags"] == "llm" and row.evidence["model"] == "m"
    assert "Pamuklu" in seen[0]["messages"][1]["content"]
    assert await llm_styles.count_pending(db_session) == 0


async def test_an_empty_answer_is_kept_so_the_product_is_not_retried(
    db_session: AsyncSession,
) -> None:
    await collect(db_session, plain())
    await tagging.refresh_attributes(db_session)
    batch = await llm_styles.next_batch(db_session, None)
    client, _ = model('{"style_tags": []}')
    async with client:
        answers = await llm_styles.ask_model(client, batch)
    assert await llm_styles.save(db_session, batch, answers, "m") == 1
    assert await llm_styles.count_pending(db_session) == 0


async def test_a_failed_call_skips_only_that_product(db_session: AsyncSession) -> None:
    await collect(db_session, plain("a"), slug="a")
    await collect(db_session, plain("b"), slug="b")
    await tagging.refresh_attributes(db_session)
    batch = await llm_styles.next_batch(db_session, None)
    client, _ = model(["ERROR", '{"style_tags": ["minimal"]}'])
    async with client:
        answers = await llm_styles.ask_model(client, batch, concurrency=1)
    assert len(answers) == 1
    assert await llm_styles.save(db_session, batch, answers, "m") == 1
    assert await llm_styles.count_pending(db_session) == 1  # the failed one waits for next run


async def test_a_product_that_changed_meanwhile_is_not_overwritten(
    db_session: AsyncSession,
) -> None:
    product = await collect(db_session, plain())
    await tagging.refresh_attributes(db_session)
    batch = await llm_styles.next_batch(db_session, None)
    await db_session.execute(update(ProductAttributes).values(content_hash="changed"))
    assert await llm_styles.save(db_session, batch, {product.id: ("minimal",)}, "m") == 0
    row = await attributes(db_session, product)
    assert row is not None and row.source == "rules"


async def test_batches_resume_after_the_cursor(db_session: AsyncSession) -> None:
    for slug in ("a", "b", "c"):
        await collect(db_session, plain(slug), slug=slug)
    await tagging.refresh_attributes(db_session)
    first = await llm_styles.next_batch(db_session, None, limit=2)
    rest = await llm_styles.next_batch(db_session, first[-1].product_id, limit=2)
    assert len(first) == 2 and len(rest) == 1
    assert rest[0].product_id not in {c.product_id for c in first}
