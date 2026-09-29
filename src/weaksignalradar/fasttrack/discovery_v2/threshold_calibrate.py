"""Production threshold calibration on frozen real-E5 vectors (not deterministic backend)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .mechanism_cluster import cluster_frames
from .registry import build_candidate_dict
from .threshold import (
    CALIBRATED_DISTANCE_THRESHOLD,
)

_CALIBRATION_GRID = (0.02, 0.03, 0.04, 0.05, 0.055, 0.06, 0.065, 0.07, 0.075, 0.08, 0.10, 0.12)
_REPRESENTATIONS = (
    "A_mechanism",
    "B_mechanism_function",
    "C_mechanism_object_function",
)

# Calibration-only semantic indices on discovery_v2_e5_live2_34_v1 frame order.
_QUANT_IDX = {10, 11, 12}
_AI_IDX = {8, 18}
_MUST_SEPARATE = (
    (7, 8),
    (18, 19),
    (23, 24),
    (20, 23),
    (28, 29),
    (30, 29),  # ATM vs tokenized tickets
    (5, 17),  # biometrics vs big-data analysis
)
_BLOCKCHAIN_IDX = {2, 3, 7, 13, 16, 19, 21, 22, 26, 27, 32}


def _fixture_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "discovery_v2_e5_live2_34_v1.json"
    )


def load_calibration_fixture() -> dict[str, Any]:
    path = _fixture_path()
    return json.loads(path.read_text(encoding="utf-8"))


def _cluster_map(
    vectors: list[list[float]], threshold: float
) -> tuple[dict[int, int], list[list[int]]]:
    clusters = cluster_frames(list(range(len(vectors))), vectors, distance_threshold=threshold)
    cmap: dict[int, int] = {}
    for ci, member in enumerate(clusters):
        for idx in member:
            cmap[idx] = ci
    return cmap, clusters


def _largest_doc_share(
    clusters: list[list[int]], frames: list[dict[str, Any]], corpus_n: int
) -> float:
    largest = 0.0
    for member in clusters:
        docs = {frames[i]["doc_id"] for i in member}
        largest = max(largest, len(docs) / max(corpus_n, 1))
    return largest


def evaluate_calibration_grid(fixture: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    data = fixture or load_calibration_fixture()
    frames = data["frames"]
    corpus_n = 75
    rows: list[dict[str, Any]] = []
    for rep in _REPRESENTATIONS:
        vectors = data["vectors_by_representation"][rep]
        for threshold in _CALIBRATION_GRID:
            cmap, clusters = _cluster_map(vectors, threshold)
            largest = _largest_doc_share(clusters, frames, corpus_n)
            memberships: list[dict[str, Any]] = []
            multi = 0
            for member in clusters:
                mframes = [frames[i] for i in member]
                pseudo_docs = []
                cand = build_candidate_dict(
                    frames=_frames_as_objects(mframes),
                    documents=pseudo_docs,
                )
                del pseudo_docs
                if cand["gate_label"] != "TECHNOLOGY":
                    continue
                if cand["document_count"] > 1:
                    multi += 1
                memberships.append(
                    {
                        "canonical_name": cand["canonical_name"][:120],
                        "doc_count": cand["document_count"],
                        "frame_count": len(mframes),
                    }
                )
            rows.append(
                {
                    "representation": rep,
                    "distance_threshold": threshold,
                    "cluster_count": len(clusters),
                    "singleton_count": sum(1 for c in clusters if len(c) == 1),
                    "multi_document_cluster_count": multi,
                    "largest_document_share": largest,
                    "technology_memberships": memberships,
                }
            )
    return rows


def _frames_as_objects(raw: list[dict[str, Any]]):
    from .tmf_types import MechanismFrame

    out: list[MechanismFrame] = []
    for r in raw:
        out.append(
            MechanismFrame(
                doc_id=str(r["doc_id"]),
                mechanism=str(r["mechanism"]),
                object=r.get("object"),
                function=r.get("function"),
                evidence_span=str(r["evidence_span"]),
                label=r.get("label") or "TECHNOLOGY_MECHANISM",
            )
        )
    return out


def _semantic_calibration_pass(
    cmap: dict[int, int], clusters: list[list[int]], frames: list[dict]
) -> bool:
    if len({cmap[i] for i in _QUANT_IDX}) > 2:
        return False
    if len({cmap[i] for i in _AI_IDX}) != 1:
        return False
    if any(cmap[a] == cmap[b] for a, b in _MUST_SEPARATE):
        return False
    if cmap[8] == cmap[7] or cmap[18] == cmap[19]:
        return False
    bc_multi = any(
        len({frames[i]["doc_id"] for i in mem if i in _BLOCKCHAIN_IDX}) > 1
        for mem in clusters
    )
    return bc_multi


def select_production_calibration(
    fixture: dict[str, Any] | None = None,
) -> tuple[dict[str, object], list[dict[str, Any]]]:
    """Pick highest distance threshold (still conservative vs 0.22) passing guards + semantics."""
    data = fixture or load_calibration_fixture()
    frames = data["frames"]
    table = evaluate_calibration_grid(data)
    chosen_rep = "A_mechanism"
    chosen_thr = CALIBRATED_DISTANCE_THRESHOLD
    best_thr = -1.0
    for rep in _REPRESENTATIONS:
        vectors = data["vectors_by_representation"][rep]
        for threshold in _CALIBRATION_GRID:
            cmap, clusters = _cluster_map(vectors, threshold)
            largest = _largest_doc_share(clusters, frames, 75)
            if largest > 0.25 or len(clusters) < 2:
                continue
            if not _semantic_calibration_pass(cmap, clusters, frames):
                continue
            if threshold > best_thr:
                best_thr = threshold
                chosen_thr = threshold
                chosen_rep = rep
    rep_map = {
        "A_mechanism": ("mechanism", "tmf_mechanism_v1"),
        "B_mechanism_function": ("mechanism_function", "tmf_mechanism_function_v1"),
        "C_mechanism_object_function": (
            "mechanism_object_function",
            "tmf_mechanism_object_function_v1",
        ),
    }
    rep_name, rep_ver = rep_map[chosen_rep]
    selected = {
        "distance_threshold": chosen_thr,
        "representation_key": chosen_rep,
        "clustering_representation": rep_name,
        "clustering_representation_version": rep_ver,
    }
    return selected, table


def choose_distance_threshold(*args: object, **kwargs: object) -> tuple[float, dict[str, object]]:
    """Legacy hook: refuse deterministic-backend calibration."""
    del args, kwargs
    raise RuntimeError(
        "choose_distance_threshold() uses deterministic backend and is disabled; "
        "use frozen fixture discovery_v2_e5_live2_34_v1 + threshold.py constants."
    )
