"""Strict JSON Schema for LLM technical signature extraction."""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

from .profile import SCHEMA_VERSION

EXTRACTION_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "TechnicalSignatureExtraction",
    "type": "object",
    "required": [
        "candidate_name",
        "object_class",
        "function",
        "mechanism",
        "architecture_or_process",
        "key_technical_property",
        "evidence_span_refs",
        "unknown_fields",
        "status",
    ],
    "properties": {
        "candidate_name": {"type": "string"},
        "object_class": {"type": ["string", "null"]},
        "function": {"type": ["string", "null"]},
        "mechanism": {"type": ["string", "null"]},
        "architecture_or_process": {"type": ["string", "null"]},
        "key_technical_property": {"type": ["string", "null"]},
        "evidence_span_refs": {"type": "array", "items": {"type": "string"}},
        "unknown_fields": {"type": "array", "items": {"type": "string"}},
        "status": {"enum": ["OK", "PARTIAL", "UNKNOWN"]},
    },
    "additionalProperties": False,
}

_VALIDATOR = Draft202012Validator(EXTRACTION_JSON_SCHEMA)


def validate_extraction_payload(payload: dict[str, Any]) -> None:
    _VALIDATOR.validate(payload)


def schema_version() -> str:
    return SCHEMA_VERSION
