"""Serialize AnalysisRunState ↔ JSON for PostgreSQL."""

from __future__ import annotations

from typing import Any

from ..domain.run_state import AnalysisRunState, CandidateRecord
from ..llm.base import TechnicalSignature
from ..sources.contract import CoverageState, NormalizedSourceDocument, OriginalAvailability


def _doc_to_dict(d: NormalizedSourceDocument) -> dict[str, Any]:
    return {
        "source_document_id": d.source_document_id,
        "source_id": d.source_id,
        "source_type": d.source_type,
        "stable_external_id": d.stable_external_id,
        "title": d.title,
        "year": d.year,
        "canonical_url": d.canonical_url,
        "doi": d.doi,
        "original_availability_status": d.original_availability_status.value,
        "metadata_json": d.metadata_json,
        "source_snapshot_id": d.source_snapshot_id,
        "retrieved_at": d.retrieved_at,
        "content_hash_of_api_record": d.content_hash_of_api_record,
        "coverage_state": d.coverage_state.value,
        "organization_names": d.organization_names,
        "abstract": d.abstract,
    }


def _doc_from_dict(raw: dict[str, Any]) -> NormalizedSourceDocument:
    return NormalizedSourceDocument(
        source_document_id=raw["source_document_id"],
        source_id=raw["source_id"],
        source_type=raw["source_type"],
        stable_external_id=raw["stable_external_id"],
        title=raw["title"],
        year=raw.get("year"),
        canonical_url=raw["canonical_url"],
        doi=raw.get("doi"),
        original_availability_status=OriginalAvailability(raw["original_availability_status"]),
        metadata_json=raw.get("metadata_json") or {},
        source_snapshot_id=raw["source_snapshot_id"],
        retrieved_at=raw["retrieved_at"],
        content_hash_of_api_record=raw["content_hash_of_api_record"],
        coverage_state=CoverageState(raw["coverage_state"]),
        organization_names=list(raw.get("organization_names") or []),
        abstract=raw.get("abstract"),
    )


def _sig_to_dict(s: TechnicalSignature | None) -> dict[str, Any] | None:
    if s is None:
        return None
    return {
        "object_class": s.object_class,
        "function": s.function,
        "mechanism": s.mechanism,
        "architecture_or_process": s.architecture_or_process,
        "key_technical_property": s.key_technical_property,
        "extraction_status": s.extraction_status,
        "evidence_span_refs": s.evidence_span_refs,
        "llm_model_id": s.llm_model_id,
        "prompt_version": s.prompt_version,
        "validation_status": s.validation_status,
        "llm_profile_id": s.llm_profile_id,
    }


def _sig_from_dict(raw: dict[str, Any] | None) -> TechnicalSignature | None:
    if raw is None:
        return None
    return TechnicalSignature(
        object_class=raw.get("object_class"),
        function=raw.get("function"),
        mechanism=raw.get("mechanism"),
        architecture_or_process=raw.get("architecture_or_process"),
        key_technical_property=raw.get("key_technical_property"),
        extraction_status=raw.get("extraction_status", "UNKNOWN"),
        evidence_span_refs=list(raw.get("evidence_span_refs") or []),
        llm_model_id=raw.get("llm_model_id"),
        prompt_version=raw.get("prompt_version", ""),
        validation_status=raw.get("validation_status"),
        llm_profile_id=raw.get("llm_profile_id"),
    )


def _candidate_to_dict(c: CandidateRecord) -> dict[str, Any]:
    return {
        "candidate_id": c.candidate_id,
        "canonical_name": c.canonical_name,
        "name_ru": c.name_ru,
        "name_en": c.name_en,
        "aliases": c.aliases,
        "state": c.state,
        "document_ids": c.document_ids,
        "first_observed_year": c.first_observed_year,
        "document_count": c.document_count,
        "organization_count": c.organization_count,
        "source_class_count": c.source_class_count,
        "signature": _sig_to_dict(c.signature),
        "yearly_stats": c.yearly_stats,
        "features": c.features,
        "filters": c.filters,
        "score": c.score,
        "rank": c.rank,
        "ranking_status": c.ranking_status,
        "fwci_diagnostic": c.fwci_diagnostic,
        "bootstrap_status": c.bootstrap_status,
        "d_diagnostics": c.d_diagnostics,
        "decision_explanation": c.decision_explanation,
        "discovery_frames": c.discovery_frames,
    }


def _candidate_from_dict(raw: dict[str, Any]) -> CandidateRecord:
    return CandidateRecord(
        candidate_id=raw["candidate_id"],
        canonical_name=raw["canonical_name"],
        name_ru=raw.get("name_ru"),
        name_en=raw.get("name_en"),
        aliases=list(raw.get("aliases") or []),
        state=raw["state"],
        document_ids=list(raw.get("document_ids") or []),
        first_observed_year=raw.get("first_observed_year"),
        document_count=int(raw.get("document_count") or 0),
        organization_count=int(raw.get("organization_count") or 0),
        source_class_count=int(raw.get("source_class_count") or 0),
        signature=_sig_from_dict(raw.get("signature")),
        yearly_stats=list(raw.get("yearly_stats") or []),
        features=dict(raw.get("features") or {}),
        filters=list(raw.get("filters") or []),
        score=raw.get("score"),
        rank=raw.get("rank"),
        ranking_status=raw.get("ranking_status"),
        fwci_diagnostic=raw.get("fwci_diagnostic"),
        bootstrap_status=raw.get("bootstrap_status", "NOT_REQUESTED"),
        d_diagnostics=dict(raw.get("d_diagnostics") or {}),
        decision_explanation=raw.get("decision_explanation"),
        discovery_frames=list(raw.get("discovery_frames") or []),
    )


def state_to_json(state: AnalysisRunState) -> dict[str, Any]:
    return {
        "run_id": state.run_id,
        "normalized_query": state.normalized_query,
        "domain_id": state.domain_id,
        "data_mode": state.data_mode,
        "snapshot_id": state.snapshot_id,
        "status": state.status,
        "score_profile_id": state.score_profile_id,
        "feature_contract_version": state.feature_contract_version,
        "candidate_universe_version": state.candidate_universe_version,
        "embedding_model_id": state.embedding_model_id,
        "llm_model_id": state.llm_model_id,
        "coverage_summary": state.coverage_summary,
        "documents": [_doc_to_dict(d) for d in state.documents],
        "candidates": [_candidate_to_dict(c) for c in state.candidates],
        "registries": state.registries,
        "provenance": state.provenance,
        "source_runs": state.source_runs,
        "started_at": state.started_at,
        "finished_at": state.finished_at,
    }


def state_from_json(raw: dict[str, Any]) -> AnalysisRunState:
    return AnalysisRunState(
        run_id=raw["run_id"],
        normalized_query=raw["normalized_query"],
        domain_id=raw.get("domain_id", "default"),
        data_mode=raw["data_mode"],
        snapshot_id=raw.get("snapshot_id"),
        status=raw["status"],
        score_profile_id=raw["score_profile_id"],
        feature_contract_version=raw["feature_contract_version"],
        candidate_universe_version=raw.get("candidate_universe_version", "cu_v1"),
        embedding_model_id=raw["embedding_model_id"],
        llm_model_id=raw.get("llm_model_id"),
        coverage_summary=dict(raw.get("coverage_summary") or {}),
        documents=[_doc_from_dict(d) for d in raw.get("documents") or []],
        candidates=[_candidate_from_dict(c) for c in raw.get("candidates") or []],
        registries=dict(raw.get("registries") or {}),
        provenance=dict(raw.get("provenance") or {}),
        source_runs=list(raw.get("source_runs") or []),
        started_at=raw.get("started_at"),
        finished_at=raw.get("finished_at"),
    )
