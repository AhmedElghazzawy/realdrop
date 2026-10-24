# Roadmap: Sat 24 Oct -> Fri 27 Nov 2026

Assumes about 3-4 focused hours per day. If classes take that time, use the cut lines at the bottom;
do not silently slip dates. Update the checkboxes as work completes.

**The one thing that cannot slip:** price collection must run on a **server** from **Tue 27 Oct**.
History is the asset competitors cannot fake; every missing day is lost forever.

## Week 1: foundation and data (24-31 Oct)

- [ ] **Sat 24:** Phase 1 environment (`docs/SETUP.md`), kit committed, repo on GitHub, docs read once.
- [ ] **Sun 25:** Alembic setup + first migration (catalog, prices, runs). `/health`. `text.py` tests.
      Base collector interface + fixture-test pattern.
- [ ] **Mon 26:** Feasibility check for the first 3 brands (`docs/brands/<slug>.md`: robots, terms, feed or JSON,
      stability). Pick the easiest. Brand 1 collector against fixtures; dry run of 20 products.
- [ ] **Tue 27:** Brand 1 stored in DB with validation (glitch filter). Rent a VPS, deploy collection with a
      daily job. **Collection is now running without the laptop.**
- [ ] **Wed 28 - Thu 29:** Brands 2 and 3. `price_daily` roll-up, `current_prices`.
- [ ] **Fri 30 - Sat 31:** Brands 4-6 (as many as are feasible; 4 is fine). Collection health report
      (success rate per brand). Add `pricing/real_drop.py` with the full test suite (pure functions).

## Week 2: language and search (1-7 Nov)

- [ ] **Sun 1 - Mon 2:** Taxonomy + Turkish synonym maps. Extractor with Pydantic schema; label 60 products by hand.
- [ ] **Tue 3:** Run extractor on the catalog (dry-run cost estimate first); extractor eval baseline.
- [ ] **Wed 4 - Thu 5:** bge-m3 embeddings pipeline, pgvector HNSW index, full-text index. Hybrid search v1 (RRF).
- [ ] **Fri 6 - Sat 7:** Reranker. Retrieval judgments for 30 queries; baseline recall@10 and nDCG@10.

## Week 3: parser and product pages (8-14 Nov)

- [ ] **Sun 8 - Mon 9:** Query parser + golden queries (grow to 60+), parser eval baseline, fallback path.
- [ ] **Tue 10 - Wed 11:** Search API with filters + chips contract. Next.js scaffold, design tokens, fonts (Turkish glyph check).
- [ ] **Thu 12 - Fri 13:** Product page: price chart, real-discount badge, size picker. Search UI.
- [ ] **Sat 14:** **Checkpoint.** Is search good and are 14+ days of data in? If not, apply the cut lines.

## Week 4: alerts and assistant (15-21 Nov)

- [ ] **Sun 15 - Mon 16:** Users (email magic link or Telegram login), alerts model, alert evaluation + tests.
- [ ] **Tue 17:** Telegram bot notifications end to end. Raise collection frequency (every 4 h) for the 3 weeks before the sale.
- [ ] **Wed 18 - Thu 19:** Assistant tools + loop + number-grounding guard; assistant eval suite.
- [ ] **Fri 20 - Sat 21:** Assistant UI (streaming, tool chips). Prompt-injection and fabrication tests green.

## Week 5: personalization and launch (22-27 Nov)

- [ ] **Sun 22:** Signals, taste vector + counters, onboarding quiz, bounded re-ranking, "because..." labels.
- [ ] **Mon 23:** Black Friday page (real best deals, inflated-claim examples). KVKK pages: privacy notice, consent, delete-my-data.
- [ ] **Tue 24:** Load check, error pages, Sentry, backups verified (restore test), rate limits.
- [ ] **Wed 25:** Full eval run; fix the worst failures; freeze features.
- [ ] **Thu 26:** Soft launch to friends; watch logs, costs and alerts.
- [ ] **Fri 27:** Black Friday. Monitor collection every few hours. No risky deploys.

## Cut lines (apply in this order)

1. **Sat 14 Nov, behind:** drop email alerts and web push (Telegram only). Reduce brands to 4.
2. **Sat 21 Nov, behind:** assistant becomes non-streaming and answers only about one product at a time
   (`check_real_discount`, `get_price_history`); no `compare_products`.
3. **Sun 22 Nov, behind:** taste profile becomes counters only (no vector); keep onboarding.
4. **Never cut:** server-side collection, the real-drop tests, the number-grounding guard, KVKK basics, honest "tracking since" wording.

## After launch (not before)

Price forecasting once there are 3+ months of history; cross-brand matching; more brands and regions;
English UI; affiliate integration; Langfuse tracing; partitioning `price_observations` if needed.
