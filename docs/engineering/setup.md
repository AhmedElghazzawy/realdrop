# Local development

From a fresh clone to a running app and a green `make check`. macOS (Apple Silicon) is the primary
platform; Linux works the same.

## Prerequisites

| Tool | Version | Install (macOS) |
|---|---|---|
| Docker | OrbStack or Docker Desktop | `brew install --cask orbstack` |
| Python | 3.12 (managed by uv) | `brew install uv` |
| Node | 24 LTS | `brew install node` |
| pnpm | from `apps/web/package.json` `packageManager` | `corepack enable` |
| gh | any recent | `brew install gh` (then `gh auth login`) |
| Ollama (optional) | any recent | `brew install ollama && ollama pull gemma4:12b` (for AI work, ~8 GB) |

## First run

```bash
git clone git@github.com:AhmedElghazzawy/realdrop.git && cd realdrop
cp .env.example .env     # local defaults work as is; never commit .env
make setup               # uv sync + pnpm install
make up                  # Postgres 16 + pgvector in Docker, waits until healthy
make migrate             # alembic upgrade head on the local database
make check               # lint, types, tests, web build: should be green
```

Then, in two terminals:

```bash
make api                 # http://localhost:8010/docs
make web                 # http://localhost:3000 (reads API_URL, default http://localhost:8010)
```

The local database starts empty. To fill it with real products, dry-run a collector
(`make collect-dry BRAND=defacto LIMIT=20`) or run a stored collection against local Postgres:

```bash
cd apps/api && uv run python -m realdrop.collectors.run --brand lesbenjamins --limit 50
```

To browse production-like data, point the API at a Neon **branch** (never prod) by injecting its
connection string into `DATABASE_URL` for that one command, without printing or saving it.

## Everyday commands

`make help` lists them all. The ones you need daily:

| Task | Command |
|---|---|
| Tests (API) | `make test`, or `cd apps/api && uv run pytest tests/pipeline -q` for one folder |
| Format + autofix | `make format` |
| New migration | `cd apps/api && uv run alembic revision --autogenerate -m "add product_attributes"` (review the file; see the `add-migration` skill) |
| Everything CI runs | `make check` |

## How tests use the database

DB tests run against a separate `realdrop_test` database on the local Postgres, built by the real
Alembic migrations, each test inside a rolled-back transaction. If Postgres is down they are skipped
locally (CI fails instead: `REQUIRE_DB=1`). Network access is blocked in tests (`pytest-socket`).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'realdrop'` | The repo is inside an iCloud-synced folder and macOS hid the venv's `.pth` file. `chflags nohidden apps/api/.venv/lib/python3.12/site-packages/*.pth`, or move the repo out of `~/Desktop` / `~/Documents` |
| `pnpm dev` ignores edits to `globals.css` | Same iCloud cause; restart `make web` |
| Port 5432 busy | Another Postgres is running: stop it or change the host port in `docker-compose.yml` |
| `docker: command not found` | Open OrbStack once so it installs the CLI |
| DB tests skipped | `make up`, then re-run |
| Init SQL did not run | It runs only when the volume is created: `docker compose down -v` deletes local data and re-creates it |
