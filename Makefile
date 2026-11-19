# One entry point for everyday tasks. `make help` lists them. CI runs `make check`'s steps.
.DEFAULT_GOAL := help
API := apps/api
WEB := apps/web

.PHONY: help setup up down api web test lint format typecheck check migrate collect-dry eval

help: ## List the available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[1m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install API and web dependencies
	cd $(API) && uv sync
	cd $(WEB) && pnpm install

up: ## Start local Postgres (pgvector) in Docker
	docker compose up -d --wait

down: ## Stop local containers (data volume is kept)
	docker compose down

api: ## Run the API with reload on http://localhost:8010
	cd $(API) && uv run uvicorn realdrop.main:app --app-dir src --reload --port 8010

web: ## Run the web app on http://localhost:3000
	cd $(WEB) && pnpm dev

test: ## Run the API test suite (needs `make up` for database tests)
	cd $(API) && uv run pytest -q

lint: ## Lint API and web
	cd $(API) && uv run ruff check . && uv run ruff format --check .
	cd $(WEB) && pnpm lint

format: ## Auto-format the API code
	cd $(API) && uv run ruff check --fix . && uv run ruff format .

typecheck: ## Type-check API (mypy) and web (tsc)
	cd $(API) && uv run mypy src
	cd $(WEB) && pnpm typecheck

check: lint typecheck test ## Everything CI checks, plus the web production build
	cd $(WEB) && pnpm build

migrate: ## Apply database migrations to DATABASE_URL (local by default)
	cd $(API) && uv run alembic upgrade head

collect-dry: ## Dry-run a collector: make collect-dry BRAND=defacto LIMIT=20
	cd $(API) && uv run python -m realdrop.collectors.run --brand $(BRAND) --limit $(or $(LIMIT),20) --dry-run

eval: ## Run an eval suite: make eval SUITE=tagger TAGGER=rules|llm|hybrid [MODEL=gemma4:12b RUNS=3]
	cd $(API) && uv run python -m realdrop.evals.run --suite $(or $(SUITE),tagger) --tagger $(or $(TAGGER),rules) $(if $(MODEL),--model $(MODEL)) --runs $(or $(RUNS),1)
