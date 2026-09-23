"""Health endpoint tests for the Stage A FastAPI scaffold."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from weaksignalradar.api.app import create_app
from weaksignalradar.storage.db import check_db_ready


def test_health_live_always_ok() -> None:
    app = create_app(engine=create_engine("sqlite+pysqlite:///:memory:"))
    # live must not depend on DB; use a dummy engine that may be unreachable dialect-wise
    client = TestClient(app)
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "live"}


def test_health_ready_with_postgres_when_configured() -> None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        pytest.skip("DATABASE_URL not set")
    engine = create_engine(url, pool_pre_ping=True)
    assert check_db_ready(engine) is True
    app = create_app(engine=engine)
    client = TestClient(app)
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


def test_health_ready_unavailable_without_database_url(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Engine that fails connectivity checks.
    class _Boom:
        def connect(self):  # noqa: ANN001
            raise RuntimeError("no db")

    app = create_app(engine=_Boom())  # type: ignore[arg-type]
    client = TestClient(app)
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
