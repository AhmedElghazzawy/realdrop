---
name: deploy
description: Release and deployment checklist for RealDrop on no-card free tiers (Neon Postgres, GitHub Actions collection, Render API, Vercel web), including migrations, scheduled jobs, health checks, smoke tests and rollback. Use for first deploy and every release.
---

# Deploy

**[ASK]** the owner before every production deploy. Never deploy during the 24 hours around 27 Nov
except for a hotfix the owner approves.

## Pre-flight

1. `git status` clean; branch up to date. CI green (tests, ruff, mypy, web lint/typecheck/test, `pricing` evals).
2. Relevant eval suites meet thresholds (`docs/EVALS.md`); record the scores.
3. Secrets are set in the hosts' settings (GitHub secrets, Render/Vercel env), never in the repo: `LLM_API_KEY`, `DATABASE_URL`,
   `REDIS_URL`, `COLLECTOR_USER_AGENT` (with a real contact address), `TELEGRAM_BOT_TOKEN`, `SENTRY_DSN`.
4. A fresh database backup exists and a restore of it has been tested at least once.

## First-time setup (once): `docs/DEPLOY.md`

No-card free tiers only (ADR 12). Never add a paid plan or a service that asks for a card without the
owner's explicit OK.

1. **Database:** Neon free project (Postgres 16, Frankfurt). Connection string only in the GitHub
   secret `DATABASE_URL` (`pbpaste | gh secret set DATABASE_URL`) and the hosts' env settings.
2. **Collection:** `.github/workflows/collect.yml`, scheduled daily; manual runs via
   `gh workflow run collect -f brand=<slug> -f limit=20`.
3. **API (later):** Render free web service from `apps/api/Dockerfile`; env: `DATABASE_URL`,
   `REDIS_URL` (a free Redis such as Upstash, only when the worker exists), `LLM_*`.
   Free services sleep when idle; the first request after a sleep is slow.
4. **Web (later):** Vercel free, root `apps/web`, `NEXT_PUBLIC_API_URL` pointing at Render.
5. Sentry free tier for API and web; a free uptime monitor on `/health`.

## Release

1. Merge to `main` with CI green. Render and Vercel deploy from `main`; the collect workflow always
   uses the latest `main`.
2. Migrations: `alembic upgrade head` runs at the start of every collection job; for an API release run
   it first (manual `collect` run with `limit=1`, or locally against the Neon URL).
   Migrations must be backward compatible with the running version (add columns before using them).
3. Health: `/health` returns ok; the latest `collection_runs` row per brand is `succeeded` or `partial`.

## Smoke test (after every deploy)

- Open the site on a phone-sized viewport; search "siyah oversize kaban"; open a product; view the chart.
- Create a test alert, then delete it.
- Check the latest `collection_runs`: each brand succeeded in the last scheduled window.
- Ask the assistant one price question; confirm it called a tool and the guard passed.
- Check Sentry for new errors and `llm_calls` for errors and rate-limit hits in the last hour.

## Rollback

If smoke tests fail: redeploy the previous commit (Render/Vercel "rollback" button). If a migration must be undone, run
`alembic downgrade -1` only if the migration was written to be reversible; otherwise restore from backup
and tell the owner exactly what data would be lost first.

## After

Record the release (date, commit, eval scores, notes) in `docs/ARCHITECTURE.md` decision log if it
changed anything structural. Tell the owner in 2-4 sentences what shipped and what to watch.
