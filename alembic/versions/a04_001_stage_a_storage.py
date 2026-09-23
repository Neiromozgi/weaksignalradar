"""A-04: initial Stage A storage tables (reversible).

Revision ID: a04_001_stage_a_storage
Revises:
Create Date: 2026-09-23

Tables: search_runs, source_documents, source_spans, task_log.
SourceSpan is storage-preparation only (no VERIFIED semantics).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a04_001_stage_a_storage"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requested_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("rules_version", sa.String(length=128), nullable=False),
        sa.Column("code_version", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_search_runs")),
    )

    op.create_table(
        "source_documents",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=512), nullable=False),
        sa.Column("origin_url_or_official_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("snapshot_pointer", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=128), nullable=False),
        sa.Column("coverage", sa.String(length=32), nullable=False),
        sa.Column("author_or_org", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publicly_available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("primary_origin_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["search_runs.run_id"],
            name=op.f("fk_source_documents_run_id_search_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("run_id", "source_id", name=op.f("pk_source_documents")),
    )

    op.create_table(
        "source_spans",
        sa.Column("source_span_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=512), nullable=False),
        sa.Column("exact_quote", sa.Text(), nullable=False),
        sa.Column("offset_or_locator", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id", "source_id"],
            ["source_documents.run_id", "source_documents.source_id"],
            name="fk_source_spans_run_source_documents",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("source_span_id", name=op.f("pk_source_spans")),
    )

    op.create_table(
        "task_log",
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("executed_commands", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("exit_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_paths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("blockers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("task_id", name=op.f("pk_task_log")),
    )


def downgrade() -> None:
    op.drop_table("source_spans")
    op.drop_table("source_documents")
    op.drop_table("task_log")
    op.drop_table("search_runs")
