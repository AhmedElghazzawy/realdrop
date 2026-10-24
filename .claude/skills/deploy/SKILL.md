---
name: deploy
description: Release and deployment checklist for fiyatgercek to the production VPS (Docker Compose via Coolify), including migrations, backups, scheduled jobs, health checks, smoke tests and rollback. Use for first deploy and every release.
---

# Deploy

**[ASK]** the owner before every production deploy. Never deploy during the 24 hours around 27 Nov
except for a hotfix the owner approves.

## Pre-flight

1. `git status` clean; branch up to date. CI green (tests, ruff, mypy, web lint/typecheck/test, `pricing` evals).
2. Relevant eval suites meet thresholds (`docs/EVALS.md`); record the scores.
3. Secrets are set in the server's secret store, not in the repo: `ANTHROPIC_API_KEY`, `DATABASE_URL`,
   `REDIS_URL`, `COLLECTOR_USER_AGENT` (with a real contact address), `TELEGRAM_BOT_TOKEN`, `SENTRY_DSN`.
4. A fresh database backup exists and a restore of it has been tested at least once.

## First-time server setup (once)

1. Create the VPS (Ubuntu LTS), a non-root user, SSH keys only, firewall allowing 22/80/443, automatic security updates.
2. Install Docker and Coolify (or plain Docker Compose); connect the GitHub repo.
3. Services: `db` (pgvector image, persistent volume, **not** exposed publicly), `redis`, `api`,
   `worker` (Arq), `scheduler` (collection jobs), `web`. Reverse proxy with automatic HTTPS.
4. Daily database backup to off-server storage; test a restore.
5. Sentry for API and web; uptime monitor on `/health`.

## Release

1. Build and push images (or let Coolify build from the commit).
2. Run migrations: `alembic upgrade head` as a one-off job **before** starting the new API version.
   Migrations must be backward compatible with the running version (add columns before using them).
3. Roll out `api`, `worker`, `scheduler`, `web`. Keep the previous image tag for rollback.
4. Health: `/health` returns ok; worker connected to Redis; scheduler registered the jobs.

## Smoke test (after every deploy)

- Open the site on a phone-sized viewport; search "siyah oversize kaban"; open a product; view the chart.
- Create a test alert, then delete it.
- Check the latest `collection_runs`: each brand succeeded in the last scheduled window.
- Ask the assistant one price question; confirm it called a tool and the guard passed.
- Check Sentry for new errors and `llm_calls` for the cost of the last hour.

## Rollback

If smoke tests fail: redeploy the previous image tag. If a migration must be undone, run
`alembic downgrade -1` only if the migration was written to be reversible; otherwise restore from backup
and tell the owner exactly what data would be lost first.

## After

Record the release (date, commit, eval scores, notes) in `docs/ARCHITECTURE.md` decision log if it
changed anything structural. Tell the owner in 2-4 sentences what shipped and what to watch.
