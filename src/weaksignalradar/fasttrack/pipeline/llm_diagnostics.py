"""Aggregate per-run LLM counters (no prompts, evidence, or secrets)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..llm.base import TechnicalSignature


@dataclass
class LLMDiagnostics:
    llm_candidates_attempted: int = 0
    llm_provider_calls: int = 0
    llm_replayed: int = 0
    llm_ok: int = 0
    llm_partial: int = 0
    llm_failed: int = 0
    llm_not_configured: int = 0
    llm_duration_ms_total: int = 0
    _t0: float | None = field(default=None, repr=False)

    def begin_candidate(self) -> None:
        self.llm_candidates_attempted += 1

    def mark_replay(self, sig: TechnicalSignature) -> None:
        self.llm_replayed += 1
        self._classify(sig)

    def begin_provider_call(self) -> None:
        self.llm_provider_calls += 1
        self._t0 = time.monotonic()

    def finish_provider_call(self, sig: TechnicalSignature) -> None:
        if self._t0 is not None:
            self.llm_duration_ms_total += int((time.monotonic() - self._t0) * 1000)
            self._t0 = None
        self._classify(sig)

    def _classify(self, sig: TechnicalSignature) -> None:
        status = (sig.extraction_status or "").upper()
        if status == "NOT_CONFIGURED":
            self.llm_not_configured += 1
        elif status == "OK":
            self.llm_ok += 1
        elif status == "PARTIAL":
            self.llm_partial += 1
        else:
            self.llm_failed += 1

    def as_dict(self) -> dict[str, int]:
        return {
            "llm_candidates_attempted": self.llm_candidates_attempted,
            "llm_provider_calls": self.llm_provider_calls,
            "llm_replayed": self.llm_replayed,
            "llm_ok": self.llm_ok,
            "llm_partial": self.llm_partial,
            "llm_failed": self.llm_failed,
            "llm_not_configured": self.llm_not_configured,
            "llm_duration_ms_total": self.llm_duration_ms_total,
        }


def provenance_has_secret_material(provenance: dict[str, Any]) -> bool:
    blob = str(provenance).lower()
    forbidden = ("authorization", "bearer ", "openai_api_key", "sk-", "api_key")
    return any(x in blob for x in forbidden)
