"""Tranche 2 correction tests — Discovery v2 gates T1–T15."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from weaksignalradar.fasttrack.corpus.snapshot_loader import load_openalex_works
from weaksignalradar.fasttrack.db.repository import MemoryRunRepository
from weaksignalradar.fasttrack.discovery_v2.llm_cache import cache_key, save_cached_json
from weaksignalradar.fasttrack.discovery_v2.pipeline import discover_candidates_v2
from weaksignalradar.fasttrack.discovery_v2.semantic_non_technology import (
    reject_technology_mechanism_label,
)
from weaksignalradar.fasttrack.discovery_v2.text_norm import normalize_text, span_in_source
from weaksignalradar.fasttrack.discovery_v2.tmf_extract import extract_tmfs
from weaksignalradar.fasttrack.discovery_v2.tmf_types import TMF_PROMPT_VERSION
from weaksignalradar.fasttrack.discovery_v2.tmf_validator import validate_frame
from weaksignalradar.fasttrack.embedding.backend import (
    DeterministicTestBackend,
    EmbeddingBackend,
    get_embedding_backend,
)
from weaksignalradar.fasttrack.llm.profile import LLM_MODEL
from weaksignalradar.fasttrack.pipeline.runner import start_analysis
from weaksignalradar.fasttrack.sources.contract import (
    CoverageState,
    NormalizedSourceDocument,
    OriginalAvailability,
)
from weaksignalradar.fasttrack.sources.openalex_ft import OpenAlexFastTrackAdapter

_PKG = Path(__file__).resolve().parents[3] / "src"
FIXTURE_LLM_CACHE = _PKG / "weaksignalradar" / "fasttrack" / "fixtures" / "llm_cache"


@pytest.fixture(autouse=True)
def _v2_env(monkeypatch):
    monkeypatch.setenv("WSR_EMBEDDING_BACKEND", "deterministic")
    monkeypatch.setenv("DISCOVERY_V2_ENABLED", "true")
    monkeypatch.setenv("WSR_LLM_CACHE_DIR", str(FIXTURE_LLM_CACHE))
    monkeypatch.delenv("WSR_ALLOW_LLM_PROVIDER", raising=False)


def _doc(
    *,
    doc_id: str,
    title: str,
    abstract: str,
    year: int = 2024,
) -> NormalizedSourceDocument:
    return NormalizedSourceDocument(
        source_document_id=doc_id,
        source_id=f"openalex:{doc_id}",
        source_type="openalex_work",
        stable_external_id=f"https://openalex.org/{doc_id}",
        title=title,
        year=year,
        canonical_url=f"https://openalex.org/{doc_id}",
        doi=None,
        original_availability_status=OriginalAvailability.ABSTRACT_AVAILABLE,
        metadata_json={},
        source_snapshot_id="test",
        retrieved_at="2026-01-01T00:00:00+00:00",
        content_hash_of_api_record=hashlib.sha256(title.encode()).hexdigest(),
        coverage_state=CoverageState.FOUND,
        organization_names=["Org A", "Org B", "Org C"],
        abstract=abstract,
    )


def _seed_frames(doc: NormalizedSourceDocument, frames: list[dict]) -> None:
    norm = normalize_text(f"{doc.title}\n{doc.abstract or ''}")
    key = cache_key(
        model_id=LLM_MODEL,
        prompt_version=TMF_PROMPT_VERSION,
        normalized_input=norm,
    )
    save_cached_json(key, {"frames": frames, "prompt_version": TMF_PROMPT_VERSION})


def _live2_docs() -> list[NormalizedSourceDocument]:
    works = load_openalex_works("live2_replay_v1")
    return OpenAlexFastTrackAdapter().search_from_fixture(
        works, snapshot_id="live2_replay_v1"
    ).documents


def test_t2_span_grounding_all_accepted_tmfs():
    docs = _live2_docs()
    frames, stats, _ = extract_tmfs(docs)
    assert stats.frames_kept == len(frames)
    for frame in frames:
        doc = next(d for d in docs if d.source_document_id == frame.doc_id)
        assert span_in_source(frame.evidence_span, doc.title, doc.abstract)


def test_t3_macro_negative_control_zero_technology_candidates():
    macro_docs = [
        _doc(
            doc_id="m1",
            title="Financial market development policy",
            abstract=(
                "This paper discusses market regulation and sector digitalization policy "
                "for national economy transformation without technical systems."
            ),
        ),
        _doc(
            doc_id="m2",
            title="Sector ecosystem transformation",
            abstract=(
                "We review economy-wide ecosystem development and regulation trends "
                "in the financial sector and public policy frameworks."
            ),
        ),
    ]
    for d in macro_docs:
        _seed_frames(
            d,
            [
                {
                    "mechanism": "market regulation sector",
                    "object": None,
                    "function": None,
                    "evidence_span": d.abstract,
                    "label": "MACRO_THEME",
                }
            ],
        )
    backend = get_embedding_backend(allow_none=True)
    cands, _, _ = discover_candidates_v2(macro_docs, domain_id="t", backend=backend)
    assert cands == []


def test_t5_no_mega_cluster_on_live2_fixture():
    docs = _live2_docs()
    backend = get_embedding_backend(allow_none=True)
    cands, _, prov = discover_candidates_v2(docs, domain_id="t", backend=backend)
    corpus = len(docs)
    for c in cands:
        assert c["document_count"] / corpus <= 0.25
    assert float(prov.get("largest_cluster_doc_share") or 0) <= 0.25


def test_t7_t8_determinism_and_order_invariance():
    docs = _live2_docs()
    backend = get_embedding_backend(allow_none=True)
    a, _, _ = discover_candidates_v2(docs, domain_id="t", backend=backend)
    b, _, _ = discover_candidates_v2(docs, domain_id="t", backend=backend)
    assert {c["candidate_id"] for c in a} == {c["candidate_id"] for c in b}
    shuffled = list(reversed(docs))
    c, _, _ = discover_candidates_v2(shuffled, domain_id="t", backend=backend)
    assert {x["candidate_id"] for x in a} == {x["candidate_id"] for x in c}


def test_t10_live2_replay_honest_discovery():
    repo = MemoryRunRepository()
    state = start_analysis(
        query="Финтех",
        data_mode="SNAPSHOT",
        score_profile_id="ABCDE_v1",
        snapshot_id="live2_replay_v1",
        repository=repo,
    )
    assert state.status == "COMPLETED"
    assert state.provenance.get("discovery_version") == "v2"
    for c in state.candidates:
        assert "conceptual model" not in c.canonical_name.lower()
    status = state.provenance.get("discovery_status")
    assert status in {
        "DISCOVERY_OK",
        "RETRIEVAL_INSUFFICIENT",
        "NO_TECHNICAL_FRAMES",
    }


def test_t11_decision_explanation_present():
    repo = MemoryRunRepository()
    state = start_analysis(
        query="Финтех",
        data_mode="SNAPSHOT",
        score_profile_id="ABCDE_v1",
        snapshot_id="live2_replay_v1",
        repository=repo,
    )
    for c in state.candidates:
        assert c.decision_explanation is not None


def test_t1_frozen_methodology_regression_v1_path(monkeypatch):
    monkeypatch.setenv("DISCOVERY_V2_ENABLED", "false")
    repo = MemoryRunRepository()
    state = start_analysis(
        query="quantum photonic",
        data_mode="SNAPSHOT",
        score_profile_id="ABCDE_v1",
        snapshot_id="ft_bench_v1",
        repository=repo,
    )
    assert state.provenance.get("discovery_method") == "embedding_cluster_v1"


def test_t14_generic_semantic_false_positive(monkeypatch, tmp_path):
    monkeypatch.setenv("WSR_LLM_CACHE_DIR", str(tmp_path))
    span = (
        "A conceptual model of the relationship between the level of maturity "
        "and market outcomes in the sector."
    )
    doc = _doc(doc_id="fp1", title="Framework paper", abstract=span)
    _seed_frames(
        doc,
        [
            {
                "mechanism": "conceptual model of the relationship",
                "object": None,
                "function": None,
                "evidence_span": span,
                "label": "TECHNOLOGY_MECHANISM",
            }
        ],
    )
    assert reject_technology_mechanism_label(
        mechanism="conceptual model of the relationship", evidence_span=span
    )
    backend = get_embedding_backend(allow_none=True)
    cands, _, _ = discover_candidates_v2([doc], domain_id="t", backend=backend)
    assert cands == []


def test_t15_paraphrase_clustering(monkeypatch, tmp_path):
    monkeypatch.setenv("WSR_LLM_CACHE_DIR", str(tmp_path))
    mech_a_spans = [
        "The waveguide coupling interferometer measures phase drift in photonic lanes.",
        "An interferometric waveguide coupler senses optical phase drift in the lane.",
        "Phase drift in photonic waveguides is tracked via a coupling interferometer design.",
        "We built a waveguide interferometer coupler for distributed phase monitoring.",
        "Coupled waveguide interferometry reports phase drift across photonic paths.",
    ]
    mech_b_spans = [
        "A photonic bandgap filter isolates the target wavelength channel.",
        "Bandgap-engineered photonic filters suppress out-of-band leakage.",
        "We fabricate photonic crystal bandgap filters for channel isolation.",
    ]
    noise = [
        "Sector policy drives digital transformation across regional markets and ecosystems.",
        "Market development frameworks assess economic relationships without hardware detail.",
    ]
    docs: list[NormalizedSourceDocument] = []
    mech_a_labels = [
        "waveguide coupling interferometer",
        "interferometric waveguide coupler",
        "coupling interferometer waveguide design",
        "waveguide interferometer coupler",
        "coupled waveguide interferometry",
    ]
    for i, sent in enumerate(mech_a_spans):
        d = _doc(doc_id=f"a{i}", title=f"Photonic study A{i}", abstract=sent)
        _seed_frames(
            d,
            [
                {
                    "mechanism": mech_a_labels[i],
                    "object": "phase drift",
                    "function": "measurement",
                    "evidence_span": sent,
                    "label": "TECHNOLOGY_MECHANISM",
                }
            ],
        )
        docs.append(d)
    for i, sent in enumerate(mech_b_spans):
        d = _doc(doc_id=f"b{i}", title=f"Filter study B{i}", abstract=sent)
        _seed_frames(
            d,
            [
                {
                    "mechanism": "photonic bandgap filter",
                    "object": "wavelength channel",
                    "function": "isolation",
                    "evidence_span": sent,
                    "label": "TECHNOLOGY_MECHANISM",
                }
            ],
        )
        docs.append(d)
    for i, sent in enumerate(noise):
        d = _doc(doc_id=f"n{i}", title=f"Policy note {i}", abstract=sent)
        _seed_frames(
            d,
            [
                {
                    "mechanism": "market development frameworks",
                    "object": None,
                    "function": None,
                    "evidence_span": sent,
                    "label": "MACRO_THEME",
                }
            ],
        )
        docs.append(d)
    class ParaphraseBackend(EmbeddingBackend):
        profile = DeterministicTestBackend.profile

        def encode(self, texts: list[str]) -> list[list[float]]:
            out: list[list[float]] = []
            for text in texts:
                low = text.lower()
                if "bandgap" in low or "filter" in low:
                    key = "mech_b"
                elif "waveguide" in low or "interfer" in low:
                    key = "mech_a"
                else:
                    key = "noise"
                out.append(DeterministicTestBackend().encode([f"passage: {key}"])[0])
            return out

    backend = ParaphraseBackend()
    cands, _, _ = discover_candidates_v2(docs, domain_id="t", backend=backend)
    assert len(cands) == 2
    by_name = {c["canonical_name"]: c for c in cands}
    a = next(c for c in cands if c["document_count"] == 5)
    b = next(c for c in cands if c["document_count"] == 3)
    assert len(a["aliases"]) >= 2
    assert a["candidate_id"] != b["candidate_id"]
    shuffled = list(reversed(docs))
    c2, _, _ = discover_candidates_v2(shuffled, domain_id="t", backend=backend)
    assert {c["candidate_id"] for c in cands} == {c["candidate_id"] for c in c2}
    del by_name


def test_tmf_validator_rejects_bad_span():
    doc = _doc(doc_id="x1", title="Title here", abstract="Some abstract about markets.")
    frame, drop = validate_frame(
        doc_id=doc.source_document_id,
        mechanism="nonexistent mechanism phrase",
        object=None,
        function=None,
        evidence_span="missing span words entirely",
        label="TECHNOLOGY_MECHANISM",
        doc=doc,
    )
    assert frame is None
    assert drop is not None
    assert drop.reason == "SPAN_NOT_FOUND"


def test_tmf_provider_batch_call_counter_matches_populate_batches():
    from weaksignalradar.fasttrack.discovery_v2.tmf_extract import (
        provider_calls_made,
        record_tmf_provider_batch_call,
        reset_provider_call_counter,
    )

    reset_provider_call_counter()
    for _ in range(9):
        record_tmf_provider_batch_call()
    assert provider_calls_made() == 9
