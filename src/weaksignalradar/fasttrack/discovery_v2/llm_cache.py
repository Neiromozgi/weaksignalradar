"""LLM response cache for offline TMF / query planner calls."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def cache_key(*, model_id: str, prompt_version: str, normalized_input: str) -> str:
    raw = f"{model_id}|{prompt_version}|{normalized_input}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_root() -> Path:
    custom = os.environ.get("WSR_LLM_CACHE_DIR", "").strip()
    if custom:
        return Path(custom)
    return Path(__file__).resolve().parents[1] / "fixtures" / "llm_cache"


def load_cached_json(key: str) -> dict[str, Any] | None:
    path = cache_root() / f"{key}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_cached_json(key: str, payload: dict[str, Any]) -> None:
    root = cache_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{key}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
