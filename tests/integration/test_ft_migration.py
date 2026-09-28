"""FastTrack Alembic revision ft_001 (requires DATABASE_URL)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect


def _host_database_url() -> str | None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    return url.replace("@db:", "@127.0.0.1:")


pytestmark = pytest.mark.skipif(
    _host_database_url() is None,
    reason="DATABASE_URL not set",
)


def test_ft_analysis_runs_table_exists_after_upgrade():
    from alembic import command
    from alembic.config import Config

    url = _host_database_url()
    assert url is not None
    os.environ["DATABASE_URL"] = url
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    engine = create_engine(url, pool_pre_ping=True)
    tables = set(inspect(engine).get_table_names())
    assert "ft_analysis_runs" in tables
