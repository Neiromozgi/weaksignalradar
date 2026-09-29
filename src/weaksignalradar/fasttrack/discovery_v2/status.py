"""Run-level discovery diagnosis codes."""

from __future__ import annotations

from .tmf_types import MechanismFrame


def resolve_discovery_status(
    *,
    technology_frames: list[MechanismFrame],
    largest_technology_cluster_share: float,
    embedding_available: bool,
    partial_sources: bool,
) -> str:
    if not embedding_available:
        return "EMBEDDING_UNAVAILABLE"
    if partial_sources:
        return "PARTIAL_SOURCE_COVERAGE"
    tech_count = sum(1 for f in technology_frames if f.label == "TECHNOLOGY_MECHANISM")
    if tech_count < 10:
        if tech_count == 0:
            return "NO_TECHNICAL_FRAMES"
        return "RETRIEVAL_INSUFFICIENT"
    if largest_technology_cluster_share > 0.25:
        return "DISCOVERY_TOO_MACRO"
    return "DISCOVERY_OK"
