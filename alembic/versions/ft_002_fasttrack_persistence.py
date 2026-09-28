"""FastTrack full persistence schema (addendum v1.0.2).

Revision ID: ft_002
Revises: ft_001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ft_002"
down_revision = "ft_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ft_analysis_runs", sa.Column("domain_id", sa.String(128), nullable=True))
    op.add_column(
        "ft_analysis_runs",
        sa.Column("embedding_profile_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "ft_analysis_runs",
        sa.Column("feature_contract_version", sa.String(64), nullable=True),
    )
    op.add_column(
        "ft_analysis_runs",
        sa.Column("candidate_universe_version", sa.String(64), nullable=True),
    )
    op.add_column("ft_analysis_runs", sa.Column("llm_profile_id", sa.String(128), nullable=True))
    op.add_column(
        "ft_analysis_runs",
        sa.Column("source_coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "ft_analysis_runs",
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "ft_analysis_runs",
        sa.Column("registries", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "ft_analysis_runs",
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "ft_analysis_runs",
        sa.Column("limitations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("ft_analysis_runs", sa.Column("error_text", sa.Text(), nullable=True))
    op.add_column(
        "ft_analysis_runs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE ft_analysis_runs SET domain_id='default', embedding_profile_id='e5_small_v1', "
            "feature_contract_version='ABCDE_v1', candidate_universe_version='cu_v1', "
            "source_coverage='{}'::jsonb, provenance='{}'::jsonb, registries='{}'::jsonb, "
            "warnings='[]'::jsonb, limitations='[]'::jsonb WHERE domain_id IS NULL"
        )
    )
    op.alter_column("ft_analysis_runs", "domain_id", nullable=False)
    op.alter_column("ft_analysis_runs", "embedding_profile_id", nullable=False)
    op.alter_column("ft_analysis_runs", "feature_contract_version", nullable=False)
    op.alter_column("ft_analysis_runs", "candidate_universe_version", nullable=False)
    op.alter_column("ft_analysis_runs", "source_coverage", nullable=False)
    op.alter_column("ft_analysis_runs", "provenance", nullable=False)
    op.alter_column("ft_analysis_runs", "registries", nullable=False)
    op.alter_column("ft_analysis_runs", "warnings", nullable=False)
    op.alter_column("ft_analysis_runs", "limitations", nullable=False)

    op.create_table(
        "ft_source_documents",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("source_document_id", sa.String(length=128), nullable=False),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=128), nullable=False),
        sa.Column("stable_external_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("original_availability_status", sa.String(length=64), nullable=False),
        sa.Column("coverage_state", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ft_analysis_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "source_document_id"),
    )
    op.create_table(
        "ft_candidates",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("technical_signature", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("document_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("organization_count", sa.Integer(), nullable=False),
        sa.Column("source_class_count", sa.Integer(), nullable=False),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ft_analysis_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "candidate_id"),
    )
    op.create_table(
        "ft_snapshots",
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("source_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("storage_ref", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("parent_snapshot_id", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("snapshot_id"),
    )
    op.create_table(
        "ft_source_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("execution_status", sa.String(length=32), nullable=False),
        sa.Column("external_calls", sa.Integer(), nullable=False),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("cap_reached", sa.Boolean(), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ft_analysis_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ft_llm_extractions",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("llm_profile_id", sa.String(length=128), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("extraction_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id", "candidate_id", "evidence_hash"),
    )


def downgrade() -> None:
    op.drop_table("ft_llm_extractions")
    op.drop_table("ft_source_runs")
    op.drop_table("ft_snapshots")
    op.drop_table("ft_candidates")
    op.drop_table("ft_source_documents")
    for col in (
        "completed_at",
        "error_text",
        "limitations",
        "warnings",
        "registries",
        "provenance",
        "source_coverage",
        "llm_profile_id",
        "candidate_universe_version",
        "feature_contract_version",
        "embedding_profile_id",
        "domain_id",
    ):
        op.drop_column("ft_analysis_runs", col)
