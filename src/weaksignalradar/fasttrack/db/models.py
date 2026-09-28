"""FastTrack PostgreSQL persistence (ft_* tables, addendum v1.0.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from weaksignalradar.storage.models import Base


class FtAnalysisRunRow(Base):
    __tablename__ = "ft_analysis_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    data_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    snapshot_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    score_profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_universe_version: Mapped[str] = mapped_column(String(64), nullable=False)
    llm_profile_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_coverage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    registries: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    warnings: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    limitations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FtSourceDocumentRow(Base):
    __tablename__ = "ft_source_documents"

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ft_analysis_runs.run_id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_document_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(128), nullable=False)
    stable_external_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    original_availability_status: Mapped[str] = mapped_column(String(64), nullable=False)
    coverage_state: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class FtCandidateRow(Base):
    __tablename__ = "ft_candidates"

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ft_analysis_runs.run_id", ondelete="CASCADE"),
        primary_key=True,
    )
    candidate_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    technical_signature: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    document_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    organization_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_class_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class FtSnapshotRow(Base):
    __tablename__ = "ft_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    source_set: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    storage_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_snapshot_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class FtSourceRunRow(Base):
    __tablename__ = "ft_source_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ft_analysis_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    external_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cap_reached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class FtLlmExtractionRow(Base):
    __tablename__ = "ft_llm_extractions"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    evidence_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    llm_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    extraction_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
