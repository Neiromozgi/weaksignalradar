"""Populate LIVE #2 offline LLM cache (authorized <=10 OpenAI calls)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from weaksignalradar.fasttrack.corpus.snapshot_loader import load_openalex_works
from weaksignalradar.fasttrack.discovery_v2.llm_cache import cache_root
from weaksignalradar.fasttrack.discovery_v2.openai_tmf import call_openai_tmf_batch
from weaksignalradar.fasttrack.discovery_v2.provider_cache_manifest import (
    LIVE2_FIXTURE_ID,
    build_manifest_entry,
    infer_provider_status,
    save_provider_cache_manifest,
)
from weaksignalradar.fasttrack.discovery_v2.query_planner import plan_domain_query
from weaksignalradar.fasttrack.discovery_v2.tmf_extract import (
    _save_cached_frames,
    provider_calls_made,
    record_tmf_provider_batch_call,
    reset_provider_call_counter,
)
from weaksignalradar.fasttrack.sources.openalex_ft import OpenAlexFastTrackAdapter

LIVE2_BATCH_SIZE = 9
MAX_TMF_BATCHES = 9


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Populate LIVE #2 fixture LLM cache.")
    parser.add_argument(
        "--force-current-fixture",
        action="store_true",
        help="Refresh only the 75 live2_replay_v1 cache keys and update manifest.",
    )
    return parser.parse_args()


def main() -> int:
    import os

    args = _parse_args()
    os.environ.setdefault("WSR_ALLOW_LLM_PROVIDER", "1")
    os.environ.setdefault(
        "WSR_LLM_CACHE_DIR",
        str(ROOT / "src" / "weaksignalradar" / "fasttrack" / "fixtures" / "llm_cache"),
    )
    reset_provider_call_counter()
    generated_at = datetime.now(UTC).isoformat()
    planner = plan_domain_query("Финтех")
    planner_calls = 1 if planner.get("planner_status") == "PLANNER_OK" else 0
    works = load_openalex_works("live2_replay_v1")
    docs = OpenAlexFastTrackAdapter().search_from_fixture(
        works, snapshot_id="live2_replay_v1"
    ).documents
    manifest_rows: list[dict] = []
    tmf_batches = 0
    for i in range(0, len(docs), LIVE2_BATCH_SIZE):
        if tmf_batches >= MAX_TMF_BATCHES:
            break
        batch = docs[i : i + LIVE2_BATCH_SIZE]
        batch_id = tmf_batches
        if not args.force_current_fixture:
            result, err = call_openai_tmf_batch(batch)
            record_tmf_provider_batch_call()
            tmf_batches += 1
            if result is None:
                print(json.dumps({"error": err, "batch": tmf_batches}, ensure_ascii=False))
                continue
            for doc in batch:
                frames = result.get(doc.source_document_id, [])
                _save_cached_frames(doc, frames)
            continue
        result, err = call_openai_tmf_batch(batch)
        record_tmf_provider_batch_call()
        tmf_batches += 1
        if result is None:
            print(json.dumps({"error": err, "batch": tmf_batches}, ensure_ascii=False))
            for doc in batch:
                manifest_rows.append(
                    build_manifest_entry(
                        doc,
                        batch_id=batch_id,
                        generated_at=generated_at,
                        provider_status="PROVIDER_ERROR",
                    )
                )
            continue
        for doc in batch:
            frames = result.get(doc.source_document_id, [])
            _save_cached_frames(doc, frames)
            status = (
                "PROVIDER_OK_EMPTY" if len(frames) == 0 else infer_provider_status({"frames": frames})
            )
            manifest_rows.append(
                build_manifest_entry(
                    doc,
                    batch_id=batch_id,
                    generated_at=generated_at,
                    provider_status=status,
                )
            )
    if args.force_current_fixture and manifest_rows:
        save_provider_cache_manifest(
            {
                "fixture_id": LIVE2_FIXTURE_ID,
                "document_count": len(manifest_rows),
                "model_id": planner.get("model_id") or manifest_rows[0].get("model_id"),
                "tmf_prompt_version": manifest_rows[0].get("prompt_version"),
                "planner_status": planner.get("planner_status"),
                "generated_at": generated_at,
                "documents": manifest_rows,
            }
        )
    summary = {
        "cache_root": str(cache_root()),
        "force_current_fixture": bool(args.force_current_fixture),
        "planner_status": planner.get("planner_status"),
        "planner_calls": planner_calls,
        "tmf_batches": tmf_batches,
        "provider_calls_total": planner_calls + tmf_batches,
        "tmf_provider_calls_counter": provider_calls_made(),
        "documents": len(docs),
        "manifest_documents": len(manifest_rows) if manifest_rows else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
