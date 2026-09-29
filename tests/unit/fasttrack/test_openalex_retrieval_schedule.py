"""OpenAlex v2 retrieval budget scheduling (LIVE #3 patch)."""

from __future__ import annotations

from dataclasses import dataclass, field

from weaksignalradar.fasttrack.discovery_v2.query_planner import (
    fallback_domain_only_plan,
    split_planner_subqueries,
)
from weaksignalradar.fasttrack.discovery_v2.retrieval import (
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
    pages_per_call: int = 1

    def search_live_bounded(
        self,
        query: str,
        *,
        run_id: str,
        max_calls: int,
    ) -> OpenAlexLiveResult:
        del run_id
        use = min(max(self.pages_per_call, 0), max_calls)
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
        return OpenAlexLiveResult(
            documents=[doc] if use else [],
            coverage_state=CoverageState.FOUND,
            calls_used=use,
            pages=use or 1,
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


def test_total_openalex_calls_never_exceed_cap():
    plan = _planner_ok_plan()
    adapter = RecordingAdapter()
    _, meta = retrieve_openalex_v2(
        query="Финтех",
        run_id="run_test",
        adapter=adapter,  # type: ignore[arg-type]
        max_calls=15,
        plan=plan,
    )
    assert meta["openalex_calls_used"] <= 15


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
    assert adapter.calls[0][0] == "Финтех"
    assert meta["openalex_calls_used"] <= 15


def test_deterministic_call_order():
    plan = _planner_ok_plan()
    a1 = RecordingAdapter()
    a2 = RecordingAdapter()
    retrieve_openalex_v2(
        query="Финтех",
        run_id="r1",
        adapter=a1,  # type: ignore[arg-type]
        max_calls=15,
        plan=plan,
    )
    retrieve_openalex_v2(
        query="Финтех",
        run_id="r2",
        adapter=a2,  # type: ignore[arg-type]
        max_calls=15,
        plan=plan,
    )
    assert [q for q, _ in a1.calls] == [q for q, _ in a2.calls]
    _, facets = split_planner_subqueries(plan)
    for facet in facets:
        assert facet in [q for q, _ in a1.calls]


def test_live3_like_budget_does_not_starve_facets():
    plan = _planner_ok_plan()
    broad, facets = split_planner_subqueries(plan)

    @dataclass
    class GreedyBroadAdapter(RecordingAdapter):
        def search_live_bounded(
            self,
            query: str,
            *,
            run_id: str,
            max_calls: int,
        ) -> OpenAlexLiveResult:
            if query in broad:
                self.pages_per_call = min(max_calls, 6)
            else:
                self.pages_per_call = 1
            return super().search_live_bounded(query, run_id=run_id, max_calls=max_calls)

    adapter = GreedyBroadAdapter()
    _, meta = retrieve_openalex_v2(
        query="Финтех",
        run_id="run_live3",
        adapter=adapter,  # type: ignore[arg-type]
        max_calls=15,
        plan=plan,
    )
    assert meta["openalex_calls_used"] == 15
    assert len({q for q, _ in adapter.calls if q in facets}) == 6
