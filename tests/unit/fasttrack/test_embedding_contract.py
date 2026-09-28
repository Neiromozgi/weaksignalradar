import os

import pytest

from weaksignalradar.fasttrack.config.embedding_profile import E5_SMALL_V1
from weaksignalradar.fasttrack.embedding.backend import DeterministicTestBackend, cosine_similarity
from weaksignalradar.fasttrack.preprocessing.e5 import facet_query, prefix_passage, prefix_query


def test_frozen_embedding_profile_literals():
    assert E5_SMALL_V1.embedding_profile_id == "e5_small_v1"
    assert E5_SMALL_V1.embedding_model_id == "intfloat/multilingual-e5-small"
    assert E5_SMALL_V1.embedding_model_revision == "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    assert E5_SMALL_V1.vector_dimension == 384
    assert E5_SMALL_V1.max_tokens == 512


def test_e5_prefix_policy():
    assert prefix_query("alpha") == "query: alpha"
    assert prefix_passage("title abstract") == "passage: title abstract"
    assert facet_query("UNKNOWN") is None
    assert facet_query("memristor") == "query: memristor"


def test_deterministic_backend_l2_unit_norm():
    os.environ["WSR_EMBEDDING_BACKEND"] = "deterministic"
    backend = DeterministicTestBackend()
    vec = backend.encode(["query: test"])[0]
    assert len(vec) == 384
    norm = sum(x * x for x in vec) ** 0.5
    assert norm == pytest.approx(1.0, rel=1e-5)
    sim = cosine_similarity(vec, vec)
    assert sim == pytest.approx(1.0, rel=1e-5)
