"""FastAPI backend: Stage A health + FastTrack /api/v1 (when mounted)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Response, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import Engine

from weaksignalradar.fasttrack.api.router import router as fasttrack_router
from weaksignalradar.fasttrack.db.repository import build_run_repository
from weaksignalradar.observability.event_log import emit_event
from weaksignalradar.storage.db import check_db_ready, create_db_engine


def _frontend_dir() -> Path:
    if raw := os.environ.get("FRONTEND_DIR", "").strip():
        return Path(raw)
    checkout = Path(__file__).resolve().parents[3] / "frontend"
    if checkout.is_dir():
        return checkout
    container = Path("/app/frontend")
    if container.is_dir():
        return container
    return checkout


def create_app(*, engine: Engine | None = None) -> FastAPI:
    """Application factory (engine injectable for tests)."""

    state: dict[str, Any] = {"engine": engine}

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if state["engine"] is None:
            try:
                state["engine"] = create_db_engine()
            except Exception:
                state["engine"] = None
        application.state.engine = state["engine"]
        application.state.run_repository = build_run_repository(state["engine"])
        emit_event("SERVICE_STARTED", component="backend")
        if state["engine"] is not None and check_db_ready(state["engine"]):
            emit_event("SERVICE_READY", component="backend", status="ready")
        yield

    application = FastAPI(
        title="weaksignalradar-snnit-fasttrack",
        version="0.2.0-fasttrack",
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    application.include_router(fasttrack_router)
    application.state.engine = state["engine"]
    application.state.run_repository = build_run_repository(state["engine"])

    frontend_dir = _frontend_dir()
    static_dir = frontend_dir / "static"
    if static_dir.is_dir():
        application.mount("/static", StaticFiles(directory=static_dir), name="static")

    @application.get("/", include_in_schema=False, response_model=None)
    def ui_shell() -> FileResponse | HTMLResponse:
        index = frontend_dir / "index.html"
        if index.is_file():
            return FileResponse(index)
        return HTMLResponse("<p>UI shell not packaged</p>", status_code=503)

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
        state["engine"] = eng
        application.state.engine = eng
        if application.state.run_repository is None:
            application.state.run_repository = build_run_repository(eng)
        if not check_db_ready(eng):
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "not_ready", "reason": "database_unavailable"}
        repo = getattr(application.state, "run_repository", None)
        if repo is None:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            emit_event(
                "SERVICE_NOT_READY",
                level="WARN",
                component="backend",
                status="not_ready",
                reason_code="persistence_unavailable",
            )
            return {"status": "not_ready", "reason": "persistence_unavailable"}
        return {"status": "ready"}

    return application


def get_app() -> FastAPI:
    """Uvicorn factory entrypoint."""
    return create_app()


app = create_app()
