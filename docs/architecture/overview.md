# Architecture

## Components

```
                         +-------------------+
   retailer feeds/APIs ->|    Collectors     |  httpx + selectolax (Playwright last resort)
                         +---------+---------+
                                   | RawProduct (Pydantic)
                         +---------v---------+
                         |  Validate / glitch|  pipeline/validate.py
                         +---------+---------+
                                   | confirmed observations
   +----------------+    +---------v---------+    +-------------------+
   |  Redis + Arq   |<-->|   PostgreSQL 16   |<-->|   FastAPI (API)   |<--> Next.js web
   |  job queue     |    |  + pgvector       |    +----+---------+----+
   +-------+--------+    |  products,        |         |         |
           |             |  variants, prices,|    search/    assistant/
           |             |  embeddings,      |    hybrid     loop + tools
           |             |  users, signals,  |         |         |
           |             |  alerts           |    LLM (free/open)  Embeddings + reranker
           |             +---------+---------+    (parser, extractor, assistant)  (bge-m3, bge-reranker)
           |                       |
           +---> extract -> embed -> alerts evaluate -> notify (Telegram, email, push)
```

## Data flow (one cycle)

1. **Collect** (`jobs/schedule.py`): per brand, staggered, at a polite rate. Output: `RawProduct` with
   variants (size, color, price, original price, stock). Raw payload hash is stored for debugging.
2. **Validate** (`pipeline/validate.py`): reject impossible prices; hold suspicious jumps as `pending`
   until a second observation confirms them (rules in `DATA_MODEL.md`).
3. **Store** (`pipeline/store.py`): upsert products and variants, append `price_observations`,
   roll up `price_daily`, refresh `current_prices`.
4. **Extract** (`ai/extractor.py`): only for new or changed products (content hash); structured attributes.
5. **Embed** (`ai/embeddings.py`): only when the embedding text changed.
6. **Evaluate alerts** (`alerts/evaluate.py`): for each newly confirmed price, check active alerts.
7. **Serve**: search (parser -> filters + hybrid retrieval -> rerank -> personalize), product pages,
   assistant (tool loop over the same services).

## Key decisions (short ADRs; add new ones at the bottom)

| # | Decision | Why |
|---|---|---|
| 1 | One Postgres for relational data, full-text search and vectors (pgvector) | Fewer moving parts for a 5-week build; hybrid search in one SQL query path |
| 2 | Arq + Redis for jobs, not Celery | Async-native, tiny, enough for scheduled collection and fan-out |
| 3 | OpenAI-compatible client with a hand-written tool loop, no agent framework | The owner must learn the loop; fewer hidden behaviours; easier to test; one client works with Ollama and every free API tier |
| 4 | Discounts computed in code, LLM only explains | Trust is the product. LLMs must never be the source of a price |
| 5 | Self-hosted bge-m3 + reranker | Good Turkish quality, no per-query cost; CPU is acceptable at launch scale |
| 6 | Append-only `price_observations`, derived `price_daily` | Glitch confirmation needs raw observations; history stays auditable |
| 7 | Integer kurus for money | No float errors; comparisons and medians stay exact |
| 8 | Collection runs on a server by Oct 27 at the latest (end of roadmap Phase 3) | A sleeping laptop would create gaps in the history, which is our main asset |
| 9 | Taste profile is plain code (decayed vector + counters) | Explainable, cheap, deletable, testable. No LLM needed |
| 10 | Next.js frontend, English default + Turkish (`/en`, `/tr`) | Fast mobile UX, strong ecosystem, easy deploy |
| 11 | Free LLMs only: Ollama locally, free API tiers in prod, switchable via env (24 Oct 2026) | Zero budget. Providers are swapped in `.env`, not code; evals decide which model is good enough |
| 12 | Hosting on no-card free tiers: Neon (DB), GitHub Actions (collection), Render/Vercel later (24 Oct 2026) | Owner gives no card to any provider (Oracle dropped). Revisit if Neon's 0.5 GB or GitHub's 6 h job limit is hit |

## Scaling assumptions (launch)

6 brands x ~3,000 tracked products x ~6 variants ~= 100k variants. One observation per variant per run;
every 4 hours near Black Friday ~= 600k rows/day at most. **Neon's free 0.5 GB cannot hold that**
(~160 bytes/row with indexes): one brand daily (~45k rows, ~7 MB/day) fits until launch, more brands or
4-hourly runs need change-only observations (a data-model decision for Phase 4). Partition `price_observations` by month only
if needed after launch. The assistant is the per-user load on free-tier rate limits: daily caps per user (see `AI_DESIGN.md`).

## Environments

- **dev**: Docker Compose (Postgres+pgvector, Redis) on the Mac; API and web run natively.
- **prod**: free tiers that need no credit card (ADR 12). Database: **Neon** free Postgres (0.5 GB,
  pgvector). Collection: **GitHub Actions** scheduled workflow (`.github/workflows/collect.yml`, free and
  unlimited for a public repo). Later: API on **Render** free, web on **Vercel** free. Sentry free for
  errors. Nothing paid without the owner's explicit OK. Setup: `docs/DEPLOY.md`.

## Failure behaviour

- LLM down: search falls back to pure semantic/keyword; assistant shows a clear unavailable message.
- Brand collection fails: keep serving last data, mark `as_of` honestly in the UI, alert the owner.
- Embedding model slow: serve results without rerank (flag in response), never block the page.

## Decision log

(Append new ADRs here with date, decision, reason, and what would make us revisit it.)
