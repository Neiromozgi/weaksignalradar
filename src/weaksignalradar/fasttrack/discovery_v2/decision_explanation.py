"""Deterministic emerging-signal explanation (no LLM prose)."""

from __future__ import annotations

from typing import Any

from ..domain.run_state import CandidateRecord


def _sufficiency_block(c: CandidateRecord) -> dict[str, Any]:
    docs_ok = c.document_count >= 10
    orgs_ok = c.organization_count >= 3
    ys = sorted(int(row["year"]) for row in c.yearly_stats if row.get("year") is not None)
    temporal = len(ys)
    temporal_ok = temporal >= 4
    return {
        "documents": {
            "value": c.document_count,
            "required": 10,
            "status": "PASS" if docs_ok else "FAIL",
        },
        "organizations": {
            "value": c.organization_count,
            "required": 3,
            "status": "PASS" if orgs_ok else "FAIL",
        },
        "temporal_points": {
            "value": temporal,
            "required": 4,
            "status": "PASS" if temporal_ok else "FAIL",
        },
    }


def _feature_block(c: CandidateRecord) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for code in ("A", "B", "C", "D", "E"):
        f = c.features.get(code, {})
        out[code] = {
            "value": f.get("raw"),
            "percentile": f.get("percentile"),
            "status": f.get("availability") or "UNKNOWN",
        }
    return out


def _why_lines(c: CandidateRecord) -> list[str]:
    lines: list[str] = []
    if c.ranking_status == "UNKNOWN_INSUFFICIENT":
        for flt in c.filters:
            code = flt.get("reason_code") or flt.get("filter_code")
            if code:
                lines.append(f"INSUFFICIENT:{code}")
        if not lines:
            lines.append("INSUFFICIENT:DATA_SUFFICIENCY")
    elif c.ranking_status == "REJECTED":
        for flt in c.filters:
            if not flt.get("passed", True):
                lines.append(
                    f"FILTER_REJECT:{flt.get('filter_code')}:{flt.get('reason_code')}"
                )
    elif c.ranking_status == "RANKED":
        lines.append("QUALIFIED:ABCDE_PERCENTILE_SCORE")
        if c.rank is not None and c.rank <= 15:
            lines.append("RANK:TOP15")
        else:
            lines.append("RANK:BELOW_15")
    return lines


def build_decision_explanation(
    c: CandidateRecord,
    *,
    frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    decision = c.ranking_status or c.state
    if c.rank is not None and c.rank <= 15 and c.ranking_status == "RANKED":
        decision = "TOP15"
    elif c.ranking_status == "RANKED":
        decision = "RANKED_BELOW_15"
    elif c.ranking_status == "REJECTED":
        decision = "REJECTED"
    elif c.ranking_status == "UNKNOWN_INSUFFICIENT":
        decision = "UNKNOWN_INSUFFICIENT"

    examples: list[dict[str, str]] = []
    if frames:
        for fr in frames[:3]:
            if fr.get("evidence_span"):
                examples.append(
                    {"doc_id": str(fr.get("doc_id")), "evidence_span": str(fr["evidence_span"])}
                )
    if not examples:
        examples.append({"doc_id": "", "evidence_span": "", "reason": "NO_GROUNDED_SPAN_IN_RECORD"})

    summary = decision
    if c.score is not None:
        summary = f"{decision}; score={c.score}"

    return {
        "decision": decision,
        "qualification_summary": summary,
        "evidence_examples": examples,
        "sufficiency": _sufficiency_block(c),
        "features": _feature_block(c),
        "filters": list(c.filters),
        "why_or_why_not": _why_lines(c),
    }
