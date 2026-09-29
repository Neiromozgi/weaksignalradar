"""Shared OpenAI Responses API helpers for Discovery v2 (not signature extraction)."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from ..llm.openai_responses import openai_http_error_summary
from ..llm.profile import LLM_MODEL


def openai_configured() -> bool:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    provider = os.environ.get("LLM_PROVIDER", "openai").strip()
    return provider == "openai" and bool(key)


def llm_provider_calls_allowed() -> bool:
    return os.environ.get("WSR_ALLOW_LLM_PROVIDER", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_openai_http() -> tuple[str, httpx.Client]:
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    return base, httpx.Client(timeout=120.0)


def build_strict_json_schema_request(
    *,
    schema_name: str,
    schema: dict[str, Any],
    user_content: str,
) -> dict[str, Any]:
    """Request body aligned with OpenAIResponsesExtractionAdapter (no temperature)."""
    return {
        "model": LLM_MODEL,
        "input": [{"role": "user", "content": user_content}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
    }


def post_strict_json_schema(
    *,
    api_key: str,
    base_url: str,
    http: httpx.Client,
    schema_name: str,
    schema: dict[str, Any],
    user_content: str,
) -> tuple[dict[str, Any] | None, str | None]:
    body = build_strict_json_schema_request(
        schema_name=schema_name,
        schema=schema,
        user_content=user_content,
    )
    resp = http.post(
        f"{base_url}/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
    )
    if resp.status_code >= 400:
        return None, openai_http_error_summary(resp)
    try:
        return _parse_response_json(resp.json()), None
    except (ValueError, json.JSONDecodeError, KeyError, TypeError):
        return None, "invalid_output"


def _parse_response_json(data: dict[str, Any]) -> dict[str, Any]:
    if "output" in data:
        for item in data.get("output") or []:
            for part in item.get("content") or []:
                if part.get("type") == "output_text":
                    return json.loads(part.get("text") or "{}")
    if "output_text" in data:
        return json.loads(data["output_text"])
    raise ValueError("unrecognized responses payload")
