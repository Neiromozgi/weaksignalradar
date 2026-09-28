"""Candidate discovery from Source Document Registry (handoff 09)."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from ..sources.contract import NormalizedSourceDocument


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[\w\u0080-\uFFFF]{4,}", text.lower())}


def discover_candidates(
    documents: list[NormalizedSourceDocument],
    *,
    domain_id: str,
    method_version: str = "keyphrase_cluster_v1",
) -> tuple[list[dict], str]:
    """Returns candidate dicts + method_version recorded in run metadata."""
    del domain_id
    clusters: dict[str, list[NormalizedSourceDocument]] = defaultdict(list)
    for doc in documents:
        key = _cluster_key(doc.title)
        clusters[key].append(doc)

    out: list[dict] = []
    for key, docs in clusters.items():
        if not key:
            continue
        cid = f"tech_{hashlib.sha256(key.encode()).hexdigest()[:12]}"
        years = [d.year for d in docs if d.year]
        orgs: set[str] = set()
        for d in docs:
            orgs.update(d.organization_names)
        source_classes = {d.source_type.split("_")[0] for d in docs}
        out.append(
            {
                "candidate_id": cid,
                "canonical_name": key.replace("_", " ").title(),
                "name_ru": None,
                "name_en": key.replace("_", " ").title(),
                "aliases": [],
                "document_ids": [d.source_document_id for d in docs],
                "first_observed_year": min(years) if years else None,
                "document_count": len(docs),
                "organization_count": len(orgs),
                "source_class_count": len(source_classes),
            }
        )
    return out, method_version


def _cluster_key(title: str) -> str:
    low = title.lower()
    if "quantum" in low and "photon" in low:
        return "quantum_photonic"
    if "solid" in low and "battery" in low:
        return "solid_state_battery"
    return _primary_keyphrase(title)


def _primary_keyphrase(title: str) -> str:
    tokens = sorted(_tokenize(title), key=len, reverse=True)
    if not tokens:
        return "unknown_topic"
    return tokens[0]
