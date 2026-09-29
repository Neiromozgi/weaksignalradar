"""Multi-subquery OpenAlex retrieval with global dedup budget."""

from __future__ import annotations

import re
from typing import Any

from ..sources.budget import OPENALEX_MAX_WORKS
from ..sources.contract import NormalizedSourceDocument
from ..sources.openalex_ft import OpenAlexFastTrackAdapter, OpenAlexLiveResult
from .query_planner import plan_domain_query, split_planner_subqueries, subquery_sequence


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


def compute_call_allocation(plan: dict[str, Any], max_calls: int) -> list[dict[str, Any]]:
    """Deterministic per-subquery OpenAlex call budget (one adapter invocation each)."""
    broad, facets = split_planner_subqueries(plan)
    if max_calls <= 0:
        return []

    if plan.get("planner_status") != "PLANNER_OK" or not facets:
        subs = subquery_sequence(plan)
        if not subs:
            return []
        return [
            {
                "query": subs[0],
                "allocated_calls": max_calls,
                "role": "sequential",
            }
        ]

    ordered: list[tuple[str, str]] = [(q, "facet") for q in facets] + [(q, "broad") for q in broad]
    alloc: dict[str, int] = {q: 0 for q, _ in ordered}
    remaining = max_calls

    for q, role in ordered:
        if role != "facet" or remaining <= 0:
            continue
        alloc[q] += 1
        remaining -= 1

    for q, role in ordered:
        if role != "broad" or remaining <= 0:
            continue
        alloc[q] += 1
        remaining -= 1

    idx = 0
    guard = 0
    n = len(ordered)
    while remaining > 0 and n > 0 and guard < max_calls * n + 5:
        q, _ = ordered[idx % n]
        alloc[q] += 1
        remaining -= 1
        idx += 1
        guard += 1

    rows: list[dict[str, Any]] = []
    for q, role in ordered:
        calls = alloc.get(q, 0)
        if calls > 0:
            rows.append({"query": q, "allocated_calls": calls, "role": role})
    return rows


def planned_retrieval_phases(plan: dict[str, Any], *, max_calls: int = 15) -> dict[str, Any]:
    """Describe scheduling for tests and provenance (no network)."""
    broad, facets = split_planner_subqueries(plan)
    allocation = compute_call_allocation(plan, max_calls)
    if plan.get("planner_status") != "PLANNER_OK" or not facets:
        return {
            "mode": "SEQUENTIAL_FAIL_SOFT",
            "broad_subqueries": broad,
            "facet_subqueries": facets,
            "call_allocation": allocation,
        }
    return {
        "mode": "FACET_RESERVED_THEN_BROAD",
        "broad_subqueries": broad,
        "facet_subqueries": facets,
        "call_allocation": allocation,
        "allocated_calls_total": sum(r["allocated_calls"] for r in allocation),
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
    schedule = planned_retrieval_phases(planner_out, max_calls=max_calls)
    allocation = compute_call_allocation(planner_out, max_calls)
    batches: list[list[NormalizedSourceDocument]] = []
    per_query: list[dict[str, Any]] = []
    calls_used_total = 0

    for row in allocation:
        sub = str(row["query"])
        budget = int(row["allocated_calls"])
        if budget <= 0 or not sub.strip():
            continue
        if calls_used_total >= max_calls:
            break
        budget = min(budget, max_calls - calls_used_total)
        result: OpenAlexLiveResult = adapter.search_live_bounded(
            sub,
            run_id=run_id,
            max_calls=budget,
        )
        used = result.calls_used
        if used <= 0 and budget > 0:
            used = budget
        used = min(used, budget, max_calls - calls_used_total)
        calls_used_total += used
        batches.append(list(result.documents))
        per_query.append(
            {
                "query": sub,
                "role": row.get("role"),
                "allocated_calls": budget,
                "calls_used": used,
                "documents": len(result.documents),
                "coverage": result.coverage_state.value,
            }
        )

    merged = merge_document_batches(batches)
    meta = {
        "query_planner": planner_out,
        "retrieval_schedule": schedule,
        "call_allocation": allocation,
        "subqueries_executed": per_query,
        "openalex_calls_used": calls_used_total,
        "deduped_work_count": len(merged),
    }
    return merged, meta
