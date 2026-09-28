"""LLM adapter — structured technical signature extraction only (handoff D-008)."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class TechnicalSignature:
    object_class: str | None
    function: str | None
    mechanism: str | None
    architecture_or_process: str | None
    key_technical_property: str | None
    extraction_status: str
    evidence_span_refs: list[str]
    llm_model_id: str | None
    prompt_version: str
    validation_status: str | None = None
    llm_profile_id: str | None = None


class LLMAdapter(ABC):
    @abstractmethod
    def extract_signature(
        self,
        *,
        candidate_name: str,
        evidence_texts: list[str],
    ) -> TechnicalSignature: ...


class NotConfiguredLLMAdapter(LLMAdapter):
    """Missing OPENAI_API_KEY — facets remain UNKNOWN (no guessed values)."""

    def extract_signature(
        self,
        *,
        candidate_name: str,
        evidence_texts: list[str],
    ) -> TechnicalSignature:
        del candidate_name, evidence_texts
        return TechnicalSignature(
            object_class=None,
            function=None,
            mechanism=None,
            architecture_or_process=None,
            key_technical_property=None,
            extraction_status="NOT_CONFIGURED",
            evidence_span_refs=[],
            llm_model_id=None,
            prompt_version="technical_signature_extraction_v1",
            validation_status="SKIPPED",
            llm_profile_id="openai_gpt56_terra_extraction_v1",
        )


def get_llm_adapter() -> LLMAdapter:
    from .openai_responses import OpenAIResponsesExtractionAdapter
    from .profile import LLM_PROVIDER

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    provider = os.environ.get("LLM_PROVIDER", LLM_PROVIDER).strip()
    if provider == "openai" and key:
        return OpenAIResponsesExtractionAdapter(api_key=key)
    return NotConfiguredLLMAdapter()


def llm_runtime_status() -> str:
    if os.environ.get("OPENAI_API_KEY", "").strip():
        return "CONFIGURED"
    return "NOT_CONFIGURED"
