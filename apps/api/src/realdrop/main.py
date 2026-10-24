"""FastAPI app factory. Run with `uv run uvicorn realdrop.main:app --reload`."""

from fastapi import FastAPI

from realdrop.api.routes import health


def create_app() -> FastAPI:
    app = FastAPI(title="RealDrop API", version="0.1.0")
    app.include_router(health.router)
    return app


app = create_app()
