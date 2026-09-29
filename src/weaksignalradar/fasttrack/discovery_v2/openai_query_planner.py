"""OpenAI strict-schema domain query planner (Discovery v2)."""

from __future__ import annotations

import os
from typing import Any

from .openai_common import build_openai_http, openai_configured, post_strict_json_schema
from .query_planner_schema import QUERY_PLANNER_PROMPT_VERSION, validate_planner_payload


def planner_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "domain_original": {"type": "string"},
            "domain_en": {"type": "string"},
            "domain_aliases": {
                "type": "array",
                "maxItems": 2,
                "items": {"type": "string"},
            },
            "technical_facets": {
                "type": "array",
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "query": {"type": "string"},
                        "kind": {"type": "string", "enum": ["TECHNICAL_SEARCH_FACET"]},
                    },
                    "required": ["query", "kind"],
                },
            },
        },
        "required": ["domain_original", "domain_en", "domain_aliases", "technical_facets"],
    }


def call_openai_query_planner(domain_original: str) -> tuple[dict[str, Any] | None, str | None]:
    if not openai_configured():
        return None, "not_configured"
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    base_url, http = build_openai_http()
    instructions = (
        "Generate bounded search hypotheses that could locate technical mechanisms "
        "inside this domain. Each technical facet is a SEARCH_HYPOTHESIS only — not evidence, "
        "not a trend, not an emerging signal. Do not invent evidence. Do not name products "
        "or companies. Do not use domain-specific jury examples. Max 2 aliases, max 6 facets, "
        "each facet at most 5 words."
    )
    content = f"{instructions}\n\nDomain query: {domain_original.strip()}"
    payload, err = post_strict_json_schema(
        api_key=api_key,
        base_url=base_url,
        http=http,
        schema_name="domain_query_planner_v1",
        schema=planner_json_schema(),
        user_content=content,
    )
    http.close()
    if payload is None:
        return None, err or "planner_error"
    try:
        validate_planner_payload(payload)
    except ValueError as exc:
        return None, str(exc)
    out = dict(payload)
    out["planner_status"] = "PLANNER_OK"
    out["prompt_version"] = QUERY_PLANNER_PROMPT_VERSION
    return out, None
