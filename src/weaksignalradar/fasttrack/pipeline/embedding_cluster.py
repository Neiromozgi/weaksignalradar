"""Deterministic embedding-based document clustering for candidate discovery."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any

from ..embedding.backend import EmbeddingBackend, cosine_similarity
from ..preprocessing.e5 import passage_from_document
from ..sources.contract import NormalizedSourceDocument

CLUSTERING_ALGORITHM = "greedy_cosine_merge"
SIMILARITY_THRESHOLD = 0.84
MAX_CANDIDATES = 25
TARGET_CANDIDATES = 15

_GENERIC_SINGLE_TOKENS = frozenset(
    {
        "регулирования",
        "национальной",
        "современный",
        "трансформацию",
        "реализации",
        "состояния",
        "технология",
        "традиционными",
        "цифровизации",
        "development",
        "competition",
    }
)


@dataclass(frozen=True, slots=True)
class ClusteringProvenance:
    discovery_method: str
    clustering_algorithm: str
    clustering_similarity_threshold: float
    clustering_max_candidates: int
    clustering_target_candidates: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "discovery_method": self.discovery_method,
            "clustering_algorithm": self.clustering_algorithm,
            "clustering_similarity_threshold": self.clustering_similarity_threshold,
            "clustering_max_candidates": self.clustering_max_candidates,
            "clustering_target_candidates": self.clustering_target_candidates,
            "semantic_threshold": self.clustering_similarity_threshold,
        }


def clustering_provenance_defaults() -> ClusteringProvenance:
    return ClusteringProvenance(
        discovery_method="embedding_cluster_v1",
        clustering_algorithm=CLUSTERING_ALGORITHM,
        clustering_similarity_threshold=SIMILARITY_THRESHOLD,
        clustering_max_candidates=MAX_CANDIDATES,
        clustering_target_candidates=TARGET_CANDIDATES,
    )


def _passage_for_doc(doc: NormalizedSourceDocument) -> str:
    text = passage_from_document(doc.title, doc.abstract)
    if text:
        return text
    return f"passage: {(doc.title or '').strip()}"


def _mean_centroid(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    acc = [0.0] * dim
    for vec in vectors:
        for i, v in enumerate(vec):
            acc[i] += v
    scale = 1.0 / len(vectors)
    mean = [x * scale for x in acc]
    norm = math.sqrt(sum(x * x for x in mean))
    if norm <= 0:
        return mean
    return [x / norm for x in mean]


def _pairwise_best(
    clusters: list[list[int]], centroids: list[list[float]]
) -> tuple[int, int, float]:
    best_i, best_j, best_sim = -1, -1, -1.0
    for i in range(len(clusters)):
        for j in range(i + 1, len(clusters)):
            sim = cosine_similarity(centroids[i], centroids[j])
            if sim > best_sim:
                best_i, best_j, best_sim = i, j, sim
    return best_i, best_j, best_sim


def _merge_clusters(
    clusters: list[list[int]],
    vectors: list[list[float]],
    *,
    threshold: float,
) -> list[list[int]]:
    if not clusters:
        return []
    centroids = [_mean_centroid([vectors[i] for i in c]) for c in clusters]
    while len(clusters) > 1:
        i, j, sim = _pairwise_best(clusters, centroids)
        if i < 0 or sim < threshold:
            break
        merged = clusters[i] + clusters[j]
        new_clusters = [clusters[k] for k in range(len(clusters)) if k not in {i, j}]
        new_clusters.append(merged)
        clusters = new_clusters
        centroids = [_mean_centroid([vectors[idx] for idx in c]) for c in clusters]
    return clusters


def _is_generic_label(name: str) -> bool:
    tokens = re.findall(r"[\w\u0080-\uFFFF]+", name.lower())
    if len(tokens) != 1:
        return False
    return tokens[0] in _GENERIC_SINGLE_TOKENS


def _cluster_label(
    member_indices: list[int],
    documents: list[NormalizedSourceDocument],
    vectors: list[list[float]],
    centroid: list[float],
) -> str:
    ranked = sorted(
        member_indices,
        key=lambda idx: cosine_similarity(vectors[idx], centroid),
        reverse=True,
    )
    for idx in ranked:
        title = documents[idx].title.strip()
        if title and not _is_generic_label(title):
            return title[:160]
    for idx in ranked:
        title = documents[idx].title.strip()
        if title:
            return title[:160]
    return f"Ambiguous technology cluster ({len(member_indices)} works)"


def _stable_candidate_id(member_docs: list[NormalizedSourceDocument]) -> str:
    ids = sorted(d.stable_external_id for d in member_docs)
    digest = hashlib.sha256("|".join(ids).encode()).hexdigest()
    return f"tech_{digest[:12]}"


def cluster_documents(
    documents: list[NormalizedSourceDocument],
    backend: EmbeddingBackend,
    *,
    prov: ClusteringProvenance | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Cluster documents into candidate dicts + provenance metadata."""
    prov = prov or clustering_provenance_defaults()
    if not documents:
        return [], prov.as_dict()

    passages = [_passage_for_doc(d) for d in documents]
    vectors = backend.encode(passages)
    if len(vectors) != len(documents):
        raise ValueError("embedding count mismatch")

    initial = [[i] for i in range(len(documents))]
    merged = _merge_clusters(
        initial,
        vectors,
        threshold=prov.clustering_similarity_threshold,
    )
    cluster_meta = prov.as_dict()
    cluster_meta["cluster_count"] = len(merged)
    cluster_meta["candidate_cap_exceeded"] = len(merged) > prov.clustering_max_candidates

    out: list[dict[str, Any]] = []
    for member_indices in merged:
        docs = [documents[i] for i in member_indices]
        centroid = _mean_centroid([vectors[i] for i in member_indices])
        label = _cluster_label(member_indices, documents, vectors, centroid)
        years = [d.year for d in docs if d.year is not None]
        orgs: set[str] = set()
        for d in docs:
            orgs.update(d.organization_names)
        source_classes = {d.source_type.split("_")[0] for d in docs}
        out.append(
            {
                "candidate_id": _stable_candidate_id(docs),
                "canonical_name": label,
                "name_ru": None,
                "name_en": label,
                "aliases": [],
                "document_ids": [d.source_document_id for d in docs],
                "first_observed_year": min(years) if years else None,
                "document_count": len(docs),
                "organization_count": len(orgs),
                "source_class_count": len(source_classes),
            }
        )
    return out, cluster_meta
