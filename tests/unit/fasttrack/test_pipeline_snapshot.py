import pytest

from weaksignalradar.fasttrack.db.repository import MemoryRunRepository
from weaksignalradar.fasttrack.pipeline.runner import start_analysis


@pytest.fixture(autouse=True)
def _deterministic_embedding(monkeypatch):
    monkeypatch.setenv("WSR_EMBEDDING_BACKEND", "deterministic")


def test_snapshot_pipeline_produces_documents_and_registries():
    repo = MemoryRunRepository()
    state = start_analysis(
        query="quantum photonic",
        data_mode="SNAPSHOT",
        score_profile_id="ABCDE_v1",
        snapshot_id="ft_bench_v1",
        repository=repo,
    )
    assert state.status == "COMPLETED"
    assert len(state.documents) >= 10
    assert len(state.candidates) >= 1
    assert "TOP15" in state.registries
    reloaded = repo.get(state.run_id)
    assert reloaded is not None
    assert reloaded.provenance.get("embedding_profile_id") == "e5_small_v1"
