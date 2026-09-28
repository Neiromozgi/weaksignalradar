"""Structured local event log (addendum v1.0.4 observability)."""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}", re.I),
    re.compile(r"(postgresql\+psycopg://)[^@\s]+@", re.I),
    re.compile(r"(?i)(authorization:\s*bearer\s+)\S+"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)\S+"),
)


def log_path() -> Path:
    raw = os.environ.get("WSR_EVENT_LOG_PATH", "").strip()
    if raw:
        return Path(raw)
    return Path(os.environ.get("WSR_LOG_DIR", "logs")) / "snnit-radar.jsonl"


def _redact_text(value: str) -> str:
    out = value
    out = _SECRET_PATTERNS[0].sub("sk-REDACTED", out)
    out = _SECRET_PATTERNS[1].sub(r"\1REDACTED@", out)
    out = _SECRET_PATTERNS[2].sub(r"\1REDACTED", out)
    out = _SECRET_PATTERNS[3].sub(r"\1REDACTED", out)
    return out


def _sanitize_fields(fields: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, val in fields.items():
        if val is None:
            continue
        if isinstance(val, str):
            safe[key] = _redact_text(val)
        elif isinstance(val, (int, float, bool)):
            safe[key] = val
        elif isinstance(val, dict):
            safe[key] = _sanitize_fields(val)
        elif isinstance(val, list):
            safe[key] = [
                _redact_text(x) if isinstance(x, str) else x for x in val if x is not None
            ]
        else:
            safe[key] = _redact_text(str(val))
    return safe


def emit_event(
    event: str,
    *,
    level: str = "INFO",
    run_id: str | None = None,
    mode: str | None = None,
    component: str | None = None,
    status: str | None = None,
    reason_code: str | None = None,
    duration_ms: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    record: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        "level": level,
    }
    if run_id:
        record["run_id"] = run_id
    if mode:
        record["mode"] = mode
    if component:
        record["component"] = component
    if status:
        record["status"] = status
    if reason_code:
        record["reason_code"] = reason_code
    if duration_ms is not None:
        record["duration_ms"] = duration_ms
    if extra:
        record.update(_sanitize_fields(extra))
    line = json.dumps(record, ensure_ascii=False) + "\n"
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)


def read_recent_events(*, limit: int = 50) -> list[dict[str, Any]]:
    path = log_path()
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    tail = lines[-limit:]
    out: list[dict[str, Any]] = []
    for line in tail:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
