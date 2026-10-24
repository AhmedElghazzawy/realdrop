# RealDrop API

Python 3.12 + FastAPI backend. Package: `src/realdrop/`. Project rules live in the root `CLAUDE.md`.

```bash
uv sync                                    # install
uv run pytest                              # tests (real network is blocked)
uv run ruff check . && uv run ruff format --check .
uv run mypy src tests
```
