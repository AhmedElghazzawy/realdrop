# RealDrop API / jobs image (for Render or any Docker host later). Multi-arch base images.
# The package is installed non-editable into /opt/venv; settings come from environment variables
# (compose), never from a .env file inside the image.
FROM ghcr.io/astral-sh/uv:0.12.23 AS uv

FROM python:3.12.15-slim-bookworm
COPY --from=uv /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /opt/realdrop/apps/api

# Dependencies first, so code changes do not reinstall them.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

RUN useradd --system --no-create-home app
USER app

CMD ["python", "-m", "realdrop.collectors.run", "--help"]
