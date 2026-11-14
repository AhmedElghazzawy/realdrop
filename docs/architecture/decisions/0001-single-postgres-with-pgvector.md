# ADR 0001: One Postgres for relational data, full-text search and vectors

- **Status:** Accepted
- **Date:** 2026-10-24

## Context

The product needs relational data (catalog, prices), full-text search and vector similarity. Running a separate search engine and vector store triples the moving parts for a one-person, five-week build.

## Decision

Use PostgreSQL 16 with pgvector, `unaccent` and `pg_trgm` for everything.

## Consequences

One backup, one connection, hybrid queries in SQL. Revisit if vector search latency or the free tier's storage becomes the bottleneck.
