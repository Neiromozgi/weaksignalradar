"""SQLAlchemy models for Stage A storage (stage_a_contract.json).

No V2/V3 verification, bucket, or ranking columns.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    MetaData,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Stable Alembic / naming conventions for reversible migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class SearchRunRow(Base):
    """stage_a_contract.json#SearchRun."""

    __tablename__ = "search_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Optional timezone-aware as_of; unknown/absent must be NULL (not now()).
    as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    requested_sources: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    rules_version: Mapped[str] = mapped_column(String(128), nullable=False)
    code_version: Mapped[str] = mapped_column(String(128), nullable=False)

    documents: Mapped[list[SourceDocumentRow]] = relationship(back_populates="run")


class SourceDocumentRow(Base):
    """stage_a_contract.json#SourceDocument.

    ``source_id`` is unique per ``run_id`` (composite primary key).
    """

    __tablename__ = "source_documents"

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("search_runs.run_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    source_id: Mapped[str] = mapped_column(String(512), primary_key=True)
    origin_url_or_official_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_pointer: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(128), nullable=False)
    coverage: Mapped[str] = mapped_column(String(32), nullable=False)

    author_or_org: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Unknown publication/event/public dates MUST be NULL (contract notes).
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publicly_available_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    primary_origin_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[SearchRunRow] = relationship(back_populates="documents")
    spans: Mapped[list[SourceSpanRow]] = relationship(back_populates="document")


class SourceSpanRow(Base):
    """stage_a_contract.json#SourceSpan — STORAGE_PREPARATION_ONLY.

    No VERIFIED / semantic-validity columns.
    """

    __tablename__ = "source_spans"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "source_id"],
            ["source_documents.run_id", "source_documents.source_id"],
            name="fk_source_spans_run_source_documents",
            ondelete="RESTRICT",
        ),
    )

    source_span_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(512), nullable=False)
    exact_quote: Mapped[str] = mapped_column(Text, nullable=False)
    offset_or_locator: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    document: Mapped[SourceDocumentRow] = relationship(back_populates="spans")


class TaskLogRow(Base):
    """stage_a_contract.json#TaskLog."""

    __tablename__ = "task_log"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    executed_commands: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    exit_codes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    evidence_paths: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    blockers: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
