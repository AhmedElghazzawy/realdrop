# RealDrop

**Honest prices for Turkish fashion.** An AI shopping-intelligence web app that records real prices
every day, tells you what a discount **really** is, alerts you when your size really drops, and lets
you search in plain Turkish or English.

![Status](https://img.shields.io/badge/status-in%20development-orange)
![Launch](https://img.shields.io/badge/launch-Black%20Friday%2027%20Nov%202026-black)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?logo=nextdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/Postgres%2016-pgvector-4169E1?logo=postgresql&logoColor=white)
![Open models](https://img.shields.io/badge/AI-open%20models%20(Ollama)-black?logo=ollama&logoColor=white)

> **Built in public, in 5 weeks.** Started 24 Oct 2026, launching on Black Friday, 27 Nov 2026.
> Follow the commits and the [roadmap](docs/ROADMAP.md) to watch it come together.

## Progress

| Phase | Focus | Status |
|---|---|---|
| 1 | Environment, free/open-source models | ✅ Done |
| 2 | Backend foundation: database schema, `/health`, collector base | ✅ Done |
| 3 | First brand collecting daily on a server | 🟡 Next |
| 4 | More brands, price roll-ups, real-drop rule | ⚪ Planned |
| 5 | Taxonomy and AI extractor | ⚪ Planned |
| 6 | Hybrid search: embeddings, full-text, reranker | ⚪ Planned |
| 7 | Query parser and search API | ⚪ Planned |
| 8 | Web app: search UI, product pages | ⚪ Planned |
| 9 | Users and Telegram alerts | ⚪ Planned |
| 10 | Shopping assistant + grounding guard | ⚪ Planned |
| 11 | Personalization | ⚪ Planned |
| 12 | Black Friday page, KVKK, hardening, launch | ⚪ Planned |

## Why

On Black Friday Turkish shoppers see "70% off!" everywhere, and many of those discounts are inflated:
the "original" price was raised just before the sale. Existing price trackers focus on electronics and
ignore what matters in fashion: size, color and stock. RealDrop fixes that with data it collects
itself.

## Features (launch scope)

| | Feature |
|---|---|
| Must | Daily (later every-few-hours) price collection from 5-6 Turkish brands, running on a server |
| Must | Product pages: price chart, size/stock, **real-discount badge**, link out to the retailer |
| Must | Search: Turkish/English query parser + hybrid retrieval (full-text + vectors) + rerank |
| Must | Telegram alerts per size (target price or minimum real discount) |
| Must | Black Friday page: real best deals and inflated-claim examples |
| Must | KVKK basics: privacy notice, consent, delete-my-data |
| Should | Shopping assistant with tools and a **number-grounding guard** |
| Should | Taste profile and "for you" ordering |

Full scope, users and non-goals: [`docs/PRODUCT.md`](docs/PRODUCT.md).

## Core principles

1. **The AI never invents prices.** Discounts are computed in code from stored history
   (`pricing/`). LLMs only call tools and explain the numbers those tools return.
2. **Every AI feature ships with evals.** No eval, not done ([`docs/EVALS.md`](docs/EVALS.md)).
3. **Honest about limits.** Claims say "based on prices we observed since <date>"; a variant with
   under 14 days of data gets no real-discount claim.
4. **Polite collection.** Respect robots.txt and terms, identify ourselves, rate-limit, prefer feeds
   and JSON endpoints, never scrape behind a login, collect no personal data.

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic, Arq + Redis
- **Data:** PostgreSQL 16 + pgvector (relational, full-text and vectors in one database)
- **AI:** free and open-source models (Ollama locally, free API tiers in prod) with a hand-written tool loop (no agent frameworks), bge-m3 embeddings,
  bge-reranker
- **Frontend:** Next.js (App Router), TypeScript, Tailwind, shadcn/ui; English default, Turkish second
- **Ops:** no-card free tiers: Neon (Postgres), GitHub Actions (daily collection), Render + Vercel later, Sentry free

```
retailer feeds -> collectors -> validate (glitch filter) -> Postgres + pgvector -> FastAPI -> Next.js
                                                   \-> extract -> embed -> alerts -> Telegram
```

Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Repository layout

```
apps/api/      FastAPI backend (package: realdrop)
apps/web/      Next.js frontend (English + Turkish)
docs/          product, architecture, data model, AI design, evals, design system, setup, roadmap
evals/         golden sets for the AI components
infra/         database init scripts
.claude/       Claude Code agents, skills, hooks and settings
CLAUDE.md      project rules and memory for Claude Code
```

## Documentation

| Doc | What's in it |
|---|---|
| [PRODUCT](docs/PRODUCT.md) | Problem, users, scope, non-goals, launch targets, legal notes |
| [ROADMAP](docs/ROADMAP.md) | Phase-by-phase plan to 27 Nov, deadlines and cut lines |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Components, data flow, decision log (ADRs) |
| [DATA_MODEL](docs/DATA_MODEL.md) | Tables, the real-drop rule, glitch filter, alert rule |
| [AI_DESIGN](docs/AI_DESIGN.md) | Extractor, query parser, assistant loop, taste profile |
| [EVALS](docs/EVALS.md) | Quality gates and golden sets |
| [DESIGN_SYSTEM](docs/DESIGN_SYSTEM.md) | UI tokens and components |
| [SETUP](docs/SETUP.md) | Local machine setup (macOS) |

## Getting started (local dev)

Requires Docker (OrbStack), `uv`, Node and `pnpm`. See [`docs/SETUP.md`](docs/SETUP.md).

```bash
cp .env.example .env            # then add your own keys; never commit .env
docker compose up -d            # Postgres (pgvector) + Redis

cd apps/api && uv sync && uv run uvicorn realdrop.main:app --reload   # http://localhost:8000/docs
cd apps/web && pnpm install && pnpm dev                            # http://localhost:3000
```

## Built with Claude Code

This repo is built together with [Claude Code](https://claude.com/claude-code). `CLAUDE.md` and
`.claude/` hold the rules, specialist agents (architect, reviewer, collector, search/ML, frontend)
and step-by-step skills it follows.

## Author

**Ahmed Elghazzawy** ([@AhmedElghazzawy](https://github.com/AhmedElghazzawy)), a computer-engineering
student building this to learn and ship. Focus: AI engineering (structured extraction, hybrid search,
tool-calling agents, evals).

## License

Copyright © 2026 Ahmed Elghazzawy. All rights reserved. The source is public to view and learn from;
no license is granted to reuse it yet.

Price data shown by the app belongs to the respective retailers; brand names are their owners'
trademarks. RealDrop is not affiliated with any retailer.
