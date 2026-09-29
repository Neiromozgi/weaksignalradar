"""In-memory / serializable FastTrack run state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from ..llm.base import TechnicalSignature
from ..sources.contract import NormalizedSourceDocument

DataMode = Literal["CACHE", "LIVE", "SNAPSHOT"]
RunStatus = Literal["QUEUED", "RUNNING", "COMPLETED", "PARTIAL", "FAILED"]


@dataclass(slots=True)
class CandidateRecord:
    candidate_id: str
    canonical_name: str
    name_ru: str | None
    name_en: str | None
    aliases: list[str]
    state: str
    document_ids: list[str]
    first_observed_year: int | None
    document_count: int
    organization_count: int
    source_class_count: int
    signature: TechnicalSignature | None = None
    yearly_stats: list[dict[str, Any]] = field(default_factory=list)
    features: dict[str, dict[str, Any]] = field(default_factory=dict)
    filters: list[dict[str, Any]] = field(default_factory=list)
    score: float | None = None
    rank: int | None = None
    ranking_status: str | None = None
    fwci_diagnostic: float | None = None
    bootstrap_status: str = "NOT_REQUESTED"
    d_diagnostics: dict[str, Any] = field(default_factory=dict)
    decision_explanation: dict[str, Any] | None = None
    discovery_frames: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class AnalysisRunState:
    run_id: str
    normalized_query: str
    domain_id: str
    data_mode: DataMode
    snapshot_id: str | None
    status: RunStatus
    score_profile_id: str
    feature_contract_version: str
    candidate_universe_version: str
    embedding_model_id: str
    llm_model_id: str | None
    coverage_summary: dict[str, Any]
    documents: list[NormalizedSourceDocument] = field(default_factory=list)
    candidates: list[CandidateRecord] = field(default_factory=list)
    registries: dict[str, list[str]] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    source_runs: list[dict[str, Any]] = field(default_factory=list)
    started_at: str | None = None
    finished_at: str | None = None
