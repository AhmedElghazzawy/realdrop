# ADR 0003: OpenAI-compatible client with a hand-written tool loop, no agent framework

- **Status:** Accepted
- **Date:** 2026-10-24

## Context

The owner is learning AI engineering; frameworks hide the loop, add dependencies and make behaviour harder to test.

## Decision

Use the `openai` package only as a client for any OpenAI-compatible endpoint, and write the tool loop, validation and guards ourselves. No LangChain, LlamaIndex or similar.

## Consequences

More code to own, but every step is visible and testable, and one client works with Ollama and every free API tier.
