"""Multi-subquery OpenAlex retrieval with global dedup budget."""

from __future__ import annotations

import re
from typing import Any

from ..sources.budget import OPENALEX_MAX_WORKS
from ..sources.contract import NormalizedSourceDocument
from ..sources.openalex_ft import OpenAlexFastTrackAdapter, OpenAlexLiveResult
from .query_planner import plan_domain_query, split_planner_subqueries, subquery_sequence

# When planner succeeds, each technical facet gets at least one API call before broad
# queries may consume leftover budget for extra pagination.
_FACET_MIN_CALLS_PER_QUERY = 1
_BROAD_FIRST_PASS_MAX_CALLS = 1
_ROUND_ROBIN_EXTRA_MAX_CALLS = 1


def _dedupe_key(doc: NormalizedSourceDocument) -> str:
    if doc.doi:
        return f"doi:{doc.doi.lower()}"
    title = re.sub(r"\s+", " ", (doc.title or "").lower()).strip()
    if title:
        return f"title:{title}"
    return doc.stable_external_id


def merge_document_batches(
    batches: list[list[NormalizedSourceDocument]],
    *,
    hard_cap: int = OPENALEX_MAX_WORKS,
) -> list[NormalizedSourceDocument]:
    seen: set[str] = set()
    out: list[NormalizedSourceDocument] = []
    for batch in batches:
        for doc in batch:
            key = _dedupe_key(doc)
            if key in seen:
                continue
            seen.add(key)
            out.append(doc)
            if len(out) >= hard_cap:
                return out
    return out


def planned_retrieval_phases(plan: dict[str, Any]) -> dict[str, Any]:
    """Describe scheduling phases for tests and provenance (no network)."""
    broad, facets = split_planner_subqueries(plan)
    if plan.get("planner_status") != "PLANNER_OK" or not facets:
        return {
            "mode": "SEQUENTIAL_FAIL_SOFT",
            "broad_subqueries": broad,
            "facet_subqueries": facets,
        }
    return {
        "mode": "FACET_RESERVED_THEN_BROAD",
        "broad_subqueries": broad,
        "facet_subqueries": facets,
        "facet_min_calls_each": _FACET_MIN_CALLS_PER_QUERY,
        "broad_first_pass_max_calls": _BROAD_FIRST_PASS_MAX_CALLS,
    }


def retrieve_openalex_v2(
    *,
    query: str,
    run_id: str,
    adapter: OpenAlexFastTrackAdapter,
    max_calls: int,
    plan: dict[str, Any] | None = None,
) -> tuple[list[NormalizedSourceDocument], dict[str, Any]]:
    planner_out = plan or plan_domain_query(query)
    schedule = planned_retrieval_phases(planner_out)
    calls_left = max_calls
    batches: list[list[NormalizedSourceDocument]] = []
    per_query: list[dict[str, Any]] = []

    def execute_subquery(sub: str, call_cap: int, *, phase: str) -> None:
        nonlocal calls_left
        if calls_left <= 0 or call_cap <= 0 or not sub.strip():
            return
        budget = min(call_cap, calls_left)
        result: OpenAlexLiveResult = adapter.search_live_bounded(
            sub,
            run_id=run_id,
            max_calls=budget,
        )
        used = result.calls_used
        if used <= 0 and budget > 0:
            used = budget
        calls_left -= min(used, calls_left)
        batches.append(list(result.documents))
        per_query.append(
            {
                "query": sub,
                "phase": phase,
                "calls_used": used,
                "documents": len(result.documents),
                "coverage": result.coverage_state.value,
            }
        )

    if schedule["mode"] == "SEQUENTIAL_FAIL_SOFT":
        for sub in subquery_sequence(planner_out):
            if calls_left <= 0:
                break
            execute_subquery(sub, calls_left, phase="sequential")
    else:
        broad: list[str] = schedule["broad_subqueries"]
        facets: list[str] = schedule["facet_subqueries"]
        for sub in facets:
            execute_subquery(sub, _FACET_MIN_CALLS_PER_QUERY, phase="facet_reserved")
        for sub in broad:
            execute_subquery(sub, _BROAD_FIRST_PASS_MAX_CALLS, phase="broad_capped")
        rotation = broad + facets
        guard = 0
        max_guard = max_calls * max(len(rotation), 1) + 5
        idx = 0
        while calls_left > 0 and rotation and guard < max_guard:
            before = calls_left
            execute_subquery(
                rotation[idx % len(rotation)],
                _ROUND_ROBIN_EXTRA_MAX_CALLS,
                phase="extra_pagination",
            )
            if calls_left >= before:
                break
            idx += 1
            guard += 1

    merged = merge_document_batches(batches)
    meta = {
        "query_planner": planner_out,
        "retrieval_schedule": schedule,
        "subqueries_executed": per_query,
        "openalex_calls_used": max_calls - calls_left,
        "deduped_work_count": len(merged),
    }
    return merged, meta
