"""Evidence-grounded Candidate Registry v2."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any

from ..sources.contract import NormalizedSourceDocument
from .semantic_gate import candidate_gate_label
from .text_norm import normalize_text
from .tmf_types import MechanismFrame


def _normalize_mechanism_phrase(text: str) -> str:
    return normalize_text(text)


def stable_candidate_id(
    head_mechanism: str,
    object: str | None,
    function: str | None,
    doc_ids: list[str],
) -> str:
    parts = [
        _normalize_mechanism_phrase(head_mechanism),
        _normalize_mechanism_phrase(object or ""),
        _normalize_mechanism_phrase(function or ""),
        "|".join(sorted(doc_ids)),
    ]
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"techv2_{digest[:12]}"


def choose_canonical_name(frames: list[MechanismFrame]) -> tuple[str, list[str]]:
    phrases = [_normalize_mechanism_phrase(f.mechanism) for f in frames if f.mechanism]
    if not phrases:
        return "Unknown mechanism cluster", []
    counts = Counter(phrases)
    head, _ = counts.most_common(1)[0]
    aliases = sorted({p for p in phrases if p != head})
    obj = Counter(
        _normalize_mechanism_phrase(f.object) for f in frames if f.object
    ).most_common(1)
    func = Counter(
        _normalize_mechanism_phrase(f.function) for f in frames if f.function
    ).most_common(1)
    name = head
    if obj:
        name = f"{name} ({obj[0][0]})"
    elif func:
        name = f"{name} ({func[0][0]})"
    return name[:160], aliases[:10]


def is_forbidden_candidate_name(name: str) -> bool:
    tokens = re.findall(r"[\w\u0080-\uFFFF]+", name.lower())
    return len(tokens) == 1 and len(tokens[0]) <= 4


def build_candidate_dict(
    *,
    frames: list[MechanismFrame],
    documents: list[NormalizedSourceDocument],
) -> dict[str, Any]:
    doc_by_id = {d.source_document_id: d for d in documents}
    doc_ids = sorted({f.doc_id for f in frames})
    member_docs = [doc_by_id[d] for d in doc_ids if d in doc_by_id]
    orgs: set[str] = set()
    years: list[int] = []
    source_classes: set[str] = set()
    for d in member_docs:
        orgs.update(d.organization_names)
        if d.year is not None:
            years.append(d.year)
        source_classes.add(d.source_type.split("_")[0])

    canonical, aliases = choose_canonical_name(frames)
    head_frame = frames[0]
    gate = candidate_gate_label(frames)
    cid = stable_candidate_id(
        head_frame.mechanism,
        head_frame.object,
        head_frame.function,
        doc_ids,
    )
    frame_payload = [
        {
            "doc_id": f.doc_id,
            "mechanism": f.mechanism,
            "object": f.object,
            "function": f.function,
            "evidence_span": f.evidence_span,
            "label": f.label,
        }
        for f in frames
    ]
    return {
        "candidate_id": cid,
        "canonical_name": canonical,
        "name_ru": None,
        "name_en": canonical,
        "aliases": aliases,
        "gate_label": gate,
        "frames": frame_payload,
        "document_ids": doc_ids,
        "organization_names": sorted(orgs),
        "document_count": len(doc_ids),
        "organization_count": len(orgs),
        "source_class_count": len(source_classes) or 1,
        "first_observed_year": min(years) if years else None,
        "provenance": {"naming": "extractive_mechanism_medoid_v1"},
    }
