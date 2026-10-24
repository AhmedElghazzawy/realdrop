# Roadmap: phases to Black Friday (Fri 27 Nov 2026)

Work goes by **phases, not days**. Start the next phase as soon as the current one is done; finishing
several in one day is fine. Update the checkboxes and the README progress table as work completes.

Each phase has a **latest finish** date. Being ahead is the goal; passing a latest-finish date with the
phase still open is the signal to apply the cut lines at the bottom. Do not silently slip.

**The one thing that cannot slip:** price collection must run on a **server** as early as possible,
**27 Oct at the latest** (end of Phase 3). History is the asset competitors cannot fake; every missing
day is lost forever, and the real-drop rule needs 14+ days of history before it can make any claim.

## Phase 1: environment ✅

Latest finish: 24 Oct.

- [x] Environment from `docs/SETUP.md` (tools, apps scaffolded, Postgres + Redis, Ollama), kit committed,
      repo on GitHub.
- [x] Switch to free and open-source models only (ADR 11).
- [ ] Owner reads `docs/PRODUCT.md`, `docs/ROADMAP.md`, `docs/AI_DESIGN.md` once.

## Phase 2: backend foundation ✅

Latest finish: 25 Oct. Done 24 Oct.

- [x] Settings, async DB session, app factory. `/health`. (`text.py` tests: done in Phase 1.)
- [x] Alembic setup + first migration (catalog, prices, runs).
- [x] Base collector interface, polite HTTP client, price parsing + fixture-test pattern.

## Phase 3: first brand collecting on a server

Latest finish: 27 Oct.

- [x] Feasibility check for the first 3 brands (`docs/brands/<slug>.md`: robots, terms, feed or JSON,
      stability). Pick the easiest. (Six checked; DeFacto is brand 1.)
- [x] Brand 1 collector against fixtures; dry run of 20 products.
- [x] Brand 1 stored in DB with validation (glitch filter).
- [ ] Set up the free server (Oracle Cloud Always Free; paid VPS only with the owner's OK), deploy
      collection with a daily job. **Collection is now running without the laptop.**

## Phase 4: more brands and the real-drop rule

Latest finish: 31 Oct.

- [ ] Brands 2 and 3. `price_daily` roll-up, `current_prices`.
- [ ] Brands 4-6 (as many as are feasible; 4 is fine). Collection health report (success rate per brand).
- [ ] `pricing/real_drop.py` with the full test suite (pure functions).

## Phase 5: taxonomy and extractor

Latest finish: 3 Nov.

- [ ] Taxonomy + Turkish synonym maps. Extractor with Pydantic schema; label 60 products by hand.
- [ ] Run extractor on the catalog with local Ollama (dry-run time estimate first; run overnight);
      extractor eval baseline.

## Phase 6: hybrid search

Latest finish: 7 Nov.

- [ ] bge-m3 embeddings pipeline, pgvector HNSW index, full-text index. Hybrid search v1 (RRF).
- [ ] Reranker. Retrieval judgments for 30 queries; baseline recall@10 and nDCG@10.

## Phase 7: query parser and search API

Latest finish: 11 Nov.

- [ ] Query parser + golden queries (grow to 60+), parser eval baseline, fallback path.
- [ ] Pick the free API tier for prod (parser and assistant) by comparing candidates on the evals.
- [ ] Search API with filters + chips contract.

## Phase 8: web app

Latest finish: 14 Nov.

- [ ] Design tokens, fonts (Turkish glyph check) on the existing Next.js scaffold.
- [ ] Product page: price chart, real-discount badge, size picker. Search UI.
- [ ] **Checkpoint.** Is search good and are 14+ days of data in? If not, apply the cut lines.

## Phase 9: users and alerts

Latest finish: 17 Nov.

- [ ] Users (email magic link or Telegram login), alerts model, alert evaluation + tests.
- [ ] Telegram bot notifications end to end.
- [ ] Raise collection frequency to every 4 h for the run-up to the sale (by 17 Nov at the latest,
      whatever phase we are in).

## Phase 10: shopping assistant

Latest finish: 21 Nov.

- [ ] Assistant tools + loop + number-grounding guard; assistant eval suite.
- [ ] Assistant UI (streaming, tool chips). Prompt-injection and fabrication tests green.

## Phase 11: personalization

Latest finish: 22 Nov.

- [ ] Signals, taste vector + counters, onboarding quiz, bounded re-ranking, "because..." labels.

## Phase 12: launch

Latest finish: 27 Nov. The last three steps are tied to fixed dates.

- [ ] Black Friday page (real best deals, inflated-claim examples). KVKK pages: privacy notice, consent,
      delete-my-data.
- [ ] Load check, error pages, Sentry, backups verified (restore test), rate limits.
- [ ] Full eval run; fix the worst failures; **freeze features (25 Nov)**.
- [ ] **Soft launch to friends (26 Nov)**; watch logs, free-tier rate limits and alerts.
- [ ] **Black Friday (27 Nov).** Monitor collection every few hours. No risky deploys.

## Cut lines (apply in this order)

1. **Phase 8 still open on 14 Nov:** drop email alerts and web push (Telegram only). Reduce brands to 4.
2. **Phase 10 still open on 21 Nov:** assistant becomes non-streaming and answers only about one product
   at a time (`check_real_discount`, `get_price_history`); no `compare_products`.
3. **Phase 11 not started by 22 Nov:** taste profile becomes counters only (no vector); keep onboarding.
4. **Never cut:** server-side collection, the real-drop tests, the number-grounding guard, KVKK basics,
   honest "tracking since" wording.

## After launch (not before)

Price forecasting once there are 3+ months of history; cross-brand matching; more brands and regions;
English UI; affiliate integration; Langfuse tracing; partitioning `price_observations` if needed.
