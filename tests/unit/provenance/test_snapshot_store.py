"""SnapshotStore unit tests (local filesystem provenance only)."""

from __future__ import annotations

from pathlib import Path

from weaksignalradar.provenance.snapshot_store import SnapshotStore


def test_save_writes_bytes_and_checksum(tmp_path: Path) -> None:
    store = SnapshotStore(base_dir=tmp_path / "snapshots")
    raw = b'{"ok": true}'
    result = store.save(raw, prefix="openalex_search_run1")

    path = Path(result.path)
    assert path.exists()
    assert path.read_bytes() == raw
    assert result.byte_length == len(raw)
    assert len(result.content_hash) == 64
    # filename embeds the first 16 hex chars of the content hash
    assert result.content_hash[:16] in path.name


def test_save_is_idempotent_for_same_content(tmp_path: Path) -> None:
    store = SnapshotStore(base_dir=tmp_path / "snapshots")
    raw = b"same-bytes"
    first = store.save(raw, prefix="p")
    second = store.save(raw, prefix="p")
    assert first.path == second.path
    assert first.content_hash == second.content_hash
