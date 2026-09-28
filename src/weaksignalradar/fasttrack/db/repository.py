"""Authoritative PostgreSQL run persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..config.embedding_profile import E5_SMALL_V1
from ..domain.run_state import AnalysisRunState
from ..llm.base import TechnicalSignature
from ..llm.profile import LLM_PROFILE_ID
from . import models as m
from .state_codec import state_from_json, state_to_json


class RunRepository(Protocol):
    def save(self, state: AnalysisRunState) -> None: ...
    def get(self, run_id: str) -> AnalysisRunState | None: ...
    def get_extraction_replay(
        self, snapshot_id: str | None, candidate_id: str, evidence_hash: str
    ) -> TechnicalSignature | None: ...
    def get_extraction(
        self, run_id: str, candidate_id: str, evidence_hash: str
    ) -> TechnicalSignature | None: ...
    def save_extraction(
        self,
        *,
        run_id: str,
        candidate_id: str,
        evidence_hash: str,
        signature: TechnicalSignature,
        extraction_payload: dict,
        provenance: dict,
    ) -> None: ...


class PostgresRunRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, state: AnalysisRunState) -> None:
        payload = state_to_json(state)
        created = _parse_dt(state.started_at) or datetime.now(UTC)
        completed = _parse_dt(state.finished_at)
        with Session(self._engine) as session:
            row = session.get(m.FtAnalysisRunRow, state.run_id)
            if row is None:
                row = m.FtAnalysisRunRow(
                    run_id=state.run_id,
                    created_at=created,
                )
                session.add(row)
            row.domain_id = state.domain_id
            row.normalized_query = state.normalized_query
            row.data_mode = state.data_mode
            row.snapshot_id = state.snapshot_id
            row.status = state.status
            row.score_profile_id = state.score_profile_id
            row.embedding_profile_id = E5_SMALL_V1.embedding_profile_id
            row.feature_contract_version = state.feature_contract_version
            row.candidate_universe_version = state.candidate_universe_version
            row.llm_profile_id = state.llm_model_id or LLM_PROFILE_ID
            row.source_coverage = dict(state.coverage_summary)
            row.provenance = dict(state.provenance)
            row.registries = dict(state.registries)
            row.warnings = list(state.provenance.get("warnings") or [])
            row.limitations = list(state.provenance.get("limitations") or [])
            row.error_text = (state.coverage_summary or {}).get("message")
            row.state_json = payload
            row.completed_at = completed

            session.execute(
                delete(m.FtSourceDocumentRow).where(m.FtSourceDocumentRow.run_id == state.run_id)
            )
            session.execute(delete(m.FtCandidateRow).where(m.FtCandidateRow.run_id == state.run_id))
            session.execute(delete(m.FtSourceRunRow).where(m.FtSourceRunRow.run_id == state.run_id))

            for doc in state.documents:
                source_channel = doc.source_type.split("_")[0][:32]
                session.add(
                    m.FtSourceDocumentRow(
                        run_id=state.run_id,
                        source_document_id=doc.source_document_id,
                        source_id=source_channel,
                        source_type=doc.source_type,
                        stable_external_id=doc.stable_external_id,
                        title=doc.title,
                        publication_year=doc.year,
                        canonical_url=doc.canonical_url,
                        original_availability_status=doc.original_availability_status.value,
                        coverage_state=doc.coverage_state.value,
                        metadata_json=doc.metadata_json,
                        provenance={"snapshot_id": doc.source_snapshot_id},
                    )
                )
            for cand in state.candidates:
                sig = cand.signature
                session.add(
                    m.FtCandidateRow(
                        run_id=state.run_id,
                        candidate_id=cand.candidate_id,
                        canonical_name=cand.canonical_name,
                        stage=cand.state,
                        technical_signature=_sig_dict(sig),
                        document_ids=cand.document_ids,
                        document_count=cand.document_count,
                        organization_count=cand.organization_count,
                        source_class_count=cand.source_class_count,
                        result_json={
                            "features": cand.features,
                            "filters": cand.filters,
                            "score": cand.score,
                            "rank": cand.rank,
                            "ranking_status": cand.ranking_status,
                            "d_diagnostics": cand.d_diagnostics,
                            "signature": _sig_dict(sig),
                        },
                    )
                )
            for sr in state.source_runs:
                session.add(
                    m.FtSourceRunRow(
                        run_id=state.run_id,
                        source=sr.get("source", "unknown"),
                        execution_status=sr.get("execution_status", "UNKNOWN"),
                        external_calls=int(sr.get("external_calls") or 0),
                        records_received=int(sr.get("records_received") or 0),
                        cap_reached=bool(sr.get("cap_reached")),
                        error_detail=sr.get("error"),
                        started_at=_parse_dt(sr.get("started_at")) or created,
                        completed_at=_parse_dt(sr.get("completed_at")),
                        detail_json=dict(sr),
                    )
                )
            if state.snapshot_id:
                snap = session.get(m.FtSnapshotRow, state.snapshot_id)
                if snap is None:
                    session.add(
                        m.FtSnapshotRow(
                            snapshot_id=state.snapshot_id,
                            run_id=state.run_id,
                            created_at=created,
                            mode=state.data_mode,
                            source_set=[sr.get("source") for sr in state.source_runs],
                            storage_ref=f"fixtures/{state.snapshot_id}",
                            document_count=len(state.documents),
                        )
                    )
            session.commit()

    def get(self, run_id: str) -> AnalysisRunState | None:
        with Session(self._engine) as session:
            row = session.get(m.FtAnalysisRunRow, run_id)
            if row is None:
                return None
            return state_from_json(dict(row.state_json))

    def get_extraction_replay(
        self, snapshot_id: str | None, candidate_id: str, evidence_hash: str
    ) -> TechnicalSignature | None:
        if not snapshot_id:
            return None
        with Session(self._engine) as session:
            rows = session.scalars(
                select(m.FtLlmExtractionRow)
                .where(
                    m.FtLlmExtractionRow.candidate_id == candidate_id,
                    m.FtLlmExtractionRow.evidence_hash == evidence_hash,
                    m.FtLlmExtractionRow.validation_status == "PASSED",
                )
                .limit(20)
            ).all()
            from .state_codec import _sig_from_dict

            for row in rows:
                if (row.provenance_json or {}).get("snapshot_id") == snapshot_id:
                    inner = row.extraction_json.get("signature") or row.extraction_json
                    return _sig_from_dict(inner)
            return None

    def get_extraction(
        self, run_id: str, candidate_id: str, evidence_hash: str
    ) -> TechnicalSignature | None:
        with Session(self._engine) as session:
            row = session.get(
                m.FtLlmExtractionRow,
                {"run_id": run_id, "candidate_id": candidate_id, "evidence_hash": evidence_hash},
            )
            if row is None:
                return None
            from .state_codec import _sig_from_dict

            inner = row.extraction_json.get("signature") or row.extraction_json
            return _sig_from_dict(inner)

    def save_extraction(
        self,
        *,
        run_id: str,
        candidate_id: str,
        evidence_hash: str,
        signature: TechnicalSignature,
        extraction_payload: dict,
        provenance: dict,
    ) -> None:
        with Session(self._engine) as session:
            session.merge(
                m.FtLlmExtractionRow(
                    run_id=run_id,
                    candidate_id=candidate_id,
                    evidence_hash=evidence_hash,
                    llm_profile_id=signature.llm_profile_id or LLM_PROFILE_ID,
                    validation_status=signature.validation_status or "UNKNOWN",
                    extraction_json=extraction_payload,
                    provenance_json=provenance,
                    created_at=datetime.now(UTC),
                )
            )
            session.commit()


def _sig_dict(sig) -> dict | None:
    if sig is None:
        return None
    return {
        "object_class": sig.object_class,
        "function": sig.function,
        "mechanism": sig.mechanism,
        "architecture_or_process": sig.architecture_or_process,
        "key_technical_property": sig.key_technical_property,
        "extraction_status": sig.extraction_status,
        "evidence_span_refs": sig.evidence_span_refs,
        "llm_model_id": sig.llm_model_id,
        "prompt_version": sig.prompt_version,
        "validation_status": sig.validation_status,
        "llm_profile_id": sig.llm_profile_id,
    }


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class MemoryRunRepository:
    """Transient cache only — not authoritative."""

    def __init__(self) -> None:
        self._runs: dict[str, AnalysisRunState] = {}
        self._extractions: dict[tuple[str, str, str], TechnicalSignature] = {}
        self._replay: dict[tuple[str, str, str], TechnicalSignature] = {}

    def save(self, state: AnalysisRunState) -> None:
        self._runs[state.run_id] = state

    def get(self, run_id: str) -> AnalysisRunState | None:
        return self._runs.get(run_id)

    def get_extraction_replay(
        self, snapshot_id: str | None, candidate_id: str, evidence_hash: str
    ) -> TechnicalSignature | None:
        if not snapshot_id:
            return None
        return self._replay.get((snapshot_id, candidate_id, evidence_hash))

    def get_extraction(
        self, run_id: str, candidate_id: str, evidence_hash: str
    ) -> TechnicalSignature | None:
        return self._extractions.get((run_id, candidate_id, evidence_hash))

    def save_extraction(
        self,
        *,
        run_id: str,
        candidate_id: str,
        evidence_hash: str,
        signature: TechnicalSignature,
        extraction_payload: dict,
        provenance: dict,
    ) -> None:
        self._extractions[(run_id, candidate_id, evidence_hash)] = signature
        snap = provenance.get("snapshot_id")
        if snap and signature.validation_status == "PASSED":
            self._replay[(snap, candidate_id, evidence_hash)] = signature


def build_run_repository(engine: Engine | None) -> RunRepository | None:
    if engine is not None:
        return PostgresRunRepository(engine)
    return None
