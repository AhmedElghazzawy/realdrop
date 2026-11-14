# Setup (macOS, Apple M2, 16 GB)

Claude Code: do **Phase 1 only** when asked. Show a short plan, wait for approval, verify each step,
stop on failure. Do not touch anything the owner must do personally (logins, API keys).

Already provided in this kit: `docker-compose.yml`, `infra/initdb/01-extensions.sql`,
`.env.example`, `.gitignore`, `.vscode/settings.json`, `.vscode/extensions.json`, all docs, agents,
skills and the format hook. Phase 1 creates the apps and installs tools.

## Phase 1: environment

1. **Check installed tools:** `brew`, `git`, `gh`, `python3.12`, `uv`, `node`, `pnpm`, OrbStack (Docker),
   Ollama, the `code` command. Install only what is missing:
   `brew install git gh python@3.12 uv node pnpm ollama` and `brew install --cask orbstack`.
   Then `ollama pull gemma4:12b` (the free local LLM, about 8 GB).
   If `brew` itself is missing, stop and tell the owner.
2. **Git:** `git init -b main` if needed. Confirm `git config user.name` and `user.email` exist; if not,
   ask the owner for them. Do not run `gh auth login`; the owner does that.
3. **Backend:** `mkdir -p apps && cd apps && uv init api --python 3.12`. Create the package layout
   from `CLAUDE.md` under `apps/api/src/realdrop/` (empty `__init__.py` files and `text.py` with
   `tr_lower`, `tr_upper`, `normalize` and tests). Add dependencies:
   `fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" asyncpg alembic pydantic-settings httpx selectolax arq openai pgvector`
   and dev: `pytest pytest-asyncio pytest-socket ruff mypy`. Configure `pyproject.toml` for ruff,
   mypy (strict on `pricing` and `ai`) and pytest (asyncio mode auto, `--disable-socket`).
4. **Frontend:** `pnpm create next-app@latest apps/web --typescript --tailwind --app --eslint --src-dir --use-pnpm`.
   Accept defaults for other questions.
5. **Containers:** make sure OrbStack is running, then `docker compose up -d` and
   `docker compose ps` (both services healthy). The init script installs the `vector`, `unaccent`
   and `pg_trgm` extensions on first start. Verify:
   `docker compose exec db psql -U app -d realdrop -c "\dx"`.
6. **Env:** `cp .env.example .env` if `.env` does not exist. Never print `.env`. Defaults point at
   local Ollama (free, no key). Free API tier keys, if used, are put in by the owner personally.
7. **Verify (report as a checklist):**
   - `cd apps/api && uv run python -c "import fastapi, sqlalchemy, openai, pgvector; print('ok')"`
   - `cd apps/api && uv run pytest` passes (the `text.py` tests)
   - `cd apps/api && uv run ruff check . && uv run mypy src`
   - `cd apps/web && pnpm dev` serves `localhost:3000`, then stop it
   - `docker compose ps` shows `db` and `redis` healthy
   - `ollama list` shows `gemma4:12b`, and it answers through `LLM_BASE_URL` (OpenAI-compatible API)
8. **Commit:** `chore: bootstrap monorepo` (check `git status` first: no `.env`, no `node_modules`).

## Owner-only steps

- `gh auth login` (GitHub.com, HTTPS, browser), then `gh repo create realdrop --private --source=. --push`.
- Later (roadmap Phase 7): create a free API key on a free tier (Groq, OpenRouter or Google AI Studio) and put it
  in `.env`. Free tiers only; no card on file.
- Create a Telegram bot with BotFather later (Phase: alerts) and put the token in `.env`.

## Troubleshooting

- `ModuleNotFoundError: No module named 'realdrop'` under `uv run`: macOS flagged the venv's `.pth`
  files as hidden and Python 3.12.15+ skips hidden `.pth` files. Fix:
  `chflags nohidden apps/api/.venv/lib/python3.12/site-packages/*.pth`.
- Port 5432 busy: another Postgres is running; stop it or change the host port in `docker-compose.yml`.
- `docker: command not found`: open OrbStack once so it installs the CLI.
- Apple Silicon image issues: `pgvector/pgvector:pg16` is multi-arch; if pulling fails, check the network.
- Init SQL does not run again once the volume exists. To re-run it:
  `docker compose down -v` (deletes local DB data; ask the owner first).

## Run the app locally (API + web)

```bash
# Terminal 1, API on :8010 (8000 may be taken by another project). Uses DATABASE_URL from .env
# (local Docker). To browse the live cloud data instead, start it with the Neon URL injected:
#   DATABASE_URL="$(npx -y neonctl connection-string --project-id frosty-sun-14684999)" \
cd apps/api && PYTHONPATH=src uv run uvicorn realdrop.main:app --app-dir src --port 8010

# Terminal 2, web on :3000
cd apps/web && API_URL=http://localhost:8010 pnpm dev
```

Pages: `/` products (search, sort), `/products/<id>` price history and sizes, `/status` collection runs.
