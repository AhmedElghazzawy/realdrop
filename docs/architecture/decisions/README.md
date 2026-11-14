# Architecture decision records

One file per decision, numbered, never renumbered. A changed decision gets a new ADR that
supersedes the old one; the old file stays with its status updated. Template: [`template.md`](template.md).

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-single-postgres-with-pgvector.md) | One Postgres for relational data, full-text search and vectors | Accepted |
| [0002](0002-job-queue.md) | Arq + Redis for background jobs | Superseded by 0012 (2026-11-14) |
| [0003](0003-hand-written-llm-tool-loop.md) | OpenAI-compatible client with a hand-written tool loop, no agent framework | Accepted |
| [0004](0004-code-computes-prices.md) | Discounts are computed in code; the LLM only explains | Accepted |
| [0005](0005-self-hosted-embeddings.md) | Self-hosted bge-m3 embeddings and reranker | Accepted |
| [0006](0006-append-only-observations.md) | Change-only price observations with a derived daily table | Accepted (amended 2026-10-25) |
| [0007](0007-integer-minor-units.md) | Money as integer minor units | Accepted |
| [0008](0008-server-side-collection-early.md) | Collection on a server from day 4 | Accepted |
| [0009](0009-taste-profile-in-code.md) | Taste profile is plain code | Accepted (amended by 0014) |
| [0010](0010-nextjs-bilingual.md) | Next.js frontend, English default and Turkish | Accepted |
| [0011](0011-free-models-only.md) | Free and open-source models only | Accepted |
| [0012](0012-no-card-free-tier-hosting.md) | No-card free-tier hosting | Accepted |
| [0013](0013-pivot-to-ai-fashion-advisor.md) | Pivot to an AI fashion advisor | Accepted |
| [0014](0014-style-profile-on-device.md) | Style profile stored on the device at launch | Accepted |
| [0015](0015-shop-the-look-via-vision-model.md) | Shop the look via a free vision model and attribute search | Accepted |
| [0016](0016-ci-and-architecture-tests.md) | CI quality gate and architecture rules as tests | Accepted |
