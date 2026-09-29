"""Shared per-run LLM provider call budget (planner + TMF + signatures)."""

from __future__ import annotations

import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from .runtime_budget import (
    HARD_LLM_CALL_LIMIT,
    LIVE_HARD_TIMEOUT_SEC,
    TARGET_LLM_CALLS,
)

_active_budget: ContextVar[RunLLMBudget | None] = ContextVar("wsr_run_llm_budget", default=None)


@dataclass
class RunLLMBudget:
    calls_used: int = 0
    target_calls: int = TARGET_LLM_CALLS
    hard_limit: int = HARD_LLM_CALL_LIMIT
    started_monotonic: float = field(default_factory=time.monotonic)
    hard_timeout_sec: float = LIVE_HARD_TIMEOUT_SEC
    target_warning_emitted: bool = False
    budget_status: str = "OK"
    blocked_reason: str | None = None

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started_monotonic) * 1000)

    def _time_exceeded(self) -> bool:
        return (time.monotonic() - self.started_monotonic) >= self.hard_timeout_sec

    def try_begin_provider_call(self) -> tuple[bool, str | None]:
        if self.blocked_reason:
            return False, self.blocked_reason
        if self._time_exceeded():
            self.budget_status = "PARTIAL"
            self.blocked_reason = "LLM_TIME_BUDGET_EXCEEDED"
            return False, self.blocked_reason
        if self.calls_used >= self.hard_limit:
            self.budget_status = "PARTIAL"
            self.blocked_reason = "LLM_CALL_BUDGET_EXCEEDED"
            return False, self.blocked_reason
        if self.calls_used >= self.target_calls and not self.target_warning_emitted:
            self.target_warning_emitted = True
            if self.budget_status == "OK":
                self.budget_status = "TARGET_EXCEEDED_WARNING"
        self.calls_used += 1
        return True, None

    def as_provenance(self) -> dict[str, Any]:
        return {
            "llm_calls_used": self.calls_used,
            "llm_target_calls": self.target_calls,
            "llm_hard_limit": self.hard_limit,
            "llm_elapsed_ms": self.elapsed_ms(),
            "llm_budget_status": self.budget_status,
            "llm_budget_blocked_reason": self.blocked_reason,
        }


def begin_run_llm_budget() -> RunLLMBudget:
    budget = RunLLMBudget()
    _active_budget.set(budget)
    return budget


def get_active_run_llm_budget() -> RunLLMBudget | None:
    return _active_budget.get()


def clear_run_llm_budget() -> None:
    _active_budget.set(None)


def try_consume_llm_provider_slot() -> tuple[bool, str | None]:
    budget = get_active_run_llm_budget()
    if budget is None:
        return True, None
    return budget.try_begin_provider_call()
