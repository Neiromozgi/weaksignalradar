"""CORE LIVE QUALITY tranche 1 — normalization, clustering, LLM diag, EPO errors."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import httpx
import pytest

from weaksignalradar.discovery.contracts import (
    CoverageStatus,
    SourceDocument,
    SourceSearchResult,
)
from weaksignalradar.fasttrack.db.repository import MemoryRunRepository
from weaksignalradar.fasttrack.embedding.backend import DeterministicTestBackend, EmbeddingBackend
from weaksignalradar.fasttrack.llm.base import LLMAdapter, TechnicalSignature
from weaksignalradar.fasttrack.pipeline.candidates import discover_candidates
from weaksignalradar.fasttrack.pipeline.embedding_cluster import _is_generic_label
from weaksignalradar.fasttrack.pipeline.llm_diagnostics import (
    LLMDiagnostics,
    provenance_has_secret_material,
)
from weaksignalradar.fasttrack.pipeline.runner import start_analysis
from weaksignalradar.fasttrack.sources.contract import (
    CoverageState,
    NormalizedSourceDocument,
    OriginalAvailability,
)
from weaksignalradar.fasttrack.sources.epo_lod import EpoLodAdapter
from weaksignalradar.fasttrack.sources.openalex_ft import OpenAlexFastTrackAdapter
from weaksignalradar.fasttrack.sources.openalex_normalize import (
    collect_organization_names,
    normalize_openalex_work,
    reconstruct_abstract,
)
from weaksignalradar.fasttrack.sources.sparql import run_sparql


@pytest.fixture(autouse=True)
def _deterministic_embedding(monkeypatch):
    monkeypatch.setenv("WSR_EMBEDDING_BACKEND", "deterministic")


@pytest.fixture(autouse=True)
def _discovery_v1_only(monkeypatch):
    monkeypatch.delenv("DISCOVERY_V2_ENABLED", raising=False)


# --- TEST-A ---


def test_a1_openalex_abstract_reconstruction():
    work = {
        "id": "https://openalex.org/W1",
        "title": "Sample",
        "abstract_inverted_index": {"Hello": [0], "world": [1]},
    }
    doc = normalize_openalex_work(work, snapshot_id="snap_test")
    assert doc.abstract == "Hello world"


def test_a2_openalex_institutions_preserved():
    work = {
        "id": "https://openalex.org/W2",
        "title": "Sample",
        "authorships": [
            {
                "institutions": [
                    {"display_name": "Org A"},
                    {"display_name": "Org B"},
                ]
            },
            {"institutions": [{"display_name": "Org A"}]},
        ],
    }
    assert collect_organization_names(work) == ["Org A", "Org B"]
    doc = normalize_openalex_work(work, snapshot_id="snap_test")
    assert doc.organization_names == ["Org A", "Org B"]


def test_a3_live_and_fixture_normalization_parity(tmp_path):
    work = {
        "id": "https://openalex.org/W3",
        "title": "Fintech risk analytics",
        "publication_year": 2022,
        "abstract_inverted_index": {"Risk": [0], "analytics": [1]},
        "authorships": [{"institutions": [{"display_name": "Fin Lab"}]}],
        "primary_location": {"landing_page_url": "https://example.org/w3"},
    }
    fixture_doc = normalize_openalex_work(work, snapshot_id="bench")
    snap = tmp_path / "page.json"
    snap.write_text(json.dumps({"results": [work]}), encoding="utf-8")
    adapter = OpenAlexFastTrackAdapter(adapter=MagicMock())
    retrieved = datetime.now(UTC)
    mock_result = SourceSearchResult(
        run_id="run_test",
        documents=[
            SourceDocument(
                source_id="openalex:https://openalex.org/W3",
                run_id="run_test",
                origin_url_or_official_id="https://openalex.org/W3",
                title=work["title"],
                retrieved_at=retrieved,
                request_params={},
                content_hash="abc",
                snapshot_pointer=str(snap),
                source_type="scholarly_work",
                coverage=CoverageStatus.SEARCHED_OK,
                primary_origin_id="https://openalex.org/W3",
            )
        ],
        next_cursor=None,
        coverage=CoverageStatus.SEARCHED_OK,
        error=None,
    )
    adapter._adapter.search = MagicMock(return_value=mock_result)
    batch = adapter.search_live("fintech", 5, run_id="run_test")
    live_doc = batch.documents[0]
    assert live_doc.abstract == fixture_doc.abstract
    assert live_doc.organization_names == fixture_doc.organization_names
    assert live_doc.title == fixture_doc.title


def test_a4_missing_abstract_none():
    doc = normalize_openalex_work({"id": "W", "title": "T"}, snapshot_id="s")
    assert doc.abstract is None


def test_a5_missing_organizations_empty():
    doc = normalize_openalex_work({"id": "W", "title": "T"}, snapshot_id="s")
    assert doc.organization_names == []


@pytest.mark.parametrize(
    ("inverted", "expected"),
    [
        ({"Hello": [0], "world": [1]}, "Hello world"),
        ({"Hello": ["0"], "world": ["1"]}, "Hello world"),
        (None, None),
        ({}, None),
        ({"only": ["not-a-number"]}, None),
        ({"a": [0], "b": ["1", "bad", None]}, "a b"),
    ],
)
def test_a6_abstract_reconstruction_hardening(inverted, expected):
    assert reconstruct_abstract(inverted) == expected
    work = {"id": "W", "title": "T", "abstract_inverted_index": inverted}
    doc = normalize_openalex_work(work, snapshot_id="s")
    assert doc.abstract == expected


# --- TEST-D ---


def test_d1_organization_count_unique_union():
    docs = [
        NormalizedSourceDocument(
            source_document_id="d1",
            source_id="s1",
            source_type="openalex_work",
            stable_external_id="e1",
            title="A",
            year=2020,
            canonical_url="u",
            original_availability_status=OriginalAvailability.METADATA_ONLY,
            metadata_json={},
            source_snapshot_id="snap",
            retrieved_at="t",
            content_hash_of_api_record="h",
            coverage_state=CoverageState.FOUND,
            organization_names=["Org A", "Org B"],
        ),
        NormalizedSourceDocument(
            source_document_id="d2",
            source_id="s2",
            source_type="openalex_work",
            stable_external_id="e2",
            title="B",
            year=2021,
            canonical_url="u",
            original_availability_status=OriginalAvailability.METADATA_ONLY,
            metadata_json={},
            source_snapshot_id="snap",
            retrieved_at="t",
            content_hash_of_api_record="h2",
            coverage_state=CoverageState.FOUND,
            organization_names=["Org A"],
        ),
    ]

    class SameVecBackend(EmbeddingBackend):
        profile = DeterministicTestBackend.profile

        def encode(self, texts: list[str]) -> list[list[float]]:
            vec = DeterministicTestBackend().encode(["passage: same"])[0]
            return [vec for _ in texts]

    cands, _, _ = discover_candidates(docs, domain_id="d", backend=SameVecBackend())
    assert len(cands) == 1
    assert cands[0]["organization_count"] == 2


# --- TEST-B ---


def _synthetic_doc(i: int, topic: str, org: str) -> NormalizedSourceDocument:
    title = f"{topic} system design study number {i}"
    return NormalizedSourceDocument(
        source_document_id=f"d{i}",
        source_id=f"s{i}",
        source_type="openalex_work",
        stable_external_id=f"ext{i}",
        title=title,
        year=2020 + (i % 5),
        canonical_url="u",
        original_availability_status=OriginalAvailability.ABSTRACT_AVAILABLE,
        metadata_json={},
        source_snapshot_id="snap",
        retrieved_at="t",
        content_hash_of_api_record=f"h{i}",
        coverage_state=CoverageState.FOUND,
        abstract=f"Abstract about {topic} innovation {i}",
        organization_names=[org],
    )


def test_b1_fewer_candidates_than_documents():
    topics = ["quantum mesh", "quantum mesh", "solid battery", "solid battery", "edge ai"]
    docs = []
    for i in range(20):
        docs.append(_synthetic_doc(i, topics[i % len(topics)], f"Org{i % 4}"))

    class TopicBackend(EmbeddingBackend):
        profile = DeterministicTestBackend.profile

        def encode(self, texts: list[str]) -> list[list[float]]:
            out = []
            for t in texts:
                key = "quantum" if "quantum" in t else "battery" if "battery" in t else "edge"
                out.append(DeterministicTestBackend().encode([f"passage: {key}"])[0])
            return out

    cands, method, _ = discover_candidates(docs, domain_id="d", backend=TopicBackend())
    assert method == "embedding_cluster_v1"
    assert len(cands) < len(docs)


def test_b1b_thirty_orthogonal_vectors_stay_thirty_clusters():
    docs = [_synthetic_doc(i, f"isolated topic {i}", f"Org{i}") for i in range(30)]

    class OrthogonalBackend(EmbeddingBackend):
        profile = DeterministicTestBackend.profile

        def encode(self, texts: list[str]) -> list[list[float]]:
            dim = self.profile.vector_dimension
            vectors: list[list[float]] = []
            for i, _ in enumerate(texts):
                vec = [0.0] * dim
                vec[i] = 1.0
                vectors.append(vec)
            return vectors

    cands, _, meta = discover_candidates(docs, domain_id="d", backend=OrthogonalBackend())
    assert len(cands) == 30
    assert meta["candidate_cap_exceeded"] is True
    assert meta["cluster_count"] == 30


def test_b2_clusters_stable_for_identical_input():
    docs = [_synthetic_doc(i, "quantum mesh", "Org1") for i in range(8)]

    class TopicBackend(EmbeddingBackend):
        profile = DeterministicTestBackend.profile

        def encode(self, texts: list[str]) -> list[list[float]]:
            vec = DeterministicTestBackend().encode(["passage: quantum"])[0]
            return [vec for _ in texts]

    a, _, _ = discover_candidates(docs, domain_id="d", backend=TopicBackend())
    b, _, _ = discover_candidates(docs, domain_id="d", backend=TopicBackend())
    assert [c["candidate_id"] for c in a] == [c["candidate_id"] for c in b]


def test_b3_no_generic_single_token_names():
    for bad in ("Регулирования", "Development", "Цифровизации"):
        assert _is_generic_label(bad)
    assert not _is_generic_label("Quantum photonic mesh networks")


def test_b4_ft_bench_v1_regression():
    repo = MemoryRunRepository()
    state = start_analysis(
        query="quantum photonic",
        data_mode="SNAPSHOT",
        score_profile_id="ABCDE_v1",
        snapshot_id="ft_bench_v1",
        repository=repo,
    )
    assert state.status == "COMPLETED"
    assert state.provenance.get("discovery_method") == "embedding_cluster_v1"
    assert len(state.candidates) >= 1


def test_b5_empty_abstract_does_not_crash_clustering():
    docs = [
        NormalizedSourceDocument(
            source_document_id="d1",
            source_id="s1",
            source_type="openalex_work",
            stable_external_id="e1",
            title="Title only work",
            year=2022,
            canonical_url="u",
            original_availability_status=OriginalAvailability.METADATA_ONLY,
            metadata_json={},
            source_snapshot_id="snap",
            retrieved_at="t",
            content_hash_of_api_record="h",
            coverage_state=CoverageState.FOUND,
            abstract=None,
        )
    ]
    cands, _, _ = discover_candidates(docs, domain_id="d", backend=DeterministicTestBackend())
    assert len(cands) == 1


def test_b6_embedding_unavailable_no_fallback(monkeypatch):
    monkeypatch.setenv("WSR_EMBEDDING_BACKEND", "disabled")
    cands, _, meta = discover_candidates(
        [_synthetic_doc(0, "topic", "Org")],
        domain_id="d",
        backend=None,
    )
    assert cands == []
    assert meta["discovery_status"] == "EMBEDDING_UNAVAILABLE"


def test_b7_pipeline_embedding_unavailable_degraded(monkeypatch):
    monkeypatch.setenv("WSR_EMBEDDING_BACKEND", "disabled")
    repo = MemoryRunRepository()
    state = start_analysis(
        query="quantum photonic",
        data_mode="SNAPSHOT",
        score_profile_id="ABCDE_v1",
        snapshot_id="ft_bench_v1",
        repository=repo,
    )
    assert state.status == "COMPLETED"
    assert state.provenance.get("discovery_status") == "EMBEDDING_UNAVAILABLE"
    assert state.candidates == []


# --- TEST-H ---


class _StubLLM(LLMAdapter):
    def __init__(self, statuses: list[str]) -> None:
        self._statuses = statuses
        self.calls = 0

    def extract_signature(
        self, *, candidate_name: str, evidence_texts: list[str]
    ) -> TechnicalSignature:
        del candidate_name, evidence_texts
        status = self._statuses[min(self.calls, len(self._statuses) - 1)]
        self.calls += 1
        return TechnicalSignature(
            object_class=None,
            function=None,
            mechanism=None,
            architecture_or_process=None,
            key_technical_property=None,
            extraction_status=status,
            evidence_span_refs=[],
            llm_model_id="stub",
            prompt_version="v1",
            validation_status="PASSED" if status == "OK" else "SKIPPED",
        )


def test_h1_llm_aggregate_diagnostics():
    diag = LLMDiagnostics()
    diag.begin_candidate()
    diag.begin_provider_call()
    sig_ok = TechnicalSignature(
        object_class=None,
        function=None,
        mechanism=None,
        architecture_or_process=None,
        key_technical_property=None,
        extraction_status="OK",
        evidence_span_refs=[],
        llm_model_id="m",
        prompt_version="v1",
    )
    diag.finish_provider_call(sig_ok)
    diag.begin_candidate()
    diag.mark_replay(sig_ok)
    diag.begin_candidate()
    diag.begin_provider_call()
    diag.finish_provider_call(
        TechnicalSignature(
            object_class=None,
            function=None,
            mechanism=None,
            architecture_or_process=None,
            key_technical_property=None,
            extraction_status="NOT_CONFIGURED",
            evidence_span_refs=[],
            llm_model_id=None,
            prompt_version="v1",
        )
    )
    d = diag.as_dict()
    assert d["llm_candidates_attempted"] == 3
    assert d["llm_provider_calls"] == 2
    assert d["llm_replayed"] == 1
    assert d["llm_ok"] == 2
    assert d["llm_not_configured"] == 1


def test_h2_no_secret_material_in_provenance():
    prov = {
        "llm_diagnostics": LLMDiagnostics().as_dict(),
        "discovery_method": "embedding_cluster_v1",
    }
    assert not provenance_has_secret_material(prov)


# --- TEST-I ---


def test_i1_epo_timeout_partial_with_error(monkeypatch):
    monkeypatch.delenv("EPO_LIVE_DISABLED", raising=False)

    def _timeout(endpoint, query, **kwargs):
        del endpoint, query, kwargs
        from weaksignalradar.fasttrack.sources.sparql import SparqlResult

        return SparqlResult(bindings=[], ok=False, error="timeout")

    monkeypatch.setattr("weaksignalradar.fasttrack.sources.epo_lod.run_sparql", _timeout)
    batch = EpoLodAdapter().search("battery technology", budget_remaining=1)
    assert batch.coverage_state.value == "PARTIAL"
    assert batch.error == "timeout"


def test_i2_epo_http_error_code_persisted(monkeypatch):
    monkeypatch.delenv("EPO_LIVE_DISABLED", raising=False)
    from weaksignalradar.fasttrack.sources.sparql import SparqlResult

    monkeypatch.setattr(
        "weaksignalradar.fasttrack.sources.epo_lod.run_sparql",
        lambda *a, **k: SparqlResult(bindings=[], ok=False, error="http_503"),
    )
    batch = EpoLodAdapter().search("battery", budget_remaining=1)
    assert batch.coverage_state.value == "SEARCH_ERROR"
    assert batch.error == "http_503"


def test_sparql_http_503_classification():
    class FakeClient:
        def post(self, *args, **kwargs):
            del args, kwargs
            return httpx.Response(503, request=httpx.Request("POST", "http://example"))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            del args

    result = run_sparql("http://example", "SELECT * WHERE {}", client=FakeClient())
    assert result.error == "http_503"
