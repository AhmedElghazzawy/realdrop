# ADR 0005: Self-hosted bge-m3 embeddings and reranker

- **Status:** Accepted
- **Date:** 2026-10-24

## Context

Search needs multilingual (Turkish/English) embeddings with no per-query cost.

## Decision

Use bge-m3 (and bge-reranker-v2-m3 if needed), run locally or in batch.

## Consequences

Free and good on Turkish. Query-time embedding needs a host with enough memory; Phase 5 decides where it runs.
