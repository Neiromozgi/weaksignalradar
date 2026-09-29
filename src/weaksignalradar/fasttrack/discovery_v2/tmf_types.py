"""TMF data structures and label constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

FrameLabel = Literal[
    "TECHNOLOGY_MECHANISM",
    "APPLICATION_AREA",
    "METHOD_GENERIC",
    "MACRO_THEME",
    "POLICY_REGULATION",
    "UNCERTAIN",
]

TMF_PROMPT_VERSION = "tmf_extraction_v1"

LABEL_CLUSTERABLE = frozenset({"TECHNOLOGY_MECHANISM", "UNCERTAIN"})


@dataclass(slots=True)
class MechanismFrame:
    doc_id: str
    mechanism: str
    object: str | None
    function: str | None
    evidence_span: str
    label: FrameLabel


@dataclass(slots=True)
class FrameDrop:
    doc_id: str
    reason: str
    mechanism: str | None = None


@dataclass(slots=True)
class TMFExtractionStats:
    frames_total: int = 0
    frames_kept: int = 0
    frames_dropped: int = 0
    label_distribution: dict[str, int] = field(default_factory=dict)
    drop_reasons: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frames_total": self.frames_total,
            "frames_kept": self.frames_kept,
            "frames_dropped": self.frames_dropped,
            "label_distribution": dict(self.label_distribution),
            "drop_reason_distribution": dict(self.drop_reasons),
        }
