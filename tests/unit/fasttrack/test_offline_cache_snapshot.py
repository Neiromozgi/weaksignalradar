"""CACHE/SNAPSHOT offline demo: zero external source and LLM provider calls."""

from __future__ import annotations

from pathlib import Path

import pytest

from weaksignalradar.fasttrack.db.repository import MemoryRunRepository
from weaksignalradar.fasttrack.discovery_v2.llm_run_budget import clear_run_llm_budget
from weaksignalradar.fasttrack.discovery_v2.tmf_extract import (
    provider_calls_made,
    reset_provider_call_counter,
)
from weaksignalradar.fasttrack.pipeline.run_context import clear_run_data_mode
from weaksignalradar.fasttrack.pipeline.runner import start_analysis

_PKG = Path(__file__).resolve().parents[3] / "src"
FIXTURE_LLM_CACHE = _PKG / "weaksignalradar" / "fasttrack" / "fixtures" / "llm_cache"


@pytest.fixture(autouse=True)
def _deterministic_embedding(monkeypatch):
    monkeypatch.setenv("WSR_EMBEDDING_BACKEND", "deterministic")
    monkeypatch.setenv("DISCOVERY_V2_ENABLED", "true")
    monkeypatch.setenv("WSR_LLM_CACHE_DIR", str(FIXTURE_LLM_CACHE))


@pytest.fixture(autouse=True)
def _db_ready(monkeypatch):
    monkeypatch.setattr(
        "weaksignalradar.fasttrack.persistence_guard.check_db_ready",
        lambda _eng: True,
    )


@pytest.fixture(autouse=True)
def _reset_run_context():
    reset_provider_call_counter()
    clear_run_llm_budget()
    clear_run_data_mode()
    yield
    reset_provider_call_counter()
    clear_run_llm_budget()
    clear_run_data_mode()


@pytest.fixture
def memory_repo():
    return MemoryRunRepository()


def _external_calls_total(source_runs: list) -> int:
    return sum(int(sr.get("external_calls") or 0) for sr in source_runs)


def test_cache_run_zero_external_and_llm_provider_calls(monkeypatch, memory_repo):
    monkeypatch.setenv("WSR_ALLOW_LLM_PROVIDER", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-should-not-be-used-in-cache")
    state = start_analysis(
        query="solid state battery",
        data_mode="CACHE",
        score_profile_id="ABCDE_v1",
        snapshot_id="ft_bench_v1",
        repository=memory_repo,
    )
    assert state.status in ("COMPLETED", "PARTIAL")
    assert _external_calls_total(state.source_runs) == 0
    assert int(state.coverage_summary.get("external_calls") or 0) == 0
    diag = state.provenance.get("llm_diagnostics") or {}
    assert diag.get("llm_provider_calls") == 0
    assert state.provenance.get("tmf_provider_calls") == 0
    assert provider_calls_made() == 0
    assert state.provenance.get("offline_replay") is True
    assert state.candidates, "offline CACHE demo must expose stored candidates"


def test_snapshot_run_zero_llm_provider_calls(monkeypatch, memory_repo):
    monkeypatch.setenv("WSR_ALLOW_LLM_PROVIDER", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-should-not-be-used-in-snapshot")
    state = start_analysis(
        query="quantum photonic",
        data_mode="SNAPSHOT",
        score_profile_id="ABCDE_v1",
        snapshot_id="ft_bench_v1",
        repository=memory_repo,
    )
    assert state.status in ("COMPLETED", "PARTIAL")
    assert _external_calls_total(state.source_runs) == 0
    diag = state.provenance.get("llm_diagnostics") or {}
    assert diag.get("llm_provider_calls") == 0
    assert state.provenance.get("tmf_provider_calls") == 0
    assert state.candidates
