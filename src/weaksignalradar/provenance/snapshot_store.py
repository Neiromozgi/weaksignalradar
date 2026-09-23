"""Local-filesystem snapshot storage with checksum.

stage_a_contract.json#storage.snapshot: "local filesystem for raw/redacted
capture with checksum and access/retention note". This module only
writes bytes the caller has already redacted; it does not itself know
about API keys or other secrets.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SnapshotResult:
    """Where a redacted raw response was stored and its checksum."""

    path: str
    content_hash: str
    byte_length: int


@dataclass
class SnapshotStore:
    """Writes redacted raw bytes to disk, content-addressed by sha256.

    Retention/access note: snapshots are written under ``base_dir``
    (defaults to ``SNAPSHOT_DIR`` at call sites) with no secrets inside;
    callers are responsible for redacting response bodies before saving
    if a source could ever echo request parameters back.
    """

    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir = Path(self.base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, raw_bytes: bytes, *, prefix: str) -> SnapshotResult:
        content_hash = hashlib.sha256(raw_bytes).hexdigest()
        safe_prefix = "".join(c if c.isalnum() or c in "-_" else "_" for c in prefix)
        filename = f"{safe_prefix}_{content_hash[:16]}.snapshot"
        path = self.base_dir / filename
        if not path.exists():
            path.write_bytes(raw_bytes)
        return SnapshotResult(path=str(path), content_hash=content_hash, byte_length=len(raw_bytes))
