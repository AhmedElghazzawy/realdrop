---
name: add-brand-collector
description: Step-by-step checklist for adding a new retailer collector to RealDrop, from feasibility check to registered, tested, scheduled collector. Use whenever a new brand is added or an existing collector is rebuilt.
---

# Add a brand collector

Follow in order. Stop and ask the owner at every **[ASK]**.

## 1. Feasibility (no code yet)

1. Fetch `<base_url>/robots.txt` and read the rules for the paths we need.
2. Read the site's terms of service for clauses on automated access. Quote the relevant sentence in the brand doc.
3. Look for data sources in this order: official feed or affiliate data, documented API, the site's
   own JSON endpoints (browser DevTools -> Network -> filter Fetch/XHR while browsing a category and a
   product page), then server-rendered HTML. Note the exact endpoints and parameters.
4. Check: stable product ids and URLs, sizes and stock per variant, original (claimed) price, catalog size,
   pagination limits.
5. Write `docs/brands/<slug>.md` with the findings and a go / no-go recommendation. **[ASK] owner decides.**

## 2. Skeleton

Create `apps/api/src/realdrop/collectors/<slug>/` with `collector.py`, `parser.py`, `fixtures/`, `__init__.py`.

## 3. Implement

- Subclass `BrandCollector` (`collectors/base.py`): set `slug`, `rate_limit_rps` (default 1), implement
  `async def fetch_catalog(self) -> AsyncIterator[RawProduct]`.
- Use the shared `httpx.AsyncClient` with `COLLECTOR_USER_AGENT`, timeouts, retries with exponential
  backoff on 429/5xx, and jitter. Honour `Retry-After`.
- On 403 or a block/CAPTCHA page: stop the brand, record the run as failed with the reason, tell the owner.
  Do not rotate proxies, spoof fingerprints, solve CAPTCHAs or log in.
- `parser.py` is pure: raw payload in, `RawProduct` out. Prices to integer kurus
  (`"1.299,90 TL"` -> `129990`). Normalize size labels and colors with the taxonomy helpers.
  Use `realdrop.text` for any casing.
- Emit `original_price_minor` only when the site shows a strike-through or "old price"; otherwise `None`.

## 4. Fixtures and tests

- Save at least 3 real responses in `fixtures/`: a listing page, a product with several sizes, and an
  out-of-stock product. Strip any personal data and tracking tokens.
- `tests/collectors/test_<slug>.py` parses fixtures only. The network is blocked (`pytest-socket`).
- Assert prices in kurus, stock flags, size normalization, claimed price, and that missing fields do not crash.

## 5. Register and dry-run

1. Add the collector to `collectors/registry.py`.
2. Run `uv run python -m realdrop.collectors.run --brand <slug> --limit 20 --dry-run`.
3. Show the owner the printed sample (10 products with variants and prices). **[ASK] approve before storing.**
4. Run without `--dry-run` for the same 20 products and verify rows in `products`, `variants`,
   `price_observations`.

## 6. Schedule and finish

1. Add the brand to `jobs/schedule.py`, staggered from other brands.
2. Update `docs/brands/<slug>.md` with the final endpoints and known quirks.
3. `uv run pytest`, `uv run ruff check .`, `uv run mypy src` pass.
4. Commit: `feat(collector): add <slug>`.
5. Tell the owner in 2-4 sentences how this site serves its data and what could break it.
