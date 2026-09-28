"""Source call caps (handoff 07)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceBudget:
    max_calls: int
    calls_used: int = 0

    def consume(self, n: int = 1) -> bool:
        if self.calls_used + n > self.max_calls:
            return False
        self.calls_used += n
        return True

    @property
    def remaining(self) -> int:
        return max(0, self.max_calls - self.calls_used)


DEFAULT_SOURCE_BUDGETS: dict[str, int] = {
    "openalex": 15,
    "cordis": 8,
    "epo_lod": 8,
}

OPENALEX_MAX_PAGES = 6
OPENALEX_MAX_WORKS = 500
OPENALEX_HARD_CUTOFF_SEC = 90.0
CORDIS_HARD_CUTOFF_SEC = 120.0
EPO_HARD_CUTOFF_SEC = 120.0


@dataclass
class BudgetTracker:
    budgets: dict[str, SourceBudget] = field(
        default_factory=lambda: {
            k: SourceBudget(max_calls=v) for k, v in DEFAULT_SOURCE_BUDGETS.items()
        }
    )

    def for_source(self, source_id: str) -> SourceBudget:
        if source_id not in self.budgets:
            self.budgets[source_id] = SourceBudget(max_calls=5)
        return self.budgets[source_id]
