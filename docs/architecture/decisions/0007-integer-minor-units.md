# ADR 0007: Money as integer minor units

- **Status:** Accepted
- **Date:** 2026-10-24

## Context

Floats cause rounding errors in comparisons and medians.

## Decision

Store `price_minor` as bigint kuruş with a `currency` column next to every price; parse retailer prices via Decimal.

## Consequences

Exact arithmetic everywhere; formatting happens only at the edge.
