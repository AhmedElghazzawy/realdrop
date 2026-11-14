# ADR 0015: Shop the look via a free vision model and attribute search

- **Status:** Accepted
- **Date:** 2026-11-14

## Context

Matching a social-media photo to products needs piece detection and similarity. Image-embedding models (SigLIP/CLIP) need more memory at query time than Render's free 512 MB, and no paid API is allowed.

## Decision

v1: a free vision model (Gemini or Groq free tier, chosen by a small eval) returns each piece in our attribute schema; matching uses attribute filters plus semantic text search over tagged products. The photo is not stored.

## Consequences

Matches are 'similar style', not exact items; quality depends on catalog tagging (Phase 5). v2 after launch: image-embedding similarity computed in batch for products, with a query-time host that fits. Privacy notice must name the provider.
