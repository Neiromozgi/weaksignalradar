"""Frozen real-E5 vectors for offline clustering regression (no model download)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config.embedding_profile import E5_SMALL_V1
from ..embedding.backend import EmbeddingBackend
from .mechanism_cluster import frame_passage_for_representation
from .threshold import CLUSTERING_REPRESENTATION
from .tmf_types import MechanismFrame


def calibration_fixture_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "discovery_v2_e5_live2_34_v1.json"
    )


def load_calibration_frames() -> list[MechanismFrame]:
    data = json.loads(calibration_fixture_path().read_text(encoding="utf-8"))
    out: list[MechanismFrame] = []
    for row in data["frames"]:
        out.append(
            MechanismFrame(
                doc_id=str(row["doc_id"]),
                mechanism=str(row["mechanism"]),
                object=row.get("object"),
                function=row.get("function"),
                evidence_span=str(row["evidence_span"]),
                label=row.get("label") or "TECHNOLOGY_MECHANISM",
            )
        )
    return out


class FrozenE5CalibrationBackend(EmbeddingBackend):
    """Maps passage text to precomputed E5 vectors from the calibration fixture."""

    profile = E5_SMALL_V1

    def __init__(self, fixture: dict[str, Any] | None = None) -> None:
        data = fixture or json.loads(calibration_fixture_path().read_text(encoding="utf-8"))
        rep_key = "A_mechanism"
        frames = data["frames"]
        vectors = data["vectors_by_representation"][rep_key]
        self._by_passage: dict[str, list[float]] = {}
        for row, vec in zip(frames, vectors, strict=True):
            frame = MechanismFrame(
                doc_id=str(row["doc_id"]),
                mechanism=str(row["mechanism"]),
                object=row.get("object"),
                function=row.get("function"),
                evidence_span=str(row["evidence_span"]),
                label=row.get("label") or "TECHNOLOGY_MECHANISM",
            )
            passage = frame_passage_for_representation(
                frame, representation=CLUSTERING_REPRESENTATION
            )
            self._by_passage[passage] = list(vec)

    def encode(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = self._by_passage.get(text)
            if vec is None:
                raise KeyError(f"passage not in frozen E5 calibration fixture: {text[:80]!r}")
            out.append(list(vec))
        return out
