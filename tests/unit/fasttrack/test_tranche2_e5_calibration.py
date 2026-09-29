"""Production E5 clustering calibration gate (frozen vectors, no model download)."""

from __future__ import annotations

from weaksignalradar.fasttrack.discovery_v2.frozen_e5_fixture import (
    FrozenE5CalibrationBackend,
    load_calibration_frames,
)
from weaksignalradar.fasttrack.discovery_v2.mechanism_cluster import (
    cluster_frames,
    frame_passage_for_representation,
)
from weaksignalradar.fasttrack.discovery_v2.threshold import (
    CALIBRATED_DISTANCE_THRESHOLD,
    CLUSTERING_REPRESENTATION,
    clustering_calibration_provenance,
)
from weaksignalradar.fasttrack.discovery_v2.threshold_calibrate import (
    select_production_calibration,
)


def test_production_calibration_constants_match_fixture_selector():
    selected, _table = select_production_calibration()
    assert selected["distance_threshold"] == CALIBRATED_DISTANCE_THRESHOLD
    assert selected["clustering_representation"] == CLUSTERING_REPRESENTATION
    prov = clustering_calibration_provenance()
    assert list(prov["calibration_fixture_ids"]) == ["discovery_v2_e5_live2_34_v1"]
    assert prov["calibration_embedding_model_id"] == "intfloat/multilingual-e5-small"


def test_frozen_e5_gate_no_mega_cluster_and_paraphrase_merge():
    frames = load_calibration_frames()
    backend = FrozenE5CalibrationBackend()
    passages = [
        frame_passage_for_representation(f, representation=CLUSTERING_REPRESENTATION)
        for f in frames
    ]
    vectors = backend.encode(passages)
    clusters = cluster_frames(
        list(range(len(frames))),
        vectors,
        distance_threshold=CALIBRATED_DISTANCE_THRESHOLD,
    )
    assert len(clusters) >= 5
    cmap = {}
    for ci, mem in enumerate(clusters):
        for idx in mem:
            cmap[idx] = ci
    assert cmap[8] == cmap[18]
    assert cmap[7] != cmap[8]
    assert cmap[23] != cmap[24]
    assert cmap[30] != cmap[29]
    assert cmap[5] != cmap[17]
    largest_share = max(len({frames[i].doc_id for i in mem}) for mem in clusters) / 75
    assert largest_share <= 0.25
    assert CALIBRATED_DISTANCE_THRESHOLD < 0.15


def test_production_threshold_would_mega_cluster_at_legacy_022():
    frames = load_calibration_frames()
    backend = FrozenE5CalibrationBackend()
    vectors = backend.encode(
        [
            frame_passage_for_representation(f, representation=CLUSTERING_REPRESENTATION)
            for f in frames
        ]
    )
    clusters = cluster_frames(list(range(len(frames))), vectors, distance_threshold=0.22)
    assert len(clusters) <= 3
