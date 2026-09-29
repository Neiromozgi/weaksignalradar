"""Per-run presentation/replay context (CACHE/SNAPSHOT vs LIVE). Not scoring logic."""

from __future__ import annotations

from contextvars import ContextVar

_run_data_mode: ContextVar[str | None] = ContextVar("wsr_run_data_mode", default=None)


def set_run_data_mode(mode: str | None) -> None:
    _run_data_mode.set(mode)


def clear_run_data_mode() -> None:
    _run_data_mode.set(None)


def get_run_data_mode() -> str | None:
    return _run_data_mode.get()


def is_offline_replay_mode() -> bool:
    mode = (get_run_data_mode() or "").upper()
    return mode in ("CACHE", "SNAPSHOT")
