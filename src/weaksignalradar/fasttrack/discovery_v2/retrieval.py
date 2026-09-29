"""Multi-subquery OpenAlex retrieval with global dedup budget."""

from __future__ import annotations

import re
from typing import Any

from ..sources.budget import OPENALEX_MAX_WORKS
from ..sources.contract import NormalizedSourceDocument
from ..sources.openalex_ft import OpenAlexFastTrackAdapter, OpenAlexLiveResult
from .query_planner import plan_domain_query, subquery_sequence


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


def retrieve_openalex_v2(
    *,
    query: str,
    run_id: str,
    adapter: OpenAlexFastTrackAdapter,
    max_calls: int,
    plan: dict[str, Any] | None = None,
) -> tuple[list[NormalizedSourceDocument], dict[str, Any]]:
    planner_out = plan or plan_domain_query(query)
    subqueries = subquery_sequence(planner_out)
    calls_left = max_calls
    batches: list[list[NormalizedSourceDocument]] = []
    per_query: list[dict[str, Any]] = []
    for sub in subqueries:
        if calls_left <= 0:
            break
        result: OpenAlexLiveResult = adapter.search_live_bounded(
            sub,
            run_id=run_id,
            max_calls=calls_left,
        )
        calls_left -= result.calls_used
        batches.append(list(result.documents))
        per_query.append(
            {
                "query": sub,
                "calls_used": result.calls_used,
                "documents": len(result.documents),
                "coverage": result.coverage_state.value,
            }
        )
    merged = merge_document_batches(batches)
    meta = {
        "query_planner": planner_out,
        "subqueries_executed": per_query,
        "openalex_calls_used": max_calls - calls_left,
        "deduped_work_count": len(merged),
    }
    return merged, meta
