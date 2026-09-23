"""Minimal FastAPI backend for Stage A (A-04).

Exposes only local health endpoints. No public web product surface,
no Discovery API, no ranking/buckets/VERIFIED.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Response, status
from sqlalchemy.engine import Engine

from weaksignalradar.storage.db import check_db_ready, create_db_engine


def create_app(*, engine: Engine | None = None) -> FastAPI:
    """Application factory (engine injectable for tests)."""

    state: dict[str, Any] = {"engine": engine}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if state["engine"] is None:
            state["engine"] = create_db_engine()
        yield

    application = FastAPI(
        title="weaksignalradar-stage-a",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @application.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "live"}

    @application.get("/health/ready")
    def health_ready(response: Response) -> dict[str, str]:
        eng: Engine | None = state.get("engine")
        if eng is None:
            try:
                eng = create_db_engine()
                state["engine"] = eng
            except Exception:
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                return {"status": "not_ready", "reason": "database_url_missing_or_invalid"}
        if check_db_ready(eng):
            return {"status": "ready"}
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "database_unavailable"}

    return application


def get_app() -> FastAPI:
    """Uvicorn factory entrypoint."""
    return create_app()


app = create_app()
