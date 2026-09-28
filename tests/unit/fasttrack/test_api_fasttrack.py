import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from weaksignalradar.api.app import create_app


@pytest.fixture(autouse=True)
def _deterministic_embedding(monkeypatch):
    monkeypatch.setenv("WSR_EMBEDDING_BACKEND", "deterministic")


@pytest.fixture(autouse=True)
def _db_ready(monkeypatch):
    monkeypatch.setattr(
        "weaksignalradar.fasttrack.persistence_guard.check_db_ready",
        lambda _eng: True,
    )


@pytest.fixture
def client():
    from weaksignalradar.fasttrack.db.repository import MemoryRunRepository

    engine = create_engine("sqlite+pysqlite:///:memory:")
    app = create_app(engine=engine)
    app.state.run_repository = MemoryRunRepository()
    return TestClient(app)


def test_create_analysis_and_fetch_registries(client):
    resp = client.post(
        "/api/v1/analyses",
        json={
            "query": "solid state battery",
            "data_mode": "CACHE",
            "score_profile_id": "ABCDE_v1",
            "snapshot_id": "ft_bench_v1",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "COMPLETED"
    run_id = body["run_id"]
    docs = client.get(f"/api/v1/analyses/{run_id}/documents")
    assert docs.status_code == 200
    assert len(docs.json()["documents"]) >= 1
    cands = client.get(f"/api/v1/analyses/{run_id}/candidates", params={"state": "all"})
    assert cands.status_code == 200
    top = client.get(f"/api/v1/analyses/{run_id}/registries/top15")
    assert top.status_code == 200
    method = client.get("/api/v1/methodology/runtime")
    assert method.json()["score_profile_id"] == "ABCDE_v1"


def test_refresh_requires_postgres_engine(client):
    resp = client.post("/api/v1/refresh", json={"query": "test query"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "PERSISTENCE_UNAVAILABLE"


def test_analysis_fails_closed_without_repository():
    app = create_app(engine=None)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/analyses",
        json={
            "query": "x",
            "data_mode": "CACHE",
            "score_profile_id": "ABCDE_v1",
            "snapshot_id": "ft_bench_v1",
        },
    )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "PERSISTENCE_UNAVAILABLE"
