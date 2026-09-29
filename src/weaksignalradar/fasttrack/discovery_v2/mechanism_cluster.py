"""Complete-linkage clustering on mechanism frame embeddings."""

from __future__ import annotations

from collections.abc import Callable

from ..embedding.backend import cosine_similarity
from ..preprocessing.e5 import prefix_passage
from .threshold import (
    CALIBRATED_DISTANCE_THRESHOLD,
    CLUSTERING_ALGORITHM,
    CLUSTERING_REPRESENTATION,
)
from .tmf_types import MechanismFrame


def frame_passage_text(
    mechanism: str,
    object: str | None,
    function: str | None,
    *,
    representation: str = CLUSTERING_REPRESENTATION,
) -> str:
    mech = mechanism.strip()
    if representation == "mechanism":
        body = mech
    elif representation == "mechanism_function":
        body = " | ".join(x for x in (mech, (function or "").strip()) if x)
    elif representation == "mechanism_object_function":
        body = " | ".join(
            x for x in (mech, (object or "").strip(), (function or "").strip()) if x
        )
    else:
        body = mech
    return body


def frame_passage_for_representation(frame: MechanismFrame, *, representation: str) -> str:
    return prefix_passage(
        frame_passage_text(
            frame.mechanism,
            frame.object,
            frame.function,
            representation=representation,
        )
    )


def frame_passage(mechanism: str, object: str | None, function: str | None) -> str:
    return prefix_passage(
        frame_passage_text(mechanism, object, function, representation=CLUSTERING_REPRESENTATION)
    )


def cosine_distance(i: int, j: int, vectors: list[list[float]]) -> float:
    return 1.0 - cosine_similarity(vectors[i], vectors[j])


def complete_linkage_clusters(
    n: int,
    distance_fn: Callable[[int, int], float],
    *,
    distance_threshold: float,
) -> list[list[int]]:
    if n == 0:
        return []
    clusters: list[list[int]] = [[i] for i in range(n)]

    def cluster_distance(c1: list[int], c2: list[int]) -> float:
        return max(distance_fn(i, j) for i in c1 for j in c2)

    while len(clusters) > 1:
        best_i, best_j, best_d = -1, -1, float("inf")
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                d = cluster_distance(clusters[i], clusters[j])
                if d < best_d:
                    best_i, best_j, best_d = i, j, d
        if best_i < 0 or best_d > distance_threshold:
            break
        merged = clusters[best_i] + clusters[best_j]
        clusters = [c for idx, c in enumerate(clusters) if idx not in {best_i, best_j}]
        clusters.append(merged)
    return clusters


def cluster_frames(
    frame_indices: list[int],
    vectors: list[list[float]],
    *,
    distance_threshold: float = CALIBRATED_DISTANCE_THRESHOLD,
) -> list[list[int]]:
    if not frame_indices:
        return []

    def local_dist(a: int, b: int) -> float:
        return cosine_distance(frame_indices[a], frame_indices[b], vectors)

    local_n = len(frame_indices)
    local_clusters = complete_linkage_clusters(
        local_n, local_dist, distance_threshold=distance_threshold
    )
    return [[frame_indices[i] for i in cluster] for cluster in local_clusters]


def clustering_provenance_fields(
    *,
    cluster_count: int,
    singleton_count: int,
    largest_share: float,
    corpus_doc_count: int,
    distance_threshold: float = CALIBRATED_DISTANCE_THRESHOLD,
) -> dict[str, object]:
    return {
        "clustering_algorithm": CLUSTERING_ALGORITHM,
        "clustering_distance_threshold": distance_threshold,
        "clustering_similarity_floor": 1.0 - distance_threshold,
        "cluster_count": cluster_count,
        "singleton_cluster_count": singleton_count,
        "largest_cluster_doc_share": largest_share,
        "corpus_doc_count": corpus_doc_count,
    }
