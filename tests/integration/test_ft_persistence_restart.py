"""Persistence survives repository/backend re-instantiation (addendum v1.0.2)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine


def _host_database_url() -> str | None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    return url.replace("@db:", "@127.0.0.1:")


pytestmark = pytest.mark.skipif(
    _host_database_url() is None,
    reason="DATABASE_URL not set",
)


@pytest.fixture
def pg_engine():
    from alembic import command
    from alembic.config import Config

    url = _host_database_url()
    assert url is not None
    os.environ["DATABASE_URL"] = url
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    return create_engine(url, pool_pre_ping=True)


def test_run_survives_new_repository_instance(pg_engine):
    from weaksignalradar.api.app import create_app
    from weaksignalradar.fasttrack.db.repository import PostgresRunRepository

    app1 = create_app(engine=pg_engine)
    client1 = TestClient(app1)
    resp = client1.post(
        "/api/v1/analyses",
        json={
            "query": "quantum photonic",
            "data_mode": "CACHE",
            "score_profile_id": "ABCDE_v1",
            "snapshot_id": "ft_bench_v1",
        },
    )
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    repo2 = PostgresRunRepository(pg_engine)
    restored = repo2.get(run_id)
    assert restored is not None
    assert restored.run_id == run_id
    assert len(restored.documents) >= 1
    assert restored.candidates

    app2 = create_app(engine=pg_engine)
    client2 = TestClient(app2)
    get_resp = client2.get(f"/api/v1/analyses/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["run_id"] == run_id
    assert get_resp.json()["registries"]
