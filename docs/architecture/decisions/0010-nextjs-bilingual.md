# ADR 0010: Next.js frontend, English default and Turkish

- **Status:** Accepted
- **Date:** 2026-10-25

## Context

Mobile-first UX, server rendering and an easy free deploy were needed.

## Decision

Next.js App Router with `/en` and `/tr`; strings in `i18n/{en,tr}.ts`.

## Consequences

Every new string goes into both dictionaries; English is the source of truth.
