"""OpenAI Responses API adapter (addendum v1.0.2 LLM profile)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx

from .base import LLMAdapter, TechnicalSignature
from .extraction_schema import validate_extraction_payload
from .profile import (
    LLM_API,
    LLM_MODEL,
    LLM_OUTPUT_MODE,
    LLM_PROFILE_ID,
    PROMPT_BUNDLE_VERSION,
)


def _facet(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if not v or v.upper() == "UNKNOWN":
        return None
    return v


class OpenAIResponsesExtractionAdapter(LLMAdapter):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        http_client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = http_client or httpx.Client(timeout=60.0)

    def extract_signature(
        self,
        *,
        candidate_name: str,
        evidence_texts: list[str],
    ) -> TechnicalSignature:
        evidence_block = "\n---\n".join(evidence_texts[:20])
        instructions = (
            "Extract evidence-grounded technical signature facets only. "
            "Use null for facets not supported by the evidence. "
            "Do not infer from world knowledge."
        )
        body = {
            "model": LLM_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": (
                        f"{instructions}\n\nCandidate: {candidate_name}\n\n"
                        f"Evidence:\n{evidence_block}"
                    ),
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "technical_signature_extraction",
                    "strict": True,
                    "schema": _response_schema(),
                }
            },
        }
        resp = self._http.post(
            f"{self._base_url}/responses",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        if resp.status_code >= 400:
            return TechnicalSignature(
                object_class=None,
                function=None,
                mechanism=None,
                architecture_or_process=None,
                key_technical_property=None,
                extraction_status=openai_http_error_summary(resp),
                evidence_span_refs=[],
                llm_model_id=LLM_MODEL,
                prompt_version=PROMPT_BUNDLE_VERSION,
                validation_status=f"HTTP_{resp.status_code}",
                llm_profile_id=LLM_PROFILE_ID,
            )
        payload = _parse_response_json(resp.json())
        try:
            validate_extraction_payload(payload)
        except Exception:
            return TechnicalSignature(
                object_class=None,
                function=None,
                mechanism=None,
                architecture_or_process=None,
                key_technical_property=None,
                extraction_status="INVALID_OUTPUT",
                evidence_span_refs=[],
                llm_model_id=LLM_MODEL,
                prompt_version=PROMPT_BUNDLE_VERSION,
                validation_status="FAILED",
                llm_profile_id=LLM_PROFILE_ID,
            )
        return TechnicalSignature(
            object_class=_facet(payload.get("object_class")),
            function=_facet(payload.get("function")),
            mechanism=_facet(payload.get("mechanism")),
            architecture_or_process=_facet(payload.get("architecture_or_process")),
            key_technical_property=_facet(payload.get("key_technical_property")),
            extraction_status="OK" if payload.get("status") == "OK" else "PARTIAL",
            evidence_span_refs=list(payload.get("evidence_span_refs") or []),
            llm_model_id=LLM_MODEL,
            prompt_version=PROMPT_BUNDLE_VERSION,
            validation_status="PASSED",
            llm_profile_id=LLM_PROFILE_ID,
        )


def _response_schema() -> dict[str, Any]:
    from .extraction_schema import EXTRACTION_JSON_SCHEMA

    # OpenAI subset: no $schema key
    schema = dict(EXTRACTION_JSON_SCHEMA)
    schema.pop("$schema", None)
    schema.pop("title", None)
    return schema


def openai_http_error_summary(resp: httpx.Response) -> str:
    """Safe API error text for diagnostics (no secrets)."""
    try:
        err = (resp.json() or {}).get("error") or {}
        msg = str(err.get("message") or "")[:240]
        code = err.get("code") or err.get("type") or "error"
        return f"{code}: {msg}".strip(": ")
    except Exception:
        return f"http_{resp.status_code}"


def _parse_response_json(data: dict[str, Any]) -> dict[str, Any]:
    """Best-effort parse of Responses API output text JSON."""
    if "output" in data:
        for item in data.get("output") or []:
            for part in item.get("content") or []:
                if part.get("type") == "output_text":
                    return json.loads(part.get("text") or "{}")
    if "output_text" in data:
        return json.loads(data["output_text"])
    raise ValueError("unrecognized responses payload")


def extraction_provenance(*, response_id: str | None = None) -> dict[str, Any]:
    return {
        "llm_provider": "openai",
        "llm_model": LLM_MODEL,
        "llm_api": LLM_API,
        "llm_output_mode": LLM_OUTPUT_MODE,
        "llm_profile_id": LLM_PROFILE_ID,
        "prompt_bundle_version": PROMPT_BUNDLE_VERSION,
        "request_timestamp": datetime.now(UTC).isoformat(),
        "provider_request_or_response_id": response_id,
    }
