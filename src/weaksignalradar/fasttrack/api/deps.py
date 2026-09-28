"""FastAPI dependencies for FastTrack persistence."""

from __future__ import annotations

from fastapi import HTTPException, Request

from ..db.repository import RunRepository
from ..domain.run_state import AnalysisRunState


def get_run_repository(request: Request) -> RunRepository:
    repo = getattr(request.app.state, "run_repository", None)
    if repo is None:
        raise HTTPException(status_code=503, detail="PERSISTENCE_UNAVAILABLE")
    return repo


def get_engine(request: Request):
    eng = getattr(request.app.state, "engine", None)
    if eng is None:
        raise HTTPException(status_code=503, detail="PERSISTENCE_UNAVAILABLE")
    return eng


def load_run(run_id: str, request: Request) -> AnalysisRunState:
    state = get_run_repository(request).get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    return state
