# ADR 0006: Change-only price observations with a derived daily table

- **Status:** Accepted (amended 2026-10-25)
- **Date:** 2026-10-24

## Context

The glitch filter needs raw observations; history must stay auditable; Neon's 0.5 GB cannot hold one row per variant per run.

## Decision

`price_observations` stores one row per unchanged state (a stretch with `observed_at` and `last_seen_at`); `price_daily` is derived and rebuilt by `pipeline/rollup.py`. Rows are never deleted.

## Consequences

Compact and auditable. Rebuilds must be serialised across parallel brand jobs (advisory lock, fixed 14 Nov 2026).
