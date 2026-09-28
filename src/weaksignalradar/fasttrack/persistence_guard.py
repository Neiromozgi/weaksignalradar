"""Fail-closed persistence checks for FastTrack."""

from __future__ import annotations

from fastapi import HTTPException, Request
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, OperationalError

from weaksignalradar.storage.db import check_db_ready


def is_persistence_failure(exc: BaseException) -> bool:
    if isinstance(exc, (OperationalError, DBAPIError)):
        return True
    cause = exc.__cause__
    if isinstance(cause, (OperationalError, DBAPIError)):
        return True
    msg = str(exc).lower()
    return "connection" in msg and ("refused" in msg or "closed" in msg or "terminated" in msg)


def ensure_persistence_operational(request: Request) -> Engine:
    eng = getattr(request.app.state, "engine", None)
    if eng is None:
        raise HTTPException(status_code=503, detail="PERSISTENCE_UNAVAILABLE")
    if not check_db_ready(eng):
        request.app.state.run_repository = None
        raise HTTPException(status_code=503, detail="PERSISTENCE_UNAVAILABLE")
    return eng
