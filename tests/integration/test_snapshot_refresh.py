"""LIVE refresh registers new immutable snapshots (DEFECT-SNAPSHOT-001)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from weaksignalradar.fasttrack.db import models as m
from weaksignalradar.fasttrack.sources.contract import (
    CoverageState,
    NormalizedSourceDocument,
    OriginalAvailability,
    SourceBatch,
)
from weaksignalradar.fasttrack.sources.openalex_ft import OpenAlexLiveResult


def _host_database_url() -> str | None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    return url.replace("@db:", "@127.0.0.1:")


pytestmark = pytest.mark.skipif(
    _host_database_url() is None,
    reason="DATABASE_URL not set",
)


def _sample_doc(snapshot_id: str) -> NormalizedSourceDocument:
    return NormalizedSourceDocument(
        source_document_id="doc_snap_test_1",
        source_id="https://openalex.org/W999",
        source_type="openalex_work",
        stable_external_id="https://openalex.org/W999",
        title="Quantum photonic mesh",
        year=2024,
        canonical_url="https://example.org/w999",
        original_availability_status=OriginalAvailability.METADATA_ONLY,
        metadata_json={},
        source_snapshot_id="pending",
        retrieved_at="2026-01-01T00:00:00+00:00",
        content_hash_of_api_record="abc",
        coverage_state=CoverageState.FOUND,
        abstract="Quantum photonic mesh networks enable novel architectures.",
    )


@pytest.fixture
def pg_client(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config

    from weaksignalradar.api.app import create_app

    url = _host_database_url()
    assert url is not None
    os.environ["DATABASE_URL"] = url
    snap_dir = tmp_path / "snapshots"
    monkeypatch.setenv("SNAPSHOT_DIR", str(snap_dir))
    monkeypatch.setenv("WSR_EMBEDDING_BACKEND", "deterministic")
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    engine = create_engine(url, pool_pre_ping=True)
    app = create_app(engine=engine)
    return TestClient(app), engine, snap_dir


def test_refresh_creates_new_snapshot_and_replay_zero_calls(pg_client):
    client, engine, _snap_dir = pg_client
    live_result = OpenAlexLiveResult(
        documents=[_sample_doc("pending")],
        coverage_state=CoverageState.FOUND,
        calls_used=1,
        pages=1,
        cap_reached=False,
        elapsed_sec=0.1,
    )
    before = client.get("/api/v1/snapshots").json()["snapshots"]
    before_ids = {s["snapshot_id"] for s in before}

    with patch(
        "weaksignalradar.fasttrack.pipeline.runner.OpenAlexFastTrackAdapter.search_live_bounded",
        return_value=live_result,
    ):
        empty = SourceBatch(documents=[], coverage_state=CoverageState.SEARCHED_OK, calls_used=0)
        with patch(
            "weaksignalradar.fasttrack.pipeline.runner.CordisAdapter.search",
            return_value=empty,
        ):
            with patch(
                "weaksignalradar.fasttrack.pipeline.runner.EpoLodAdapter.search",
                return_value=empty,
            ):
                refresh = client.post("/api/v1/refresh", json={"query": "quantum photonic"})
    assert refresh.status_code == 200
    body = refresh.json()
    assert body.get("snapshot_id")
    snap_id = body["snapshot_id"]
    assert snap_id not in before_ids
    assert snap_id != "ft_bench_v1"

    after = client.get("/api/v1/snapshots").json()["snapshots"]
    assert len(after) == len(before) + 1

    with patch(
        "weaksignalradar.fasttrack.pipeline.runner.OpenAlexFastTrackAdapter.search_live_bounded",
    ) as live_mock:
        analysis = client.post(
            "/api/v1/analyses",
            json={
                "query": "quantum photonic",
                "data_mode": "SNAPSHOT",
                "score_profile_id": "ABCDE_v1",
                "snapshot_id": snap_id,
            },
        )
        live_mock.assert_not_called()
    assert analysis.status_code == 200
    assert analysis.json()["status"] == "COMPLETED"

    with engine.connect() as conn:
        row = conn.execute(
            select(m.FtSnapshotRow).where(m.FtSnapshotRow.snapshot_id == snap_id)
        ).first()
        assert row is not None
