"""Regression: DB unavailable after startup → 503 PERSISTENCE_UNAVAILABLE (DEFECT-PERSIST-002)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from weaksignalradar.api.app import create_app
from weaksignalradar.fasttrack.db.repository import MemoryRunRepository


@pytest.fixture(autouse=True)
def _deterministic_embedding(monkeypatch):
    monkeypatch.setenv("WSR_EMBEDDING_BACKEND", "deterministic")


@pytest.fixture
def client_with_repo():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    app = create_app(engine=engine)
    app.state.run_repository = MemoryRunRepository()
    return TestClient(app)


def test_analysis_503_when_db_check_fails_after_startup(client_with_repo):
    with patch("weaksignalradar.fasttrack.persistence_guard.check_db_ready", return_value=False):
        resp = client_with_repo.post(
            "/api/v1/analyses",
            json={
                "query": "test",
                "data_mode": "CACHE",
                "score_profile_id": "ABCDE_v1",
                "snapshot_id": "ft_bench_v1",
            },
        )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "PERSISTENCE_UNAVAILABLE"


def test_analysis_503_when_save_raises_operational(client_with_repo):
    with patch("weaksignalradar.fasttrack.persistence_guard.check_db_ready", return_value=True):
        err = OperationalError("INSERT", {}, Exception("connection refused"))
        with patch.object(MemoryRunRepository, "save", side_effect=err):
            resp = client_with_repo.post(
                "/api/v1/analyses",
                json={
                    "query": "test",
                    "data_mode": "CACHE",
                    "score_profile_id": "ABCDE_v1",
                    "snapshot_id": "ft_bench_v1",
                },
            )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "PERSISTENCE_UNAVAILABLE"
    assert "connection refused" not in resp.text
    assert "operationalerror" not in resp.text.lower()


def test_refresh_503_when_db_check_fails(client_with_repo):
    with patch("weaksignalradar.fasttrack.persistence_guard.check_db_ready", return_value=False):
        resp = client_with_repo.post("/api/v1/refresh", json={"query": "q"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "PERSISTENCE_UNAVAILABLE"
