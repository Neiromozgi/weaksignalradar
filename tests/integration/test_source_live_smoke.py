"""Bounded LIVE source smokes (opt-in via RUN_LIVE_SMOKE=1)."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_SMOKE", "").strip() != "1",
    reason="Set RUN_LIVE_SMOKE=1 to execute bounded LIVE source smokes",
)


def test_openalex_bounded_live_smoke():
    from weaksignalradar.fasttrack.sources.openalex_ft import OpenAlexFastTrackAdapter

    oa = OpenAlexFastTrackAdapter()
    result = oa.search_live_bounded(
        "quantum computing",
        run_id="smoke_openalex",
        max_calls=1,
    )
    assert result.calls_used <= 15
    assert result.pages <= 6
    assert result.coverage_state.value in {
        "FOUND",
        "NOT_FOUND_IN_SOURCE",
        "PARTIAL",
        "SEARCH_ERROR",
    }


def test_cordis_sparql_smoke():
    from weaksignalradar.fasttrack.sources.cordis import CordisAdapter

    batch = CordisAdapter().search("battery", budget_remaining=1)
    assert batch.calls_used <= 8
    assert batch.coverage_state.value in {
        "SEARCHED_OK",
        "FOUND",
        "PARTIAL",
        "SEARCH_ERROR",
        "RATE_LIMITED",
    }


def test_epo_lod_sparql_smoke():
    from weaksignalradar.fasttrack.sources.epo_lod import EpoLodAdapter

    batch = EpoLodAdapter().search("battery", budget_remaining=1)
    assert batch.calls_used <= 8
    assert batch.coverage_state.value in {
        "SEARCHED_OK",
        "FOUND",
        "PARTIAL",
        "SEARCH_ERROR",
        "RATE_LIMITED",
    }
