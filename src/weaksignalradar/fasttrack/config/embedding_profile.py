"""Frozen embedding profile e5_small_v1 (addendum 01)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmbeddingProfile:
    embedding_profile_id: str
    embedding_model_id: str
    embedding_model_revision: str
    vector_dimension: int
    max_tokens: int
    pooling: str
    normalization: str
    metric: str
    prefix_policy_version: str
    preprocessing_version: str


E5_SMALL_V1 = EmbeddingProfile(
    embedding_profile_id="e5_small_v1",
    embedding_model_id="intfloat/multilingual-e5-small",
    embedding_model_revision="614241f622f53c4eeff9890bdc4f31cfecc418b3",
    vector_dimension=384,
    max_tokens=512,
    pooling="mean",
    normalization="L2",
    metric="cosine",
    prefix_policy_version="e5_prefix_v1",
    preprocessing_version="e5_small_preprocess_v1",
)


def embedding_provenance_fields(profile: EmbeddingProfile = E5_SMALL_V1) -> dict[str, str | int]:
    return {
        "embedding_profile_id": profile.embedding_profile_id,
        "embedding_model_id": profile.embedding_model_id,
        "embedding_model_revision": profile.embedding_model_revision,
        "vector_dimension": profile.vector_dimension,
        "max_tokens": profile.max_tokens,
        "pooling": profile.pooling,
        "normalization": profile.normalization,
        "similarity_metric": profile.metric,
        "prefix_policy_version": profile.prefix_policy_version,
        "preprocessing_version": profile.preprocessing_version,
    }
