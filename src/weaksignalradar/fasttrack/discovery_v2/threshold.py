"""Production complete-linkage distance threshold (real E5 calibration only)."""

from __future__ import annotations

from ..config.embedding_profile import E5_SMALL_V1

# Selected offline on frozen intfloat/multilingual-e5-small @ revision
# 614241f622f53c4eeff9890bdc4f31cfecc418b3 using fixture discovery_v2_e5_live2_34_v1.
# DeterministicTestBackend MUST NOT be used to derive this value.
CALIBRATED_DISTANCE_THRESHOLD = 0.065
CALIBRATED_SIMILARITY_FLOOR = 1.0 - CALIBRATED_DISTANCE_THRESHOLD
CALIBRATION_FIXTURES = ("discovery_v2_e5_live2_34_v1",)
CLUSTERING_ALGORITHM = "complete_linkage_cosine"
CLUSTERING_REPRESENTATION = "mechanism"
CLUSTERING_REPRESENTATION_VERSION = "tmf_mechanism_v1"
CALIBRATION_EMBEDDING_MODEL_ID = E5_SMALL_V1.embedding_model_id
CALIBRATION_EMBEDDING_MODEL_REVISION = E5_SMALL_V1.embedding_model_revision


def clustering_calibration_provenance() -> dict[str, object]:
    return {
        "clustering_algorithm": CLUSTERING_ALGORITHM,
        "clustering_distance_threshold": CALIBRATED_DISTANCE_THRESHOLD,
        "clustering_similarity_floor": CALIBRATED_SIMILARITY_FLOOR,
        "clustering_representation": CLUSTERING_REPRESENTATION,
        "clustering_representation_version": CLUSTERING_REPRESENTATION_VERSION,
        "calibration_embedding_backend": "SentenceTransformerBackend",
        "calibration_embedding_model_id": CALIBRATION_EMBEDDING_MODEL_ID,
        "calibration_embedding_model_revision": CALIBRATION_EMBEDDING_MODEL_REVISION,
        "calibration_fixture_ids": list(CALIBRATION_FIXTURES),
    }
