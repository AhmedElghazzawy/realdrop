"""The LLM style pass: a local model re-judges the style of products the keyword rules tagged.

The rules (pipeline/tagger.py) read colours, fit and material well but style poorly: style F1 0.66
on the golden set. The model (ai/style_tagger.py) scores 0.84 when it judges every product, but
only 0.71 when it only fills the products the rules left without a style (`make eval
TAGGER=hybrid`, 19 Nov): most rule errors are wrong tags, not missing ones. So `--all` asks the
model for every rule row, the style-less ones first (owner decision, 19 Nov).

The pass is resumable: it only picks rows that are still `source = 'rules'` with no style and
commits every batch, so stopping it (Ctrl-C) loses at most one batch. A row the model answered
becomes `source = 'llm'` (even with an empty answer, so it is not asked again); when the product
itself changes, pipeline/tagging.py re-tags it with the rules and it becomes a candidate again.

    uv run python -m realdrop.pipeline.llm_styles --all --dry-run   # count and time estimate
    uv run python -m realdrop.pipeline.llm_styles --all [--limit N] # run (Ollama must be up)
    uv run python -m realdrop.pipeline.llm_styles                   # style-less rows only
"""

import argparse
import asyncio
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from realdrop.ai.llm import LLMClient, LLMError
from realdrop.ai.style_tagger import STYLE_TAGGER_VERSION, tag_styles
from realdrop.db.session import get_sessionmaker
from realdrop.models import Brand, Product, ProductAttributes
from realdrop.pipeline.tagger import Attributes

BATCH_SIZE = 50
CONCURRENCY = 2  # Ollama on a laptop serves about one request at a time; 2 keeps it busy
SECONDS_PER_PRODUCT = 2.75  # gemma4:12b, thinking off, M2 16 GB (16 Nov eval)


@dataclass(frozen=True)
class Candidate:
    product_id: uuid.UUID
    content_hash: str
    title: str
    category_raw: str | None
    category: str | None
    brand: str
    rules: Attributes


def _pending(styled: bool = False) -> Any:
    """Rule rows the model has not judged: without a style, or (styled=True) with one."""
    pa = ProductAttributes
    return and_(
        pa.source == "rules",
        pa.style_tags != [] if styled else pa.style_tags == [],
        pa.content_hash == Product.content_hash,  # stale rows wait for the rules first
    )


def _candidates(after: uuid.UUID | None, limit: int, styled: bool) -> Select[Any]:
    pa = ProductAttributes
    stmt: Any = (  # 11 columns: past the typed overloads of select()
        select(
            Product.id,
            Product.content_hash,
            Product.title_raw,
            Product.category_raw,
            Product.category,
            Brand.name,
            pa.subcategory,
            pa.colors,
            pa.fit,
            pa.material,
            pa.pattern,
        )
        .join(pa, pa.product_id == Product.id)
        .join(Brand, Brand.id == Product.brand_id)
        .where(_pending(styled))
        .order_by(Product.id)
        .limit(limit)
    )
    if after is not None:
        stmt = stmt.where(Product.id > after)
    return stmt


async def count_pending(session: AsyncSession, styled: bool = False) -> int:
    stmt = (
        select(func.count())
        .select_from(ProductAttributes)
        .join(Product, Product.id == ProductAttributes.product_id)
        .where(_pending(styled))
    )
    return int(await session.scalar(stmt) or 0)


async def next_batch(
    session: AsyncSession, after: uuid.UUID | None, limit: int = BATCH_SIZE, styled: bool = False
) -> list[Candidate]:
    rows = (await session.execute(_candidates(after, limit, styled))).all()
    return [
        Candidate(
            product_id=r[0],
            content_hash=r[1],
            title=r[2],
            category_raw=r[3],
            category=r[4],
            brand=r[5],
            rules=Attributes(
                subcategory=r[6],
                colors=tuple(r[7] or ()),
                fit=r[8],
                material=tuple(r[9] or ()),
                pattern=r[10],
            ),
        )
        for r in rows
    ]


async def ask_model(
    client: LLMClient, batch: Sequence[Candidate], concurrency: int = CONCURRENCY
) -> dict[uuid.UUID, tuple[str, ...]]:
    """Style tags per product. A product the model fails on is left out (retried next run)."""
    semaphore = asyncio.Semaphore(concurrency)
    answers: dict[uuid.UUID, tuple[str, ...]] = {}

    async def one(c: Candidate) -> None:
        async with semaphore:
            try:
                result = await tag_styles(
                    client,
                    title=c.title,
                    category_raw=c.category_raw,
                    category=c.category,
                    brand=c.brand,
                    rules=c.rules,
                )
            except (LLMError, ValueError, KeyError) as error:
                print(f"  skipped {c.product_id}: {str(error)[:120]}")
                return
        answers[c.product_id] = result.style_tags

    await asyncio.gather(*(one(c) for c in batch))
    return answers


async def save(
    session: AsyncSession,
    batch: Sequence[Candidate],
    answers: dict[uuid.UUID, tuple[str, ...]],
    model: str,
) -> int:
    """Store the answers. A row the rules re-tagged meanwhile (product changed) is left alone."""
    pa = ProductAttributes
    written = 0
    for c in batch:
        if c.product_id not in answers:
            continue
        result = await session.execute(
            update(pa)
            .where(
                pa.product_id == c.product_id,
                pa.source == "rules",
                pa.content_hash == c.content_hash,
            )
            .values(
                style_tags=list(answers[c.product_id]),
                source="llm",
                tagger_version=STYLE_TAGGER_VERSION,
                evidence=pa.evidence.op("||")(
                    func.jsonb_build_object("style_tags", "llm", "model", model)
                ),
                tagged_at=func.now(),
            )
        )
        written += int(getattr(result, "rowcount", 0) or 0)
    return written


async def _main(limit: int | None, dry_run: bool, model: str | None, everything: bool) -> None:
    sessionmaker = get_sessionmaker()
    passes = (False, True) if everything else (False,)  # style-less rows first
    async with sessionmaker() as session:
        pending = [await count_pending(session, styled) for styled in passes]
    todo = min(sum(pending), limit) if limit else sum(pending)
    hours = todo * SECONDS_PER_PRODUCT / 3600
    styled_note = f", {pending[1]} with one" if everything else ""
    print(f"pending: {pending[0]} without a style{styled_note}")
    print(f"this run: {todo} products (~{hours:.1f} h)")
    if dry_run or not todo:
        return

    started = time.monotonic()
    done = tagged = 0
    async with LLMClient(model=model) as client:
        for styled in passes:
            after: uuid.UUID | None = None
            while done < todo:
                # Short sessions: no database connection stays open while the model thinks.
                async with sessionmaker() as session:
                    batch = await next_batch(session, after, min(BATCH_SIZE, todo - done), styled)
                if not batch:
                    break
                answers = await ask_model(client, batch)
                async with sessionmaker() as session, session.begin():
                    await save(session, batch, answers, client.model)
                after = batch[-1].product_id
                done += len(batch)
                tagged += sum(1 for tags in answers.values() if tags)
                rate = (time.monotonic() - started) / done
                left = (todo - done) * rate / 3600
                print(f"{done}/{todo} done, {tagged} styled, {rate:.1f} s each, ~{left:.1f} h left")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Style tags by the LLM for rule-tagged products.")
    parser.add_argument("--all", action="store_true", help="also re-judge rows the rules styled")
    parser.add_argument("--limit", type=int, help="stop after this many products")
    parser.add_argument("--dry-run", action="store_true", help="only count and estimate")
    parser.add_argument("--model", help="Ollama model (default: LLM_MODEL_FAST)")
    args = parser.parse_args()
    asyncio.run(_main(args.limit, args.dry_run, args.model, args.all))
