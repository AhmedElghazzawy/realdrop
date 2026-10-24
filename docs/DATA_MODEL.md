# Data model

All ids are UUIDs unless noted. All timestamps are `timestamptz` (UTC). `snapshot_date` is the
`Europe/Istanbul` calendar date. Money is integer **kurus** (`price_minor`); 1 TRY = 100 kurus.

## Tables

### Catalog

- **brands**: `id`, `slug` (unique), `name`, `country` (default `TR`), `currency` (default `TRY`),
  `base_url`, `is_active`, `collector_config` (jsonb)
- **products**: `id`, `brand_id` FK, `external_id`, `url`, `title_raw`, `description_raw`,
  `image_urls` (text[]), `category_raw`, `content_hash`, `first_seen_at`, `last_seen_at`, `is_active`.
  Unique `(brand_id, external_id)`.
- **product_attributes**: `product_id` PK/FK, `category`, `subcategory`, `gender`, `colors` (text[]),
  `fit`, `material` (text[]), `season` (text[]), `occasion` (text[]), `formality`, `pattern`,
  `confidence` (jsonb), `extractor_version`, `extracted_at`.
- **variants**: `id`, `product_id` FK, `external_sku`, `size_label`, `size_normalized`, `color_raw`,
  `color_normalized`. Unique `(product_id, external_sku)`.

### Prices

- **collection_runs**: `id`, `brand_id`, `started_at`, `finished_at`, `status`, `items_seen`,
  `items_failed`, `notes`.
- **price_observations** (append-only): `id` bigserial, `variant_id` FK, `run_id` FK, `observed_at`,
  `price_minor`, `original_price_minor` (nullable, what the retailer claims as the old price),
  `in_stock`, `status` enum(`confirmed`,`pending`,`rejected`), `reject_reason`.
  Index `(variant_id, observed_at)`.
- **price_daily** (derived): `variant_id`, `snapshot_date`, `close_price_minor` (last confirmed of the
  day), `low_price_minor`, `high_price_minor`, `claimed_original_minor`, `in_stock_close`.
  PK `(variant_id, snapshot_date)`.
- **current_prices** (materialized view or table): `variant_id` PK, `price_minor`,
  `claimed_original_minor`, `in_stock`, `as_of`, plus the computed `status`, `real_discount_pct`,
  `claim_inflated`, `all_time_low` from `pricing/real_drop.py`.

### Search

- **product_embeddings**: `product_id` PK/FK, `model`, `dim`, `embedding vector(1024)`, `text_hash`,
  `created_at`. HNSW index with `vector_cosine_ops`.
- Full-text: generated `tsvector` column on a `product_search` view combining title, brand,
  category, extracted attributes; `simple` config plus `unaccent`; GIN index. Also `pg_trgm`
  for typo tolerance.

### Users and personalization

- **users**: `id`, `email` (nullable, unique), `telegram_chat_id` (nullable), `locale` (`tr`),
  `consent_at`, `created_at`, `deleted_at`.
- **user_signals**: `id`, `user_id`, `product_id`, `type` enum(`view`,`click`,`save`,`dismiss`,
  `alert_create`,`dwell`), `weight`, `created_at`, `meta` (jsonb).
- **user_taste**: `user_id` PK, `vector vector(1024)` (nullable), `counters` (jsonb: brands, colors,
  fits, price bands, sizes), `updated_at`.

### Alerts

- **alerts**: `id`, `user_id`, `product_id`, `size_normalized` (nullable = any size),
  `target_price_minor` (nullable), `min_real_discount_pct` (nullable), `channels` (text[]),
  `is_active`, `cooldown_until`, `last_notified_price_minor`, `created_at`.
  At least one of target price or minimum real discount must be set.
- **alert_events**: `id`, `alert_id`, `price_minor`, `real_discount_pct`, `channel`, `sent_at`,
  `delivery_status`.

### Operations

- **llm_calls**: `id`, `purpose` (extractor|parser|assistant|other), `provider` (ollama|groq|openrouter|
  gemini|...), `model`, `input_tokens`, `output_tokens`, `latency_ms`, `status` (ok|invalid|rate_limited|
  error), `trace_id`, `created_at`. No cost column: free models only.
- **assistant_usage**: `user_id`, `usage_date`, `messages_count`, `tokens`. PK `(user_id, usage_date)`.

## Glitch filter (`pipeline/validate.py`)

Applies to each new observation. Defaults live in `pricing/config.py` and are covered by tests.

1. **Reject** if `price_minor <= 0` or `price_minor < MIN_PRICE_MINOR` (default 500, i.e. 5 TRY).
2. **Hold as `pending`** if the price differs from the last confirmed price by `>= 70%`, or is below
   `20%` of the 30-day median, or `original_price_minor < price_minor` (impossible claim).
3. A pending observation becomes **`confirmed`** when a second observation with the same price
   arrives at least 30 minutes later (any run).
4. A pending observation not confirmed within **48 hours** becomes `rejected` (reason logged).
5. Only `confirmed` observations feed `price_daily`, the real-drop rule and alerts.

## Real-drop rule (`pricing/real_drop.py`)

For a variant on day `t`, with `P_t` the confirmed close price:

- **History** `H` = confirmed daily close prices for days `t-30 ... t-1` on which the variant was tracked.
- If `len(H) < MIN_HISTORY_DAYS` (default 14): status = `insufficient_history`. **No real-discount claim.**
  The UI shows "tracking since <date>".
- `reference = median(H)` (the median resists one-day spikes and one-day dips).
- `real_discount_pct = (reference - P_t) / reference`.
- `claimed_discount_pct = (claimed_original - P_t) / claimed_original` when a claimed original exists.

Status (exactly one):

| Status | Condition |
|---|---|
| `real_drop` | `real_discount_pct >= 0.10` and `P_t <= min(last 7 days of H)` and in stock |
| `small_drop` | `0.03 <= real_discount_pct < 0.10` |
| `normal` | `-0.03 < real_discount_pct < 0.03` |
| `price_up` | `real_discount_pct <= -0.03` |
| `insufficient_history` | see above |

Flags (independent):

- `claim_inflated`: `claimed_discount_pct >= 0.20` and `claimed_discount_pct - real_discount_pct >= 0.15`.
- `all_time_low`: `P_t <= min(all confirmed daily closes)` with at least `MIN_HISTORY_DAYS` of history.

Known limitations (document them in the UI where relevant): gradual end-of-season markdowns lag behind
the 30-day median; before 30 days of history exist the window is `min(30, available)`; a retailer that
raises the price for a few days and then "discounts" is only caught if the raise happened after we
started tracking.

All thresholds are config, and the rule is pure functions over a price series, so it is easy to test:
median robust to a single spike, monotonic in price, no claim under 14 days, flags independent of status.

## Alert rule (`alerts/evaluate.py`)

When a new **confirmed** price arrives for a variant, for each active alert on that product:

1. Skip if the variant is out of stock, or the alert has a size and it does not match this variant.
2. Fire if `price <= target_price_minor`, **or** if status is `real_drop` and
   `real_discount_pct >= min_real_discount_pct`.
3. Skip if `now < cooldown_until`, or `price == last_notified_price_minor`.
4. On fire: send, write `alert_events`, set `cooldown_until = now + 24h`, store `last_notified_price_minor`.
5. Per-user cap: at most 5 alert messages per day; extra matches go into a single digest message.

Alerts never reference a price that is not in `price_observations` as `confirmed`.
