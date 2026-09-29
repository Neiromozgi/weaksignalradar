"""Discovery v2 orchestration."""

from __future__ import annotations

from typing import Any

from ..embedding.backend import EmbeddingBackend
from ..sources.contract import NormalizedSourceDocument
from .mechanism_cluster import cluster_frames, clustering_provenance_fields, frame_passage
from .registry import build_candidate_dict, is_forbidden_candidate_name
from .semantic_gate import frame_clusterable
from .status import resolve_discovery_status
from .threshold import (
    CALIBRATED_DISTANCE_THRESHOLD,
    clustering_calibration_provenance,
)
from .tmf_extract import extract_tmfs

DISCOVERY_METHOD = "discovery_v2_tmf_complete_link_v1"


def discover_candidates_v2(
    documents: list[NormalizedSourceDocument],
    *,
    domain_id: str,
    backend: EmbeddingBackend | None,
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    del domain_id
    prov: dict[str, Any] = {
        "discovery_version": "v2",
        "discovery_method": DISCOVERY_METHOD,
    }
    if backend is None:
        prov["discovery_status"] = "EMBEDDING_UNAVAILABLE"
        return [], DISCOVERY_METHOD, prov

    frames, tmf_stats, drops = extract_tmfs(documents)
    prov["tmf_extraction"] = tmf_stats.to_dict()
    prov["tmf_drops_sample"] = [{"doc_id": d.doc_id, "reason": d.reason} for d in drops[:20]]

    clusterable_frames = sorted(
        [f for f in frames if frame_clusterable(f)],
        key=lambda f: (f.doc_id, f.mechanism, f.evidence_span),
    )
    tech_frames = [f for f in frames if f.label == "TECHNOLOGY_MECHANISM"]

    passages = [frame_passage(f.mechanism, f.object, f.function) for f in clusterable_frames]
    vectors = backend.encode(passages) if passages else []
    index_clusters = cluster_frames(
        list(range(len(clusterable_frames))),
        vectors,
        distance_threshold=CALIBRATED_DISTANCE_THRESHOLD,
    )

    scoring_candidates: list[dict[str, Any]] = []
    audit_rejected: list[dict[str, Any]] = []
    largest_tech_share = 0.0
    corpus_n = max(len(documents), 1)

    for member in index_clusters:
        member_frames = [clusterable_frames[i] for i in member]
        cand = build_candidate_dict(frames=member_frames, documents=documents)
        if is_forbidden_candidate_name(cand["canonical_name"]):
            cand["gate_label"] = "REJECTED_NOT_TECHNOLOGY_LEVEL"
        if cand["gate_label"] == "TECHNOLOGY":
            share = cand["document_count"] / corpus_n
            largest_tech_share = max(largest_tech_share, share)
            scoring_candidates.append(cand)
        else:
            audit_rejected.append(cand)

    singletons = sum(1 for c in index_clusters if len(c) == 1)
    prov.update(
        clustering_provenance_fields(
            cluster_count=len(index_clusters),
            singleton_count=singletons,
            largest_share=largest_tech_share,
            corpus_doc_count=len(documents),
        )
    )
    prov.update(clustering_calibration_provenance())
    prov["discovery_v2_rejected_audit"] = audit_rejected
    prov["technology_mechanism_frame_count"] = len(tech_frames)
    prov["discovery_status"] = resolve_discovery_status(
        technology_frames=tech_frames,
        largest_technology_cluster_share=largest_tech_share,
        embedding_available=True,
        partial_sources=False,
    )
    return scoring_candidates, DISCOVERY_METHOD, prov
