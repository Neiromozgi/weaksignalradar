"""Shared OpenAlex work → FastTrack document normalization (LIVE + fixture/replay)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contract import CoverageState, NormalizedSourceDocument, OriginalAvailability


def _coerce_position(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            pos = int(stripped)
        except ValueError:
            return None
        return pos if pos >= 0 else None
    return None


def reconstruct_abstract(inverted: Any) -> str | None:
    if not inverted or not isinstance(inverted, dict):
        return None
    max_pos = -1
    slots: list[tuple[int, str]] = []
    for word, positions in inverted.items():
        if not isinstance(word, str) or not word.strip():
            continue
        if not isinstance(positions, list):
            continue
        for raw_pos in positions:
            pos = _coerce_position(raw_pos)
            if pos is None:
                continue
            max_pos = max(max_pos, pos)
            slots.append((pos, word))
    if max_pos < 0:
        return None
    words: list[str] = [""] * (max_pos + 1)
    for pos, word in slots:
        if not words[pos]:
            words[pos] = word
    text = " ".join(w for w in words if w).strip()
    return text or None


def collect_organization_names(work: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    orgs: list[str] = []
    for auth in work.get("authorships") or []:
        if not isinstance(auth, dict):
            continue
        for inst in auth.get("institutions") or []:
            if not isinstance(inst, dict):
                continue
            name = inst.get("display_name")
            if name and name not in seen:
                seen.add(name)
                orgs.append(str(name))
    return orgs


def normalize_openalex_work(
    work: dict[str, Any],
    *,
    snapshot_id: str,
    retrieved_at: str | None = None,
    coverage_state: CoverageState = CoverageState.FOUND,
) -> NormalizedSourceDocument:
    wid = str(work.get("id") or work.get("openalex_id") or "")
    title = (work.get("title") or work.get("display_name") or "Untitled").strip()
    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
    year = work.get("publication_year")
    ids_map = work.get("ids") or {}
    doi = ids_map.get("doi") if isinstance(ids_map, dict) else None
    landing = (work.get("primary_location") or {}).get("landing_page_url") or wid
    raw_hash = hashlib.sha256(json.dumps(work, sort_keys=True).encode()).hexdigest()
    orgs = collect_organization_names(work)
    avail = (
        OriginalAvailability.ABSTRACT_AVAILABLE
        if abstract
        else OriginalAvailability.METADATA_ONLY
    )
    ts = retrieved_at or datetime.now(UTC).isoformat()
    return NormalizedSourceDocument(
        source_document_id=f"doc_{hashlib.sha256(wid.encode()).hexdigest()[:16]}",
        source_id=wid,
        source_type="openalex_work",
        stable_external_id=wid,
        title=title,
        year=int(year) if year is not None else None,
        canonical_url=str(landing),
        doi=doi,
        original_availability_status=avail,
        metadata_json={"openalex": work},
        source_snapshot_id=snapshot_id,
        retrieved_at=ts,
        content_hash_of_api_record=raw_hash,
        coverage_state=coverage_state,
        organization_names=orgs,
        abstract=abstract,
    )


def index_works_from_snapshot(snapshot_pointer: str | None) -> dict[str, dict[str, Any]]:
    """Map OpenAlex work id → raw work dict from a saved search/fetch snapshot."""
    if not snapshot_pointer:
        return {}
    path = Path(snapshot_pointer)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        items = payload["results"]
    elif isinstance(payload, dict) and payload.get("id"):
        items = [payload]
    else:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict):
            wid = str(item.get("id") or item.get("openalex_id") or "")
            if wid:
                out[wid] = item
    return out


def openalex_id_from_source_document(source_id: str, primary_origin_id: str | None) -> str:
    if primary_origin_id:
        return str(primary_origin_id)
    if source_id.startswith("openalex:"):
        return source_id.split(":", 1)[1]
    return source_id
