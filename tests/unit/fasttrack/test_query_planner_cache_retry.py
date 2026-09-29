"""Query planner cache retry when fallback was stored offline."""

from __future__ import annotations

from weaksignalradar.fasttrack.discovery_v2.llm_cache import cache_key, save_cached_json
from weaksignalradar.fasttrack.discovery_v2.query_planner import plan_domain_query
from weaksignalradar.fasttrack.discovery_v2.query_planner_schema import (
    QUERY_PLANNER_PROMPT_VERSION,
)
from weaksignalradar.fasttrack.llm.profile import LLM_MODEL


def test_planner_retries_after_cached_fallback_when_provider_allowed(monkeypatch, tmp_path):
    monkeypatch.setenv("WSR_LLM_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("WSR_ALLOW_LLM_PROVIDER", "1")
    key = cache_key(
        model_id=LLM_MODEL,
        prompt_version=QUERY_PLANNER_PROMPT_VERSION,
        normalized_input="финтех",
    )
    save_cached_json(
        key,
        {
            "domain_original": "Финтех",
            "domain_en": "Финтех",
            "domain_aliases": [],
            "technical_facets": [],
            "planner_status": "PLANNER_UNAVAILABLE",
            "fallback_mode": "FALLBACK_DOMAIN_ONLY",
        },
    )

    def _fake_planner(domain: str):
        return (
            {
                "domain_original": domain,
                "domain_en": "financial technology",
                "domain_aliases": ["fintech"],
                "technical_facets": [
                    {"query": "payment protocol", "kind": "TECHNICAL_SEARCH_FACET"}
                ],
                "planner_status": "PLANNER_OK",
            },
            None,
        )

    monkeypatch.setattr(
        "weaksignalradar.fasttrack.discovery_v2.query_planner.call_openai_query_planner",
        _fake_planner,
    )
    out = plan_domain_query("Финтех")
    assert out.get("planner_status") == "PLANNER_OK"
    assert out.get("technical_facets")
