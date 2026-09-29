"""Bounded domain query planner (search hypotheses only)."""

from __future__ import annotations

from typing import Any

from ..llm.profile import LLM_MODEL
from .llm_cache import cache_key, load_cached_json, save_cached_json
from .llm_run_budget import try_consume_llm_provider_slot
from .openai_common import llm_provider_calls_allowed, openai_configured
from .openai_query_planner import call_openai_query_planner
from .query_planner_schema import QUERY_PLANNER_PROMPT_VERSION


def fallback_domain_only_plan(domain_original: str, *, status: str) -> dict[str, Any]:
    return {
        "domain_original": domain_original.strip(),
        "domain_en": domain_original.strip(),
        "domain_aliases": [],
        "technical_facets": [],
        "planner_status": status,
        "fallback_mode": "FALLBACK_DOMAIN_ONLY",
        "prompt_version": QUERY_PLANNER_PROMPT_VERSION,
    }


def plan_domain_query(domain_original: str) -> dict[str, Any]:
    norm = domain_original.strip().lower()
    key = cache_key(
        model_id=LLM_MODEL or "openai",
        prompt_version=QUERY_PLANNER_PROMPT_VERSION,
        normalized_input=norm,
    )
    cached = load_cached_json(key)
    if cached and cached.get("domain_original"):
        if cached.get("planner_status") == "PLANNER_OK":
            return cached
        if not (openai_configured() and llm_provider_calls_allowed()):
            return cached
    allowed, reason = try_consume_llm_provider_slot()
    if not allowed:
        fb = fallback_domain_only_plan(domain_original, status="PLANNER_UNAVAILABLE")
        fb["planner_error"] = reason
        fb["llm_budget_blocked"] = True
        return fb
    plan, err = call_openai_query_planner(domain_original)
    if plan is not None:
        save_cached_json(key, plan)
        return plan
    status = "PLANNER_UNAVAILABLE" if err == "not_configured" else "PLANNER_ERROR"
    fb = fallback_domain_only_plan(domain_original, status=status)
    fb["planner_error"] = err
    save_cached_json(key, fb)
    return fb


def subquery_sequence(plan: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        q = q.strip()
        if not q:
            return
        k = q.lower()
        if k in seen:
            return
        seen.add(k)
        out.append(q)

    add(str(plan.get("domain_original") or ""))
    if plan.get("planner_status") != "PLANNER_OK":
        return out
    add(str(plan.get("domain_en") or ""))
    for alias in plan.get("domain_aliases") or []:
        if isinstance(alias, str):
            add(alias)
    for facet in plan.get("technical_facets") or []:
        if isinstance(facet, dict):
            add(str(facet.get("query") or ""))
    return out
