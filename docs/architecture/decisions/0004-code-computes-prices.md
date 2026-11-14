# ADR 0004: Discounts are computed in code; the LLM only explains

- **Status:** Accepted
- **Date:** 2026-10-24

## Context

Trust is the product. LLMs can invent or miscalculate numbers.

## Decision

Every price, discount and history fact comes from `pricing/` over stored data. Any AI text with numbers passes a number-grounding guard against tool outputs.

## Consequences

AI answers are slightly less fluent; zero invented prices is a hard eval gate.
