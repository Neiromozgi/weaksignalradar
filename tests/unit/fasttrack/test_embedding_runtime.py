import pytest

from weaksignalradar.fasttrack.config.embedding_profile import E5_SMALL_V1
from weaksignalradar.fasttrack.embedding.backend import (
    DeterministicTestBackend,
    get_embedding_backend,
)
from weaksignalradar.fasttrack.llm.base import TechnicalSignature
from weaksignalradar.fasttrack.pipeline.features import compute_c_raw as pipeline_c


@pytest.fixture(autouse=True)
def _deterministic(monkeypatch):
    monkeypatch.setenv("WSR_EMBEDDING_BACKEND", "deterministic")


def test_default_test_backend_matches_frozen_profile():
    backend = get_embedding_backend()
    assert isinstance(backend, DeterministicTestBackend)
    assert backend.profile.embedding_model_id == E5_SMALL_V1.embedding_model_id
    assert backend.profile.embedding_model_revision == E5_SMALL_V1.embedding_model_revision
    assert backend.profile.vector_dimension == 384


def test_c_computed_when_facets_and_backend_present():
    backend = get_embedding_backend()
    sig = TechnicalSignature(
        object_class="photonic chip",
        function=None,
        mechanism="waveguide mesh",
        architecture_or_process=None,
        key_technical_property=None,
        extraction_status="OK",
        evidence_span_refs=["e1"],
        llm_model_id="test",
        prompt_version="v1",
        validation_status="PASSED",
    )
    hist = TechnicalSignature(
        object_class="battery",
        function=None,
        mechanism="electrolyte",
        architecture_or_process=None,
        key_technical_property=None,
        extraction_status="OK",
        evidence_span_refs=[],
        llm_model_id="test",
        prompt_version="v1",
        validation_status="PASSED",
    )
    value = pipeline_c(sig, [hist], backend)
    assert value is not None
    assert isinstance(value, float)


def test_c_none_without_backend_not_because_facets():
    sig = TechnicalSignature(
        object_class="photonic chip",
        function="compute",
        mechanism="mesh",
        architecture_or_process="integrated",
        key_technical_property="low loss",
        extraction_status="OK",
        evidence_span_refs=["e1"],
        llm_model_id="test",
        prompt_version="v1",
        validation_status="PASSED",
    )
    assert pipeline_c(sig, [], None) is None
