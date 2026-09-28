"""Frozen score profile ABCDE_v1 (handoff 11)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScoreProfile:
    score_profile_id: str
    weights: dict[str, float]
    active_features: tuple[str, ...]

    def weighted_score(self, percentiles: dict[str, float | None]) -> float | None:
        total_w = 0.0
        total = 0.0
        for code in self.active_features:
            p = percentiles.get(code)
            if p is None:
                return None
            w = self.weights[code]
            total_w += w
            total += w * p
        if total_w <= 0:
            return None
        return total / total_w


ABCDE_V1 = ScoreProfile(
    score_profile_id="ABCDE_v1",
    active_features=("A", "B", "C", "D", "E"),
    weights={"A": 0.30, "B": 0.20, "C": 0.25, "D": 0.15, "E": 0.10},
)

FEATURE_CONTRACT_VERSION = "ABCDE_v1"
C_FACET_WEIGHTS: dict[str, float] = {
    "object_class": 0.10,
    "function": 0.20,
    "mechanism": 0.35,
    "architecture_or_process": 0.20,
    "key_technical_property": 0.15,
}
B_EPS = 1e-9
