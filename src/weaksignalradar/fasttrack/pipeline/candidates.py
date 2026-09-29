"""Candidate discovery from Source Document Registry (handoff 09)."""

from __future__ import annotations

from typing import Any

from ..embedding.backend import EmbeddingBackend
from ..sources.contract import NormalizedSourceDocument
from .embedding_cluster import cluster_documents, clustering_provenance_defaults

DISCOVERY_EMBEDDING_UNAVAILABLE = "EMBEDDING_UNAVAILABLE"


def discover_candidates(
    documents: list[NormalizedSourceDocument],
    *,
    domain_id: str,
    backend: EmbeddingBackend | None = None,
    method_version: str = "embedding_cluster_v1",
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    """Returns candidate dicts, method_version, and clustering provenance."""
    del domain_id
    prov = clustering_provenance_defaults()
    if method_version != prov.discovery_method:
        prov = clustering_provenance_defaults()
    base_meta = prov.as_dict()
    if backend is None:
        base_meta.update(
            {
                "discovery_status": DISCOVERY_EMBEDDING_UNAVAILABLE,
                "cluster_count": 0,
                "candidate_cap_exceeded": False,
            }
        )
        return [], prov.discovery_method, base_meta
    candidates, cluster_meta = cluster_documents(documents, backend, prov=prov)
    return candidates, prov.discovery_method, cluster_meta
