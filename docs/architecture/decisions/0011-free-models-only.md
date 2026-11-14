# ADR 0011: Free and open-source models only

- **Status:** Accepted
- **Date:** 2026-10-24

## Context

Zero budget: the owner pays for no LLM API.

## Decision

Ollama locally; free API tiers in production; the provider is chosen by env (`LLM_BASE_URL`, `LLM_MODEL_*`), never in code. Evals pick the model.

## Consequences

Rate limits and changing free tiers are a risk: AI endpoints get per-visitor rate limits and honest unavailable states. Free tiers may train on inputs, so no personal data goes into prompts.
