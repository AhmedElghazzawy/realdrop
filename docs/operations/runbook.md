# Runbook

What to check, and what to do when something breaks. Setup of the services themselves:
[`deployment.md`](deployment.md).

## Daily health check (2 minutes)

```bash
gh run list --workflow collect --limit 4          # last two days: both runs green?
gh run list --workflow ci --limit 3               # main green?
```

The site's `/status` page shows the latest run per brand with product counts. Neon console:
storage under 400 MB of 512 MB.

## Collection run failed

Find the brand and the error:

```bash
gh run view <run-id> --json jobs --jq '.jobs[] | select(.conclusion != "success") | .name'
gh run view <run-id> --log-failed | grep -E "Error|RUN STOPPED|Traceback" | head
```

| Error in the log | Meaning | Action |
|---|---|---|
| `CollectorBlockedError` / 403 | The site blocks us (often datacenter IPs) | **Stop.** Never route around a block. Record it in `docs/data-sources/<brand>.md`, tell the owner |
| `robots.txt disallows` | The site changed its rules | Stop collecting that path; update the data-source doc; owner decides |
| `CollectorServerError` after retries / repeated 502 | The site is overloaded or rate-limiting | Usually transient: check the next run. If it repeats 3 runs in a row, slow the brand down |
| `listing page without product data` / parse errors | Challenge page or markup change | Save one live page as a new fixture, write a failing parser test, fix the parser |
| `UniqueViolationError` on `pk_price_daily` | Concurrent roll-ups (fixed 14 Nov 2026 with an advisory lock) | Should not happen any more; if it does, check that `pipeline/rollup.py` still takes the lock |
| Job killed at 330 min | A brand outgrew one shard | Split it into more shards in `collect.yml` |

Prices from a failed run are not lost: every batch commits on its own. A missed roll-up is repaired
by the next successful run of that brand (it rebuilds the last 7 days, `ROLLUP_LOOKBACK`).

Re-run one brand by hand:

```bash
gh workflow run collect -f brand=<slug> -f shard=0/2
```

## CI failed on main

Open the run (`gh run view <id> --log-failed`), reproduce with `make check` locally, fix forward
with a commit. Do not push further features on a red main.

## Free model API unavailable or rate-limited (after Phase 7)

Expected behaviour: shop the look and the stylist show an honest "not available right now" state;
the feed, shop and product pages keep working. Check the provider's status page; if limits are hit
daily, lower per-visitor limits or switch provider via `LLM_*` environment variables (no code change).

## Neon storage near the limit

Check the largest tables (`pg_total_relation_size`). `price_observations` is change-only and grows
slowly; embeddings are the likely culprit; reduce dimension or move to `halfvec` (see the data model).
Never delete price history to make room without an owner decision.

## Security incident (leaked secret)

1. Rotate the secret at the provider (Neon: reset the role password; GitHub: regenerate the token).
2. Update the GitHub/Render/Vercel secret.
3. If it was committed, rewriting history is not enough on a public repo: rotation is what counts.
