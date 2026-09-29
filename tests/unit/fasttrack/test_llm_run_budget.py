"""Run-level LLM provider budget enforcement."""

from __future__ import annotations

import time

from weaksignalradar.fasttrack.discovery_v2.llm_run_budget import RunLLMBudget
from weaksignalradar.fasttrack.discovery_v2.runtime_budget import (
    HARD_LLM_CALL_LIMIT,
    LIVE_HARD_TIMEOUT_SEC,
    TARGET_LLM_CALLS,
)


def test_hard_limit_blocks_call_61():
    budget = RunLLMBudget(calls_used=HARD_LLM_CALL_LIMIT)
    allowed, reason = budget.try_begin_provider_call()
    assert allowed is False
    assert reason == "LLM_CALL_BUDGET_EXCEEDED"
    assert budget.budget_status == "PARTIAL"


def test_allows_sixtieth_call():
    budget = RunLLMBudget(calls_used=HARD_LLM_CALL_LIMIT - 1)
    allowed, reason = budget.try_begin_provider_call()
    assert allowed is True
    assert reason is None
    assert budget.calls_used == HARD_LLM_CALL_LIMIT


def test_target_40_warning_does_not_block():
    budget = RunLLMBudget(calls_used=TARGET_LLM_CALLS)
    allowed, _ = budget.try_begin_provider_call()
    assert allowed is True
    assert budget.target_warning_emitted is True
    assert budget.budget_status == "TARGET_EXCEEDED_WARNING"


def test_time_budget_blocks_next_call(monkeypatch):
    budget = RunLLMBudget(
        started_monotonic=time.monotonic() - LIVE_HARD_TIMEOUT_SEC - 1,
        hard_timeout_sec=LIVE_HARD_TIMEOUT_SEC,
    )
    allowed, reason = budget.try_begin_provider_call()
    assert allowed is False
    assert reason == "LLM_TIME_BUDGET_EXCEEDED"
