---
name: add-api-endpoint
description: Checklist for adding a FastAPI endpoint to fiyatgercek: schema, service, route, tests, auth, rate limit and docs. Use for any new or changed HTTP endpoint.
---

# Add an API endpoint

1. **Contract first.** Write the request and response Pydantic models in `src/fiyat/schemas/`.
   Prices are `price_minor` ints with a `currency` field. Include `status`, `real_discount_pct`,
   `claim_inflated`, `tracked_since` wherever a price is shown, so the frontend never computes discounts.
2. **Service function** in the matching module (`search/`, `alerts/`, `pricing/`...). All logic and
   queries live here, with an injected `AsyncSession`.
3. **Route** in `src/fiyat/api/routes/<area>.py`: validate, call the service, return the schema.
   No SQL and no business rules in the route. Use `Depends` for the session and the current user.
4. **Auth and limits:** decide who may call it (anonymous, user, admin). Add rate limiting for anything
   that is expensive or can send messages (search with LLM parsing, assistant, alert creation).
5. **Errors:** use the shared error model with a stable `code`; never leak stack traces or internal ids.
6. **Pagination:** list endpoints take `limit` (max 50) and a cursor or offset; return `next` info.
7. **Tests** in `tests/api/`: success, validation error, not found, unauthorized, and one edge case.
   Use `httpx.AsyncClient` against the app and a test database.
8. **OpenAPI:** open `/docs`, check names and examples read well. The frontend client is generated from it.
9. **Docs:** mention the endpoint in the relevant doc if it changes behaviour users or the frontend depend on.
10. **Run:** `uv run pytest`, `uv run ruff check .`, `uv run mypy src`. Commit: `feat(api): <endpoint>`.
11. Tell the owner in 2-4 sentences why the logic lives in the service and what the schema guarantees.
