---
name: add-migration
description: Checklist for changing the database schema safely with SQLAlchemy models and Alembic, including pgvector columns and indexes. Use for any table, column, index or constraint change.
---

# Add a migration

**[ASK]** before any data-model change that is not already described in `docs/DATA_MODEL.md`.

1. **Model first.** Edit or add the SQLAlchemy model in `src/realdrop/models/`. Money columns are
   `Integer`/`BigInteger` (kurus); timestamps are `DateTime(timezone=True)`; vectors use
   `from pgvector.sqlalchemy import Vector` with dimension 1024.
2. **Generate:** `cd apps/api && uv run alembic revision --autogenerate -m "short_snake_case_message"`.
3. **Review the generated file by hand.** Autogenerate misses or mangles things. Check:
   - `import pgvector.sqlalchemy` is present when `Vector` is used.
   - Indexes you intended exist: GIN for `tsvector`, `USING hnsw (embedding vector_cosine_ops)` for
     embeddings (write with `op.execute` if needed), plain btree for lookups.
   - `ondelete` behaviour is deliberate (cascade for owned rows, restrict for catalog rows).
   - New NOT NULL columns on tables with data have a `server_default` or a backfill step.
   - No accidental drop of columns or tables.
4. **Test upgrade and downgrade** on the local database:
   `uv run alembic upgrade head`, then `uv run alembic downgrade -1`, then `uv run alembic upgrade head`.
5. **Test the model:** add or update a test that inserts and reads the new structure.
6. **Update docs:** `docs/DATA_MODEL.md` must match the schema exactly.
7. **Run:** `uv run pytest`, `uv run ruff check .`, `uv run mypy src`.
8. **Commit:** `feat(db): <what and why>`. Migrations are never edited after they are merged; add a new one.
9. Tell the owner in 2-4 sentences why the schema looks this way and what the migration does.
