"""Discovery v2 OpenAI request shape regression (offline)."""

from __future__ import annotations

from weaksignalradar.fasttrack.discovery_v2.openai_common import (
    build_strict_json_schema_request,
    post_strict_json_schema,
)
from weaksignalradar.fasttrack.discovery_v2.openai_query_planner import planner_json_schema
from weaksignalradar.fasttrack.discovery_v2.openai_tmf import tmf_batch_json_schema
from weaksignalradar.fasttrack.llm import profile


def test_tmf_payload_matches_responses_pattern_without_temperature():
    probe = build_strict_json_schema_request(
        schema_name="tmf_extraction_v1",
        schema=tmf_batch_json_schema(),
        user_content="doc batch",
    )
    assert set(probe.keys()) == {"model", "input", "text"}
    assert "temperature" not in probe
    assert probe["text"]["format"]["strict"] is True
    assert probe["model"] == profile.LLM_MODEL


def test_planner_payload_has_no_temperature():
    planner = build_strict_json_schema_request(
        schema_name="domain_query_planner_v1",
        schema=planner_json_schema(),
        user_content="domain: test",
    )
    assert "temperature" not in planner
    assert planner["text"]["format"]["type"] == "json_schema"


def test_post_strict_json_schema_sends_body_without_temperature():
    captured: dict = {}

    class _Resp:
        status_code = 200

        def json(self) -> dict:
            return {"output_text": "{}"}

    class _Http:
        def post(self, url: str, headers: dict, json: dict) -> _Resp:
            captured["json"] = json
            return _Resp()

        def close(self) -> None:
            return None

    payload, err = post_strict_json_schema(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        http=_Http(),
        schema_name="tmf_extraction_v1",
        schema=tmf_batch_json_schema(),
        user_content="batch",
    )
    assert err is None
    assert payload == {}
    assert "temperature" not in captured["json"]
