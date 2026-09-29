"""Provider cache manifest for LIVE #2 fixture."""

from __future__ import annotations

from pathlib import Path

from weaksignalradar.fasttrack.corpus.snapshot_loader import load_openalex_works
from weaksignalradar.fasttrack.discovery_v2.provider_cache_manifest import (
    LIVE2_FIXTURE_ID,
    load_provider_cache_manifest,
    manifest_path,
)
from weaksignalradar.fasttrack.sources.openalex_ft import OpenAlexFastTrackAdapter

_PKG = Path(__file__).resolve().parents[3] / "src"
FIXTURE_LLM_CACHE = _PKG / "weaksignalradar" / "fasttrack" / "fixtures" / "llm_cache"


def test_live2_manifest_has_75_documents(monkeypatch):
    monkeypatch.setenv("WSR_LLM_CACHE_DIR", str(FIXTURE_LLM_CACHE))
    manifest = load_provider_cache_manifest()
    assert manifest is not None
    assert manifest.get("fixture_id") == LIVE2_FIXTURE_ID
    assert manifest.get("document_count") == 75
    docs = manifest.get("documents") or []
    assert len(docs) == 75
    statuses = {row.get("provider_status") for row in docs if isinstance(row, dict)}
    assert "PROVIDER_OK_EMPTY" in statuses
    assert "PROVIDER_OK_FRAMES" in statuses
    empty_rows = [r for r in docs if r.get("provider_status") == "PROVIDER_OK_EMPTY"]
    assert len(empty_rows) >= 50
    assert manifest_path().is_file()


def test_manifest_doc_ids_match_fixture_registry(monkeypatch):
    monkeypatch.setenv("WSR_LLM_CACHE_DIR", str(FIXTURE_LLM_CACHE))
    works = load_openalex_works("live2_replay_v1")
    fixture_docs = OpenAlexFastTrackAdapter().search_from_fixture(
        works, snapshot_id="live2_replay_v1"
    ).documents
    manifest = load_provider_cache_manifest()
    assert manifest is not None
    ids = {row["doc_id"] for row in manifest["documents"]}
    assert ids == {d.source_document_id for d in fixture_docs}
