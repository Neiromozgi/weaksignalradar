"""Immutable snapshot corpus loader (handoff 16)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _package_fixture_path(snapshot_id: str) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / snapshot_id / "openalex_works.json"


def _runtime_snapshot_path(snapshot_id: str) -> Path | None:
    root = Path(os.environ.get("SNAPSHOT_DIR", "snapshots"))
    path = root / "benchmark" / snapshot_id / "openalex_works.json"
    return path if path.is_file() else None


def load_openalex_works(snapshot_id: str) -> list[dict[str, Any]]:
    candidates = [_package_fixture_path(snapshot_id), _runtime_snapshot_path(snapshot_id)]
    for path in candidates:
        if path is None:
            continue
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "results" in data:
                return list(data["results"])
            if isinstance(data, list):
                return data
            raise ValueError(f"unexpected snapshot shape: {path}")
    raise FileNotFoundError(f"snapshot not found for id={snapshot_id!r}")
