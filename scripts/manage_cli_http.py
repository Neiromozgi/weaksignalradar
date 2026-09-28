"""Operator HTTP helpers for manage.cmd (in-container, no secrets)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def _get(path: str, timeout: float) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as resp:
        return json.loads(resp.read())


def diagnostics() -> int:
    try:
        data = _get("/api/v1/diagnostics", timeout=60)
    except TimeoutError:
        print("Diagnostics request timed out after 60 seconds.")
        print(
            "On a cold backend start, the first call may take longer while the embedding runtime loads."
        )
        return 1
    except urllib.error.URLError as exc:
        print(f"Backend request failed for /api/v1/diagnostics: {exc}")
        return 1
    sources = data.get("sources") or {}
    print("SNNIT RADAR (WSR) diagnostics")
    print("Service:", data.get("service"))
    print("Database:", data.get("database"))
    print("Embedding:", data.get("embedding"))
    print("LLM:", data.get("llm"), "(key", str(data.get("openai_api_key")) + ")")
    print("OpenAlex:", sources.get("openalex"))
    print("CORDIS:", sources.get("cordis"))
    print("EPO:", sources.get("epo_lod"))
    print("Analyses recorded:", data.get("analyses_recorded"))
    print("Last run:", data.get("last_run_id"), "status=" + str(data.get("last_run_status")))
    print("Last snapshot:", data.get("last_snapshot_id"))
    return 0


def llm_status() -> int:
    try:
        data = _get("/api/v1/config/llm", timeout=15)
    except urllib.error.URLError as exc:
        print(f"Backend request failed for /api/v1/config/llm: {exc}")
        return 1
    print("profile_id=" + str(data.get("profile_id", "")))
    print("provider=" + str(data.get("provider", "")))
    print("model=" + str(data.get("model", "")))
    print("runtime_status=" + str(data.get("status", "")))
    print("openai_api_key=" + str(data.get("openai_api_key", "")))
    return 0


def sources() -> int:
    try:
        data = _get("/api/v1/config/sources", timeout=15)
    except urllib.error.URLError as exc:
        print(f"Backend request failed for /api/v1/config/sources: {exc}")
        return 1
    for item in data.get("sources") or []:
        detail = item.get("detail") or ""
        print(f"{item.get('source_id')}: status={item.get('status')} {detail}".rstrip())
    return 0


def snapshots() -> int:
    try:
        data = _get("/api/v1/snapshots", timeout=15)
    except urllib.error.URLError as exc:
        print(f"Backend request failed for /api/v1/snapshots: {exc}")
        return 1
    items = data.get("snapshots") or []
    if not items:
        print("(no snapshots listed)")
        return 0
    for item in items:
        print(
            f"snapshot_id={item.get('snapshot_id')} "
            f"mode={item.get('mode')} immutable={item.get('immutable')}"
        )
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: manage_cli_http.py diagnostics|llm-status|sources|snapshots")
        return 1
    cmd = sys.argv[1].lower()
    if cmd == "diagnostics":
        return diagnostics()
    if cmd == "llm-status":
        return llm_status()
    if cmd == "sources":
        return sources()
    if cmd == "snapshots":
        return snapshots()
    print(f"Unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
