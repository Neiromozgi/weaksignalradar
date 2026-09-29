"""TMF extraction — batched OpenAI Responses API with mandatory validator."""

from __future__ import annotations

from typing import Any

from ..llm.profile import LLM_MODEL
from ..sources.contract import NormalizedSourceDocument
from .llm_cache import cache_key, load_cached_json, save_cached_json
from .llm_run_budget import try_consume_llm_provider_slot
from .openai_common import llm_provider_calls_allowed
from .openai_tmf import call_openai_tmf_batch
from .provider_cache_manifest import manifest_enforces_snapshot, manifest_entry_for_doc
from .runtime_budget import TMF_BATCH_SIZE
from .semantic_non_technology import reject_technology_mechanism_label
from .text_norm import normalize_text
from .tmf_types import TMF_PROMPT_VERSION, FrameDrop, MechanismFrame, TMFExtractionStats
from .tmf_validator import validate_frame

_PROVIDER_CALLS = 0


def provider_calls_made() -> int:
    return _PROVIDER_CALLS


def reset_provider_call_counter() -> None:
    global _PROVIDER_CALLS
    _PROVIDER_CALLS = 0


def record_tmf_provider_batch_call() -> None:
    """Count one OpenAI TMF batch request (populate script and runtime fetch path)."""
    global _PROVIDER_CALLS
    _PROVIDER_CALLS += 1


def _doc_text(doc: NormalizedSourceDocument) -> str:
    return f"{doc.title}\n{doc.abstract or ''}".strip()


def _load_cached_frames(doc: NormalizedSourceDocument) -> list[dict[str, Any]] | None:
    norm_in = normalize_text(_doc_text(doc))
    key = cache_key(
        model_id=LLM_MODEL or "openai",
        prompt_version=TMF_PROMPT_VERSION,
        normalized_input=norm_in,
    )
    entry = manifest_entry_for_doc(doc)
    if entry is not None:
        if str(entry.get("cache_key") or "") != key:
            return None
        status = str(entry.get("provider_status") or "")
        if status == "PROVIDER_ERROR":
            return None
        if status == "PROVIDER_OK_EMPTY":
            return []
    elif manifest_enforces_snapshot(doc.source_snapshot_id):
        return None
    cached = load_cached_json(key)
    if cached and isinstance(cached.get("frames"), list):
        return list(cached["frames"])
    if entry is not None and str(entry.get("provider_status") or "") == "PROVIDER_OK_EMPTY":
        return []
    return None


def _save_cached_frames(doc: NormalizedSourceDocument, frames: list[dict[str, Any]]) -> None:
    norm_in = normalize_text(_doc_text(doc))
    key = cache_key(
        model_id=LLM_MODEL or "openai",
        prompt_version=TMF_PROMPT_VERSION,
        normalized_input=norm_in,
    )
    save_cached_json(key, {"frames": frames, "prompt_version": TMF_PROMPT_VERSION})


def _fetch_missing_via_provider(
    documents: list[NormalizedSourceDocument],
) -> None:
    global _PROVIDER_CALLS
    allow = llm_provider_calls_allowed()
    if not allow:
        return
    pending = [d for d in documents if _load_cached_frames(d) is None]
    if not pending:
        return
    for i in range(0, len(pending), TMF_BATCH_SIZE):
        allowed, _reason = try_consume_llm_provider_slot()
        if not allowed:
            break
        batch = pending[i : i + TMF_BATCH_SIZE]
        result, err = call_openai_tmf_batch(batch)
        record_tmf_provider_batch_call()
        if result is None:
            for doc in batch:
                _save_cached_frames(doc, [])
            continue
        for doc in batch:
            frames = result.get(doc.source_document_id, [])
            _save_cached_frames(doc, frames)


def extract_tmfs(
    documents: list[NormalizedSourceDocument],
    *,
    llm_batch: Any | None = None,
) -> tuple[list[MechanismFrame], TMFExtractionStats, list[FrameDrop]]:
    del llm_batch
    _fetch_missing_via_provider(documents)
    stats = TMFExtractionStats()
    kept: list[MechanismFrame] = []
    drops: list[FrameDrop] = []
    doc_by_id = {d.source_document_id: d for d in documents}

    for doc in documents:
        if not doc.abstract and len(normalize_text(doc.title).split()) < 4:
            continue
        raw_frames = _load_cached_frames(doc)
        if raw_frames is None:
            stats.frames_dropped += 1
            drops.append(
                FrameDrop(doc_id=doc.source_document_id, reason="TMF_CACHE_MISS", mechanism=None)
            )
            continue
        for raw in raw_frames[:3]:
            stats.frames_total += 1
            label = str(raw.get("label") or "UNCERTAIN")
            mechanism = str(raw.get("mechanism") or "")
            span = str(raw.get("evidence_span") or "")
            if label == "TECHNOLOGY_MECHANISM" and reject_technology_mechanism_label(
                mechanism=mechanism, evidence_span=span
            ):
                stats.frames_dropped += 1
                drops.append(
                    FrameDrop(
                        doc_id=doc.source_document_id,
                        reason="NON_TECH_SEMANTIC",
                        mechanism=mechanism,
                    )
                )
                stats.drop_reasons["NON_TECH_SEMANTIC"] = (
                    stats.drop_reasons.get("NON_TECH_SEMANTIC", 0) + 1
                )
                continue
            frame, drop = validate_frame(
                doc_id=doc.source_document_id,
                mechanism=mechanism,
                object=raw.get("object"),
                function=raw.get("function"),
                evidence_span=span,
                label=label,
                doc=doc_by_id.get(doc.source_document_id),
            )
            if drop:
                stats.frames_dropped += 1
                drops.append(drop)
                stats.drop_reasons[drop.reason] = stats.drop_reasons.get(drop.reason, 0) + 1
                continue
            if frame:
                if frame.label == "TECHNOLOGY_MECHANISM" and reject_technology_mechanism_label(
                    mechanism=frame.mechanism, evidence_span=frame.evidence_span
                ):
                    stats.frames_dropped += 1
                    drops.append(
                        FrameDrop(
                            doc_id=doc.source_document_id,
                            reason="NON_TECH_SEMANTIC",
                            mechanism=frame.mechanism,
                        )
                    )
                    stats.drop_reasons["NON_TECH_SEMANTIC"] = (
                        stats.drop_reasons.get("NON_TECH_SEMANTIC", 0) + 1
                    )
                    continue
                stats.frames_kept += 1
                stats.label_distribution[frame.label] = (
                    stats.label_distribution.get(frame.label, 0) + 1
                )
                kept.append(frame)
    return kept, stats, drops
