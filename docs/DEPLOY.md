# Production setup (free tiers, no credit card)

ADR 12: everything runs on free tiers that need no card. Phase 3 needs only the first two rows.

| Piece | Service | Status |
|---|---|---|
| Database | Neon free Postgres (0.5 GB) | Phase 3 |
| Daily collection | GitHub Actions, `.github/workflows/collect.yml` | Phase 3 |
| API | Render free web service (Docker, `apps/api/Dockerfile`) | Phase 7-8 |
| Web | Vercel free (Next.js) | Phase 8 |

## 1. Neon database (owner, ~3 min)

1. <https://console.neon.tech> -> **New project**: name `realdrop`, Postgres **16**, region
   **AWS Europe Central 1 (Frankfurt)** (closest to Turkey and to the data we collect).
2. On the project dashboard click **Connect** and copy the connection string (any variant works:
   `config.asyncpg_url` turns Neon's string into an asyncpg URL and uses the direct, non-pooled host).
3. Store it as a GitHub secret **without pasting it anywhere else** (from the repo folder on the Mac,
   right after copying it):

   ```bash
   pbpaste | gh secret set DATABASE_URL
   ```

The first workflow run creates the tables and extensions (`alembic upgrade head`).

## 2. Collection on GitHub Actions

- Scheduled twice a day: 00:00 UTC (03:00 Turkey) collects shard `0/2`, 12:00 UTC (15:00 Turkey)
  shard `1/2`, for every brand in parallel (DeFacto, Colin's, Koton, Mudo, GAP, Marks & Spencer, Damat Tween, Les Benjamins).
  DeFacto has ~14.6k product pages, ~5 h at 1 request/s, so each half (~2.5-3 h) stays inside the
  job limit; Colin's (~5.75k pages) takes ~1 h per half. The Akinon brands collect men's products
  only; Koton's men's listing (~7k products, ~295 listing pages read by both halves) is the largest. Every product is still seen once a day. Up to 3 pages download at once;
  request starts stay at 1 per second. GitHub can start scheduled runs late under load, and disables
  schedules after 60 days without repo activity (not a risk while we build daily).
- Manual run (test or catch-up): Actions -> collect -> **Run workflow** (brand, optional limit), or
  `gh workflow run collect -f brand=defacto -f limit=20 -f shard=0/2`.
- A `migrate` job runs `alembic upgrade head` once; then one `collect` job per brand (install,
  collect, roll up `price_daily`). Two runs of the same brand never overlap. A job is killed after
  330 min (GitHub's limit is 6 h; half of DeFacto is ~2.5-3 h).
- A page that keeps answering 5xx is skipped as a failure; 3 such pages in a row, 20 non-product
  pages in a row, a 403, or exhausted 429s stop the run.
- Every run, including failed and blocked ones, is a row in `collection_runs`; the job log shows the
  same summary.

## Checking on it

```bash
gh run list --workflow collect --limit 5
gh run view --log <run-id> | tail -20
```

## Limits to watch

- **Storage 0.5 GB**: one brand daily is ~7 MB/day (fits until launch). More brands or 4-hourly runs
  need change-only observations first (Phase 4 decision). Check usage in the Neon console.
- **Datacenter IPs**: some shops block cloud IPs. If a run stops with `CollectorBlockedError`, we stop
  for that brand and decide; we never route around a block.
- **Backups**: Neon keeps a short restore window on the free tier. A `pg_dump` export comes in Phase 12.
