"""Groundedness validation for Technical Mechanism Frames."""

from __future__ import annotations

import re

from ..sources.contract import NormalizedSourceDocument
from .macro_vocab import is_generic_macro_mechanism
from .semantic_non_technology import reject_technology_mechanism_label
from .text_norm import significant_tokens, span_in_source
from .tmf_types import FrameDrop, MechanismFrame


def validate_frame(
    *,
    doc_id: str,
    mechanism: str,
    object: str | None,
    function: str | None,
    evidence_span: str,
    label: str,
    doc: NormalizedSourceDocument | None,
) -> tuple[MechanismFrame | None, FrameDrop | None]:
    mech = (mechanism or "").strip()
    span = (evidence_span or "").strip()
    if not doc:
        return None, FrameDrop(doc_id=doc_id, reason="INVALID_DOC", mechanism=mech or None)
    if not mech:
        return None, FrameDrop(doc_id=doc_id, reason="EMPTY_MECHANISM")
    tokens = re.findall(r"[\w\u0080-\uFFFF]+", mech.lower())
    if len(tokens) == 1 and len(tokens[0]) < 5 and not re.search(r"\d", tokens[0]):
        if is_generic_macro_mechanism(mech):
            return None, FrameDrop(doc_id=doc_id, reason="GENERIC_TOKEN", mechanism=mech)
    if is_generic_macro_mechanism(mech) and label == "TECHNOLOGY_MECHANISM":
        return None, FrameDrop(doc_id=doc_id, reason="GENERIC_TOKEN", mechanism=mech)
    if label == "TECHNOLOGY_MECHANISM" and reject_technology_mechanism_label(
        mechanism=mech, evidence_span=span
    ):
        return None, FrameDrop(doc_id=doc_id, reason="NON_TECH_SEMANTIC", mechanism=mech)
    if not span_in_source(span, doc.title, doc.abstract):
        return None, FrameDrop(doc_id=doc_id, reason="SPAN_NOT_FOUND", mechanism=mech)
    sig = significant_tokens(mech)
    if sig:
        hay = f"{doc.title} {doc.abstract or ''}".lower()
        if not any(t in hay for t in sig):
            return None, FrameDrop(doc_id=doc_id, reason="MECHANISM_UNGROUNDED", mechanism=mech)
    safe_label = label if label in {
        "TECHNOLOGY_MECHANISM",
        "APPLICATION_AREA",
        "METHOD_GENERIC",
        "MACRO_THEME",
        "POLICY_REGULATION",
        "UNCERTAIN",
    } else "UNCERTAIN"
    return (
        MechanismFrame(
            doc_id=doc_id,
            mechanism=mech,
            object=(object or None),
            function=(function or None),
            evidence_span=span,
            label=safe_label,  # type: ignore[arg-type]
        ),
        None,
    )
