"""Serialize run state for API responses."""

from __future__ import annotations

from typing import Any

from ..domain.run_state import AnalysisRunState, CandidateRecord
from ..llm.base import TechnicalSignature
from ..ui.limitations import limitations_lines
from ..ui.naming import technology_display_names


def signature_to_dict(sig: TechnicalSignature | None) -> dict[str, Any] | None:
    if sig is None:
        return None
    return {
        "object_class": sig.object_class,
        "function": sig.function,
        "mechanism": sig.mechanism,
        "architecture_or_process": sig.architecture_or_process,
        "key_technical_property": sig.key_technical_property,
        "extraction_status": sig.extraction_status,
        "llm_model_id": sig.llm_model_id,
        "prompt_version": sig.prompt_version,
    }


def candidate_to_api(c: CandidateRecord, state: AnalysisRunState) -> dict[str, Any]:
    doc_links = []
    doc_index = {d.source_document_id: d for d in state.documents}
    for did in c.document_ids:
        d = doc_index.get(did)
        if d:
            doc_links.append(
                {
                    "source_document_id": d.source_document_id,
                    "source_type": d.source_type,
                    "stable_external_id": d.stable_external_id,
                    "title": d.title,
                    "year": d.year,
                    "organization_names": d.organization_names,
                    "original_availability_status": d.original_availability_status.value,
                    "canonical_url": d.canonical_url,
                    "coverage_state": d.coverage_state.value,
                    "source_snapshot_id": d.source_snapshot_id,
                }
            )
    features_out: dict[str, Any] = {}
    for code, f in c.features.items():
        if code.startswith("_"):
            continue
        w = (
            0.0
            if code not in ("A", "B", "C", "D", "E")
            else {"A": 0.3, "B": 0.2, "C": 0.25, "D": 0.15, "E": 0.1}[code]
        )
        contrib = None
        if c.features.get("_contributions"):
            contrib = c.features["_contributions"].get(code, {}).get("contribution")
        features_out[code] = {
            "raw": f.get("raw"),
            "percentile": f.get("percentile"),
            "weight": w,
            "contribution": contrib,
            "availability": f.get("availability"),
        }
    names = technology_display_names(c)
    return {
        "candidate_id": c.candidate_id,
        "canonical_name": c.canonical_name,
        "name_ru": names["name_ru"],
        "name_original": names["name_original"],
        "display_label": names["display_label"],
        "aliases": names["aliases"],
        "state": c.state,
        "ranking_status": c.ranking_status,
        "score_profile_id": state.score_profile_id,
        "score": c.score,
        "rank": c.rank,
        "features": features_out,
        "technical_signature": signature_to_dict(c.signature),
        "early_signal_summary": _early_signal_summary(c),
        "fwci_diagnostic": c.fwci_diagnostic,
        "bootstrap": {"status": c.bootstrap_status, "interval": None},
        "filters": c.filters,
        "d_diagnostics": c.d_diagnostics,
        "limitations_human": limitations_lines(
            d_diagnostics=c.d_diagnostics,
            features=features_out,
            source_runs=state.source_runs,
            coverage=state.coverage_summary,
        ),
        "source_documents": doc_links,
        "document_count": c.document_count,
        "organization_count": c.organization_count,
        "source_class_count": c.source_class_count,
    }


def _early_signal_summary(c: CandidateRecord) -> str:
    parts: list[str] = []
    if c.rank is not None:
        parts.append(f"Ранг {c.rank} в текущем прогоне")
    if c.score is not None:
        parts.append(f"итоговый score {c.score:.3f}")
    filter_rows = c.filters if isinstance(c.filters, list) else []
    failed = [f.get("filter_code", "?") for f in filter_rows if f.get("passed") is False]
    if not failed and c.ranking_status == "RANKED":
        parts.append("пройдены эвристические фильтры раннего сигнала")
    if failed:
        parts.append("не пройдены фильтры: " + ", ".join(failed))
    feats = c.features or {}
    avail = [code for code in "ABCDE" if feats.get(code, {}).get("availability") == "OK"]
    if avail:
        parts.append("доступны признаки: " + ", ".join(avail))
    unknown = [
        code
        for code in "ABCDE"
        if feats.get(code, {}).get("availability") not in (None, "OK")
    ]
    if unknown:
        parts.append("ограничения данных: " + ", ".join(unknown))
    if c.document_count:
        parts.append(f"документов в поддержке: {c.document_count}")
    return ". ".join(parts) if parts else "Недостаточно данных для краткого обоснования."


def document_row(d) -> dict[str, Any]:
    return {
        "source_document_id": d.source_document_id,
        "source_id": d.source_id,
        "source_type": d.source_type,
        "stable_external_id": d.stable_external_id,
        "title": d.title,
        "year": d.year,
        "canonical_url": d.canonical_url,
        "original_availability_status": d.original_availability_status.value,
        "source_snapshot_id": d.source_snapshot_id,
        "coverage_state": d.coverage_state.value,
    }
