"""Sidecar manifest for frozen LIVE #2 provider LLM cache provenance."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from ..llm.profile import LLM_MODEL
from ..sources.contract import NormalizedSourceDocument
from .llm_cache import cache_key, cache_root, load_cached_json
from .text_norm import normalize_text
from .tmf_types import TMF_PROMPT_VERSION

ProviderStatus = Literal[
    "PROVIDER_OK_FRAMES",
    "PROVIDER_OK_EMPTY",
    "PROVIDER_ERROR",
]

MANIFEST_FILENAME = "provider_cache_manifest.json"
LIVE2_FIXTURE_ID = "live2_replay_v1"


def manifest_path() -> Path:
    return cache_root() / MANIFEST_FILENAME


def load_provider_cache_manifest() -> dict[str, Any] | None:
    path = manifest_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_provider_cache_manifest(payload: dict[str, Any]) -> None:
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _doc_text(doc: NormalizedSourceDocument) -> str:
    return f"{doc.title}\n{doc.abstract or ''}".strip()


def cache_key_for_doc(doc: NormalizedSourceDocument) -> str:
    norm = normalize_text(_doc_text(doc))
    return cache_key(
        model_id=LLM_MODEL or "openai",
        prompt_version=TMF_PROMPT_VERSION,
        normalized_input=norm,
    )


def infer_provider_status(cached: dict[str, Any] | None) -> ProviderStatus:
    if not cached:
        return "PROVIDER_ERROR"
    frames = cached.get("frames")
    if isinstance(frames, list) and len(frames) == 0:
        return "PROVIDER_OK_EMPTY"
    if isinstance(frames, list) and len(frames) > 0:
        return "PROVIDER_OK_FRAMES"
    return "PROVIDER_ERROR"


def build_manifest_entry(
    doc: NormalizedSourceDocument,
    *,
    batch_id: int | None,
    generated_at: str | None = None,
    provider_status: ProviderStatus | None = None,
) -> dict[str, Any]:
    key = cache_key_for_doc(doc)
    cached = load_cached_json(key)
    status = provider_status or infer_provider_status(cached)
    frames = cached.get("frames") if cached else None
    frame_count = len(frames) if isinstance(frames, list) else 0
    return {
        "doc_id": doc.source_document_id,
        "cache_key": key,
        "model_id": LLM_MODEL,
        "prompt_version": TMF_PROMPT_VERSION,
        "provider_status": status,
        "frame_count": frame_count,
        "batch_id": batch_id,
        "generated_at": generated_at,
    }


def build_live2_manifest_from_cache(
    documents: list[NormalizedSourceDocument],
    *,
    tmf_batch_size: int = 9,
    generated_at: str | None = None,
) -> dict[str, Any]:
    ts = generated_at or datetime.now(UTC).isoformat()
    entries = []
    for idx, doc in enumerate(documents):
        batch_id = idx // tmf_batch_size
        entries.append(
            build_manifest_entry(doc, batch_id=batch_id, generated_at=ts, provider_status=None)
        )
    return {
        "fixture_id": LIVE2_FIXTURE_ID,
        "document_count": len(entries),
        "model_id": LLM_MODEL,
        "tmf_prompt_version": TMF_PROMPT_VERSION,
        "documents": entries,
    }


def manifest_entry_for_doc(doc: NormalizedSourceDocument) -> dict[str, Any] | None:
    manifest = load_provider_cache_manifest()
    if not manifest:
        return None
    if manifest.get("fixture_id") != doc.source_snapshot_id:
        return None
    for row in manifest.get("documents") or []:
        if isinstance(row, dict) and row.get("doc_id") == doc.source_document_id:
            return row
    return None


def manifest_enforces_snapshot(snapshot_id: str) -> bool:
    manifest = load_provider_cache_manifest()
    return bool(manifest and manifest.get("fixture_id") == snapshot_id)
