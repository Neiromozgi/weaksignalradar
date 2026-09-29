"""OpenAlex v2 retrieval budget scheduling (LIVE #3 / #4 depth hotfix)."""

from __future__ import annotations

from dataclasses import dataclass, field

from weaksignalradar.fasttrack.discovery_v2.query_planner import (
    fallback_domain_only_plan,
    split_planner_subqueries,
)
from weaksignalradar.fasttrack.discovery_v2.retrieval import (
    compute_call_allocation,
    planned_retrieval_phases,
    retrieve_openalex_v2,
)
from weaksignalradar.fasttrack.sources.contract import (
    CoverageState,
    NormalizedSourceDocument,
    OriginalAvailability,
)
from weaksignalradar.fasttrack.sources.openalex_ft import OpenAlexLiveResult


def _planner_ok_plan() -> dict:
    return {
        "domain_original": "Финтех",
        "domain_en": "Financial technology",
        "domain_aliases": ["Fintech", "Digital finance"],
        "technical_facets": [
            {
                "query": "real-time payment settlement mechanisms",
                "kind": "TECHNICAL_SEARCH_FACET",
            },
            {
                "query": "digital identity authentication protocols",
                "kind": "TECHNICAL_SEARCH_FACET",
            },
            {"query": "transaction fraud detection models", "kind": "TECHNICAL_SEARCH_FACET"},
            {"query": "open banking authorization APIs", "kind": "TECHNICAL_SEARCH_FACET"},
            {"query": "automated credit risk scoring", "kind": "TECHNICAL_SEARCH_FACET"},
            {
                "query": "privacy-preserving financial data analytics",
                "kind": "TECHNICAL_SEARCH_FACET",
            },
        ],
        "planner_status": "PLANNER_OK",
        "prompt_version": "domain_query_planner_v1",
    }


@dataclass
class RecordingAdapter:
    calls: list[tuple[str, int]] = field(default_factory=list)

    def search_live_bounded(
        self,
        query: str,
        *,
        run_id: str,
        max_calls: int,
    ) -> OpenAlexLiveResult:
        del run_id
        self.calls.append((query, max_calls))
        doc = NormalizedSourceDocument(
            source_document_id=f"doc_{len(self.calls)}",
            source_id=f"openalex:doc_{len(self.calls)}",
            source_type="openalex_work",
            stable_external_id=f"https://openalex.org/W{len(self.calls)}",
            title=f"Title {len(self.calls)}",
            year=2024,
            canonical_url=f"https://openalex.org/W{len(self.calls)}",
            doi=None,
            original_availability_status=OriginalAvailability.ABSTRACT_AVAILABLE,
            metadata_json={},
            source_snapshot_id="live",
            retrieved_at="2026-01-01T00:00:00+00:00",
            content_hash_of_api_record="x",
            coverage_state=CoverageState.FOUND,
            organization_names=[],
            abstract="x",
        )
        use = max_calls
        return OpenAlexLiveResult(
            documents=[doc] if use else [],
            coverage_state=CoverageState.FOUND,
            calls_used=use,
            pages=use,
            cap_reached=False,
            elapsed_sec=0.01,
        )


def test_technical_facets_each_get_retrieval_attempt():
    plan = _planner_ok_plan()
    adapter = RecordingAdapter()
    _, meta = retrieve_openalex_v2(
        query="Финтех",
        run_id="run_test",
        adapter=adapter,  # type: ignore[arg-type]
        max_calls=15,
        plan=plan,
    )
    _broad, facets = split_planner_subqueries(plan)
    facet_hits = {q for q, _ in adapter.calls if q in facets}
    assert len(facet_hits) == len(facets)
    assert meta["openalex_calls_used"] <= 15


def test_total_allocation_equals_actual_calls_and_within_cap():
    plan = _planner_ok_plan()
    rows = compute_call_allocation(plan, 15)
    assert sum(r["allocated_calls"] for r in rows) == 15
    adapter = RecordingAdapter()
    _, meta = retrieve_openalex_v2(
        query="Финтех",
        run_id="run_test",
        adapter=adapter,  # type: ignore[arg-type]
        max_calls=15,
        plan=plan,
    )
    assert meta["openalex_calls_used"] == 15
    assert len(adapter.calls) == len(rows)


def test_single_adapter_invocation_when_allocation_is_two():
    plan = _planner_ok_plan()
    rows = compute_call_allocation(plan, 15)
    target = rows[0]["query"]
    assert rows[0]["allocated_calls"] >= 2
    adapter = RecordingAdapter()
    retrieve_openalex_v2(
        query="Финтех",
        run_id="run_test",
        adapter=adapter,  # type: ignore[arg-type]
        max_calls=15,
        plan=plan,
    )
    invocations = [mc for q, mc in adapter.calls if q == target]
    assert invocations == [rows[0]["allocated_calls"]]
    assert len(invocations) == 1


def test_duplicate_subqueries_deduped_before_allocation():
    plan = _planner_ok_plan()
    plan["domain_en"] = "Fintech"
    broad, facets = split_planner_subqueries(plan)
    assert "Fintech" not in broad[1:] or broad.count("Fintech") == 1
    rows = compute_call_allocation(plan, 15)
    queries = [r["query"] for r in rows]
    assert len(queries) == len(set(queries))


def test_deterministic_allocation():
    plan = _planner_ok_plan()
    a = compute_call_allocation(plan, 15)
    b = compute_call_allocation(plan, 15)
    assert a == b


def test_allocation_example_four_broad_six_facets_budget_fifteen():
    plan = _planner_ok_plan()
    broad, facets = split_planner_subqueries(plan)
    assert len(broad) == 4
    assert len(facets) == 6
    rows = compute_call_allocation(plan, 15)
    assert sum(r["allocated_calls"] for r in rows) == 15
    by_query = {r["query"]: r["allocated_calls"] for r in rows}
    for f in facets:
        assert by_query[f] >= 1
    for b in broad:
        assert by_query[b] >= 1
    assert sum(1 for r in rows if r["allocated_calls"] == 2) == 5
    assert sum(1 for r in rows if r["allocated_calls"] == 1) == 5


def test_planner_fallback_stays_sequential_fail_soft():
    plan = fallback_domain_only_plan("Финтех", status="PLANNER_UNAVAILABLE")
    assert planned_retrieval_phases(plan)["mode"] == "SEQUENTIAL_FAIL_SOFT"
    adapter = RecordingAdapter()
    _, meta = retrieve_openalex_v2(
        query="Финтех",
        run_id="run_test",
        adapter=adapter,  # type: ignore[arg-type]
        max_calls=15,
        plan=plan,
    )
    assert len(adapter.calls) == 1
    assert adapter.calls[0] == ("Финтех", 15)
    assert meta["openalex_calls_used"] <= 15


def test_one_invocation_per_unique_subquery():
    plan = _planner_ok_plan()
    adapter = RecordingAdapter()
    retrieve_openalex_v2(
        query="Финтех",
        run_id="r1",
        adapter=adapter,  # type: ignore[arg-type]
        max_calls=15,
        plan=plan,
    )
    assert len(adapter.calls) == 10
    assert len({q for q, _ in adapter.calls}) == 10
