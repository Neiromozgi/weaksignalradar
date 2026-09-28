"""Immutable LIVE snapshot registration and storage."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..db import models as m
from ..sources.contract import CoverageState, NormalizedSourceDocument, OriginalAvailability


def snapshot_root() -> Path:
    return Path(os.environ.get("SNAPSHOT_DIR", "snapshots")) / "benchmark"


def _doc_to_json(d: NormalizedSourceDocument) -> dict[str, Any]:
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


def _doc_from_json(raw: dict[str, Any]) -> NormalizedSourceDocument:
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


def register_live_snapshot(
    *,
    engine: Engine,
    query: str,
    documents: list[NormalizedSourceDocument],
    source_coverage: dict[str, Any],
    refresh_id: str,
) -> dict[str, Any]:
    if not documents:
        raise ValueError("cannot register empty snapshot")
    snapshot_id = f"snap_{uuid.uuid4().hex[:16]}"
    created = datetime.now(UTC)
    for doc in documents:
        doc.source_snapshot_id = snapshot_id

    payload = {
        "meta": {
            "snapshot_id": snapshot_id,
            "query": query,
            "refresh_id": refresh_id,
            "created_at": created.isoformat(),
            "immutable": True,
            "source_coverage": source_coverage,
        },
        "documents": [_doc_to_json(d) for d in documents],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    content_hash = hashlib.sha256(raw).hexdigest()

    root = snapshot_root()
    root.mkdir(parents=True, exist_ok=True)
    snap_dir = root / snapshot_id
    snap_dir.mkdir(parents=True, exist_ok=True)
    path = snap_dir / "corpus.json"
    path.write_bytes(raw)

    with Session(engine) as session:
        session.add(
            m.FtSnapshotRow(
                snapshot_id=snapshot_id,
                run_id=None,
                created_at=created,
                mode="LIVE_REFRESH",
                source_set=list(source_coverage.keys()),
                storage_ref=str(path),
                content_hash=content_hash,
                document_count=len(documents),
                parent_snapshot_id=None,
            )
        )
        session.commit()

    return {
        "snapshot_id": snapshot_id,
        "content_hash": content_hash,
        "storage_ref": str(path),
        "document_count": len(documents),
        "immutable": True,
    }


def load_snapshot_documents(snapshot_id: str) -> list[NormalizedSourceDocument] | None:
    path = snapshot_root() / snapshot_id / "corpus.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        docs = data.get("documents") or []
        return [_doc_from_json(d) for d in docs]
    return None


def list_snapshot_catalog(engine: Engine | None) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = [
        {
            "snapshot_id": "ft_bench_v1",
            "source": "openalex",
            "immutable": True,
            "mode": "BENCHMARK_FIXTURE",
            "document_count": None,
        }
    ]
    if engine is None:
        return catalog
    with Session(engine) as session:
        rows = session.scalars(
            select(m.FtSnapshotRow).order_by(m.FtSnapshotRow.created_at.desc())
        ).all()
        for row in rows:
            if row.snapshot_id == "ft_bench_v1":
                continue
            catalog.append(
                {
                    "snapshot_id": row.snapshot_id,
                    "source": ",".join(str(s) for s in (row.source_set or [])),
                    "immutable": True,
                    "mode": row.mode,
                    "document_count": row.document_count,
                    "content_hash": row.content_hash,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )
    return catalog


def get_snapshot_metadata(engine: Engine | None, snapshot_id: str) -> dict[str, Any] | None:
    if snapshot_id == "ft_bench_v1":
        return {
            "snapshot_id": snapshot_id,
            "immutable": True,
            "mode": "BENCHMARK_FIXTURE",
            "sources": ["openalex"],
        }
    if engine is None:
        return None
    with Session(engine) as session:
        row = session.get(m.FtSnapshotRow, snapshot_id)
        if row is None:
            return None
        return {
            "snapshot_id": row.snapshot_id,
            "immutable": True,
            "mode": row.mode,
            "sources": list(row.source_set or []),
            "document_count": row.document_count,
            "content_hash": row.content_hash,
            "storage_ref": row.storage_ref,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
