"""OpenAI batched TMF extraction (Discovery v2)."""

from __future__ import annotations

import os
from typing import Any

from ..sources.contract import NormalizedSourceDocument
from .openai_common import build_openai_http, openai_configured, post_strict_json_schema


def tmf_batch_json_schema() -> dict[str, Any]:
    frame_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "mechanism": {"type": "string"},
            "object": {"type": ["string", "null"]},
            "function": {"type": ["string", "null"]},
            "evidence_span": {"type": "string"},
            "label": {
                "type": "string",
                "enum": [
                    "TECHNOLOGY_MECHANISM",
                    "APPLICATION_AREA",
                    "METHOD_GENERIC",
                    "MACRO_THEME",
                    "POLICY_REGULATION",
                    "UNCERTAIN",
                ],
            },
        },
        "required": ["mechanism", "object", "function", "evidence_span", "label"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "documents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "doc_id": {"type": "string"},
                        "frames": {
                            "type": "array",
                            "maxItems": 3,
                            "items": frame_schema,
                        },
                    },
                    "required": ["doc_id", "frames"],
                },
            }
        },
        "required": ["documents"],
    }


def _format_batch_prompt(documents: list[NormalizedSourceDocument]) -> str:
    blocks: list[str] = []
    for doc in documents:
        abstract = (doc.abstract or "").strip()
        blocks.append(
            f"doc_id={doc.source_document_id}\n"
            f"title: {doc.title.strip()}\n"
            f"abstract: {abstract if abstract else '[none]'}"
        )
    rules = (
        "Extract 0-3 Technical Mechanism Frames per document using ONLY title and abstract. "
        "Mechanism must be an explicit atomic engineering method, architecture, algorithm, "
        "protocol, or technical mechanism present in the text. "
        "Do NOT use world knowledge. "
        "Market, ecosystem, regulation, digitalization, conceptual frameworks, business models, "
        "and general assessment methods are NOT TECHNOLOGY_MECHANISM. "
        "evidence_span must be an exact substring from title or abstract. "
        "Return strict JSON matching schema."
    )
    return f"{rules}\n\n" + "\n\n---\n\n".join(blocks)


def call_openai_tmf_batch(
    documents: list[NormalizedSourceDocument],
) -> tuple[dict[str, list[dict[str, Any]]] | None, str | None]:
    if not documents:
        return {}, None
    if not openai_configured():
        return None, "not_configured"
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    base_url, http = build_openai_http()
    payload, err = post_strict_json_schema(
        api_key=api_key,
        base_url=base_url,
        http=http,
        schema_name="tmf_extraction_v1",
        schema=tmf_batch_json_schema(),
        user_content=_format_batch_prompt(documents),
    )
    http.close()
    if payload is None:
        return None, err or "tmf_error"
    out: dict[str, list[dict[str, Any]]] = {}
    for row in payload.get("documents") or []:
        if not isinstance(row, dict):
            continue
        doc_id = str(row.get("doc_id") or "")
        frames = row.get("frames")
        if doc_id and isinstance(frames, list):
            out[doc_id] = [f for f in frames if isinstance(f, dict)][:3]
    return out, None
