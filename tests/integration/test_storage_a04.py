"""A-04 storage / migration / integrity checks against PostgreSQL.

Requires DATABASE_URL in the environment (local test credentials only).
Skipped when DATABASE_URL is unset so unit-only runs remain possible.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from weaksignalradar.provenance.snapshot_store import SnapshotStore
from weaksignalradar.storage.models import (
    SearchRunRow,
    SourceDocumentRow,
    SourceSpanRow,
    TaskLogRow,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _database_url() -> str | None:
    url = os.environ.get("DATABASE_URL", "").strip()
    return url or None


pytestmark = pytest.mark.skipif(
    _database_url() is None,
    reason="DATABASE_URL not set (A-04 integration requires local PostgreSQL)",
)


def _alembic_config(url: str) -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    # env.py reads DATABASE_URL; ensure it matches.
    os.environ["DATABASE_URL"] = url
    return cfg


def _drop_all_public_tables(url: str) -> None:
    """Reset public schema for a clean-DB migration cycle (test-only)."""
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    engine.dispose()


def test_migration_upgrade_downgrade_upgrade_cycle() -> None:
    url = _database_url()
    assert url is not None
    _drop_all_public_tables(url)
    cfg = _alembic_config(url)

    command.upgrade(cfg, "head")
    engine = create_engine(url, pool_pre_ping=True)
    tables = set(inspect(engine).get_table_names())
    assert {
        "search_runs",
        "source_documents",
        "source_spans",
        "task_log",
        "alembic_version",
    }.issubset(tables)

    command.downgrade(cfg, "base")
    tables_after_down = set(inspect(engine).get_table_names())
    assert "search_runs" not in tables_after_down
    assert "source_documents" not in tables_after_down
    assert "source_spans" not in tables_after_down
    assert "task_log" not in tables_after_down

    command.upgrade(cfg, "head")
    tables_again = set(inspect(engine).get_table_names())
    assert {
        "search_runs",
        "source_documents",
        "source_spans",
        "task_log",
    }.issubset(tables_again)
    engine.dispose()


def _seed_run(session: Session, run_id: str) -> SearchRunRow:
    row = SearchRunRow(
        run_id=run_id,
        query="sensing technologies for environmental monitoring",
        scope={"filters": []},
        as_of=None,
        params={"per-page": 5},
        requested_sources=["openalex"],
        started_at=datetime.now(UTC),
        status="IN_PROGRESS",
        rules_version="A-1.0",
        code_version="0.1.0",
    )
    session.add(row)
    session.flush()
    return row


def test_fk_cross_run_document_rejected() -> None:
    url = _database_url()
    assert url is not None
    engine = create_engine(url, pool_pre_ping=True)
    with Session(engine) as session:
        run_a = str(uuid.uuid4())
        _seed_run(session, run_a)
        session.commit()

    with Session(engine) as session:
        orphan = SourceDocumentRow(
            run_id=str(uuid.uuid4()),  # never created
            source_id="openalex:W1",
            origin_url_or_official_id="https://openalex.org/W1",
            title="x",
            retrieved_at=datetime.now(UTC),
            request_params={},
            content_hash="0" * 64,
            snapshot_pointer="/tmp/missing.snapshot",
            source_type="openalex_work",
            coverage="SEARCHED_OK",
        )
        session.add(orphan)
        with pytest.raises(IntegrityError):
            session.commit()
    engine.dispose()


def test_fk_span_requires_matching_document() -> None:
    url = _database_url()
    assert url is not None
    engine = create_engine(url, pool_pre_ping=True)
    run_id = str(uuid.uuid4())
    with Session(engine) as session:
        _seed_run(session, run_id)
        session.add(
            SourceDocumentRow(
                run_id=run_id,
                source_id="openalex:W2",
                origin_url_or_official_id="https://openalex.org/W2",
                title="doc",
                retrieved_at=datetime.now(UTC),
                request_params={},
                content_hash="a" * 64,
                snapshot_pointer="/tmp/w2.snapshot",
                source_type="openalex_work",
                coverage="SEARCHED_OK",
            )
        )
        session.commit()

    with Session(engine) as session:
        session.add(
            SourceSpanRow(
                source_span_id=str(uuid.uuid4()),
                run_id=run_id,
                source_id="openalex:OTHER_RUN_DOC",
                exact_quote="quote",
                offset_or_locator="0:5",
                sha256="b" * 64,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
    engine.dispose()


def test_nullable_dates_persist_as_null() -> None:
    url = _database_url()
    assert url is not None
    engine = create_engine(url, pool_pre_ping=True)
    run_id = str(uuid.uuid4())
    with Session(engine) as session:
        _seed_run(session, run_id)
        session.add(
            SourceDocumentRow(
                run_id=run_id,
                source_id="openalex:W3",
                origin_url_or_official_id="https://openalex.org/W3",
                title="undated",
                retrieved_at=datetime.now(UTC),
                request_params={"search": "x"},
                content_hash="c" * 64,
                snapshot_pointer="/tmp/w3.snapshot",
                source_type="openalex_work",
                coverage="SEARCHED_OK",
                published_at=None,
                event_at=None,
                publicly_available_at=None,
            )
        )
        session.commit()

    with Session(engine) as session:
        doc = session.get(SourceDocumentRow, (run_id, "openalex:W3"))
        assert doc is not None
        assert doc.published_at is None
        assert doc.event_at is None
        assert doc.publicly_available_at is None
        run = session.get(SearchRunRow, run_id)
        assert run is not None
        assert run.as_of is None
    engine.dispose()


def test_snapshot_pointer_and_checksum(tmp_path: Path) -> None:
    url = _database_url()
    assert url is not None
    raw = b'{"id":"https://openalex.org/W4","title":"snap"}'
    store = SnapshotStore(base_dir=tmp_path)
    snap = store.save(raw, prefix="openalex_search_test")
    assert snap.content_hash == hashlib.sha256(raw).hexdigest()
    assert Path(snap.path).is_file()

    engine = create_engine(url, pool_pre_ping=True)
    run_id = str(uuid.uuid4())
    with Session(engine) as session:
        _seed_run(session, run_id)
        session.add(
            SourceDocumentRow(
                run_id=run_id,
                source_id="openalex:W4",
                origin_url_or_official_id="https://openalex.org/W4",
                title="snap",
                retrieved_at=datetime.now(UTC),
                request_params={},
                content_hash=snap.content_hash,
                snapshot_pointer=snap.path,
                source_type="openalex_work",
                coverage="SEARCHED_OK",
            )
        )
        session.commit()

    with Session(engine) as session:
        doc = session.get(SourceDocumentRow, (run_id, "openalex:W4"))
        assert doc is not None
        assert doc.snapshot_pointer == snap.path
        assert doc.content_hash == snap.content_hash
        assert len(doc.content_hash) == 64
    engine.dispose()


def test_task_log_roundtrip() -> None:
    url = _database_url()
    assert url is not None
    engine = create_engine(url, pool_pre_ping=True)
    task_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            TaskLogRow(
                task_id=task_id,
                stage="A-04",
                status="READY_FOR_TEST",
                started_at=now,
                updated_at=now,
                commit_sha="0" * 40,
                executed_commands=["alembic upgrade head", "pytest -q"],
                exit_codes=[0, 0],
                evidence_paths=["tests/integration/test_storage_a04.py"],
                blockers=[],
            )
        )
        session.commit()

    with Session(engine) as session:
        row = session.get(TaskLogRow, task_id)
        assert row is not None
        assert row.status == "READY_FOR_TEST"
        assert row.executed_commands == ["alembic upgrade head", "pytest -q"]
        assert row.exit_codes == [0, 0]
        assert row.blockers == []
    engine.dispose()
