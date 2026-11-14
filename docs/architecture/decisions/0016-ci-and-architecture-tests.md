# ADR 0016: CI quality gate and architecture rules as tests

- **Status:** Accepted
- **Date:** 2026-11-14

## Context

Only the collection workflow ran in CI; a broken test or type error could reach main unnoticed, and layering rules lived only in prose.

## Decision

`ci.yml` runs ruff, mypy, pytest (against a real pgvector Postgres) and the web lint, typecheck and build on every push and PR. `tests/test_architecture.py` enforces the dependency rule from the architecture overview.

## Consequences

Slightly slower merges; layering violations fail fast instead of accumulating.
