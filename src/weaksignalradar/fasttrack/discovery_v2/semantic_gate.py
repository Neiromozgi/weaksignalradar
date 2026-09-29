"""Semantic technology gate for mechanism frames and candidate clusters."""

from __future__ import annotations

from .semantic_non_technology import reject_technology_mechanism_label
from .tmf_types import MechanismFrame

TECHNOLOGY_PURITY_MIN = 0.60


def frame_clusterable(frame: MechanismFrame) -> bool:
    if frame.label not in {"TECHNOLOGY_MECHANISM", "UNCERTAIN"}:
        return False
    if frame.label == "TECHNOLOGY_MECHANISM" and reject_technology_mechanism_label(
        mechanism=frame.mechanism, evidence_span=frame.evidence_span
    ):
        return False
    return True


def candidate_gate_label(frames: list[MechanismFrame]) -> str:
    if not frames:
        return "REJECTED_NOT_TECHNOLOGY_LEVEL"
    tech_frames = [
        f
        for f in frames
        if f.label == "TECHNOLOGY_MECHANISM"
        and not reject_technology_mechanism_label(
            mechanism=f.mechanism, evidence_span=f.evidence_span
        )
    ]
    tech = len(tech_frames)
    ratio = tech / len(frames)
    if ratio >= TECHNOLOGY_PURITY_MIN and tech > 0:
        return "TECHNOLOGY"
    return "REJECTED_NOT_TECHNOLOGY_LEVEL"
