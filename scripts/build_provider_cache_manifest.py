"""Build provider_cache_manifest.json for LIVE #2 from on-disk cache (no network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import os

os.environ.setdefault(
    "WSR_LLM_CACHE_DIR",
    str(ROOT / "src" / "weaksignalradar" / "fasttrack" / "fixtures" / "llm_cache"),
)

from weaksignalradar.fasttrack.corpus.snapshot_loader import load_openalex_works
from weaksignalradar.fasttrack.discovery_v2.provider_cache_manifest import (
    build_live2_manifest_from_cache,
    save_provider_cache_manifest,
)
from weaksignalradar.fasttrack.sources.openalex_ft import OpenAlexFastTrackAdapter


def main() -> int:
    works = load_openalex_works("live2_replay_v1")
    docs = OpenAlexFastTrackAdapter().search_from_fixture(
        works, snapshot_id="live2_replay_v1"
    ).documents
    manifest = build_live2_manifest_from_cache(docs, tmf_batch_size=9)
    save_provider_cache_manifest(manifest)
    print(json.dumps({"documents": manifest["document_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
