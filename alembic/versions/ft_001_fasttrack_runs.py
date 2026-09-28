"""FastTrack analysis run persistence table.

Revision ID: ft_001
Revises: a04_001
Create Date: 2026-09-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ft_001"
down_revision = "a04_001_stage_a_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ft_analysis_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("normalized_query", sa.Text(), nullable=False),
        sa.Column("data_mode", sa.String(length=16), nullable=False),
        sa.Column("snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("score_profile_id", sa.String(length=64), nullable=False),
        sa.Column("state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_ft_analysis_runs")),
    )


def downgrade() -> None:
    op.drop_table("ft_analysis_runs")
