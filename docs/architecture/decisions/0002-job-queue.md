# ADR 0002: Arq + Redis for background jobs

- **Status:** Superseded by 0012 (2026-11-14)
- **Date:** 2026-10-24

## Context

Scheduled collection and fan-out work needed a job runner.

## Decision

Use Arq on Redis rather than Celery.

## Consequences

Never implemented: scheduled work runs on GitHub Actions (ADR 0012), so Arq and Redis were removed on 14 Nov 2026. If the API ever needs in-process background work, reconsider with a fresh ADR.
