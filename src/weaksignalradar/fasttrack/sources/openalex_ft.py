"""OpenAlex FastTrack normalization (REQUIRED_REFERENCE_SOURCE)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from weaksignalradar.discovery.openalex import OpenAlexAdapter

from .budget import OPENALEX_HARD_CUTOFF_SEC, OPENALEX_MAX_PAGES, OPENALEX_MAX_WORKS
from .contract import (
    CoverageState,
    NormalizedSourceDocument,
    SourceBatch,
    SourceHealth,
)
from .openalex_normalize import (
    index_works_from_snapshot,
    normalize_openalex_work,
    openalex_id_from_source_document,
)


class OpenAlexFastTrackAdapter:
    source_id = "openalex"
    source_class = "REQUIRED_REFERENCE_SOURCE"

    def __init__(self, *, adapter: OpenAlexAdapter | None = None) -> None:
        self._adapter = adapter or _build_stage_a_openalex_adapter()

    def health(self) -> SourceHealth:
        return SourceHealth(source_id=self.source_id, status="CONFIGURED")

    def search_from_fixture(
        self,
        works: list[dict[str, Any]],
        *,
        snapshot_id: str,
    ) -> SourceBatch:
        docs = [self._normalize_work(w, snapshot_id=snapshot_id) for w in works]
        return SourceBatch(documents=docs, coverage_state=CoverageState.FOUND, calls_used=0)

    def search_live(
        self,
        query: str,
        budget_remaining: int,
        *,
        run_id: str,
        cursor: str | None = None,
    ) -> SourceBatch:
        if budget_remaining <= 0:
            return SourceBatch(
                documents=[],
                coverage_state=CoverageState.BLOCKED_COST,
                calls_used=0,
            )
        result = self._adapter.search(
            query,
            scope={},
            as_of=None,
            params={"per_page": min(25, budget_remaining)},
            cursor=cursor,
            run_id=run_id,
        )
        if result.error is not None:
            return SourceBatch(
                documents=[],
                coverage_state=CoverageState.SEARCH_ERROR,
                calls_used=1,
                error=result.error.error_code,
            )
        snapshot_id = f"snap_{run_id}_openalex"
        work_index: dict[str, dict[str, Any]] = {}
        if result.documents:
            snapshot_id = result.documents[0].snapshot_pointer or snapshot_id
            work_index = index_works_from_snapshot(result.documents[0].snapshot_pointer)
        docs: list[NormalizedSourceDocument] = []
        for doc in result.documents:
            oa_id = openalex_id_from_source_document(doc.source_id, doc.primary_origin_id)
            work = work_index.get(oa_id)
            if work is not None:
                docs.append(
                    normalize_openalex_work(
                        work,
                        snapshot_id=snapshot_id,
                        retrieved_at=doc.retrieved_at.isoformat(),
                    )
                )
            else:
                docs.append(
                    normalize_openalex_work(
                        {
                            "id": oa_id,
                            "title": doc.title,
                            "publication_date": doc.published_at,
                        },
                        snapshot_id=snapshot_id,
                        retrieved_at=doc.retrieved_at.isoformat(),
                    )
                )
        return SourceBatch(
            documents=docs,
            coverage_state=CoverageState.FOUND if docs else CoverageState.NOT_FOUND_IN_SOURCE,
            cursor=result.next_cursor,
            calls_used=1,
        )

    def search_live_bounded(
        self,
        query: str,
        *,
        run_id: str,
        max_calls: int,
    ) -> OpenAlexLiveResult:
        """Paginated OpenAlex acquisition with frozen caps."""
        started = time.monotonic()
        calls = 0
        cursor: str | None = None
        all_docs: list[NormalizedSourceDocument] = []
        seen: set[str] = set()
        cap_reached = False
        pages = 0
        last_cov = CoverageState.NOT_FOUND_IN_SOURCE
        while (
            calls < max_calls and pages < OPENALEX_MAX_PAGES and len(all_docs) < OPENALEX_MAX_WORKS
        ):
            if time.monotonic() - started > OPENALEX_HARD_CUTOFF_SEC:
                cap_reached = True
                last_cov = CoverageState.PARTIAL
                break
            batch = self.search_live(
                query,
                max(0, max_calls - calls),
                run_id=run_id,
                cursor=cursor,
            )
            calls += batch.calls_used
            pages += 1
            last_cov = batch.coverage_state
            if batch.coverage_state == CoverageState.SEARCH_ERROR:
                break
            for doc in batch.documents:
                if doc.stable_external_id in seen:
                    continue
                seen.add(doc.stable_external_id)
                all_docs.append(doc)
                if len(all_docs) >= OPENALEX_MAX_WORKS:
                    cap_reached = True
                    break
            cursor = batch.cursor
            if not cursor or cursor == "*":
                break
        if cap_reached and last_cov == CoverageState.FOUND:
            last_cov = CoverageState.PARTIAL
        if all_docs and last_cov not in {CoverageState.SEARCH_ERROR, CoverageState.PARTIAL}:
            last_cov = CoverageState.FOUND
        return OpenAlexLiveResult(
            documents=all_docs,
            coverage_state=last_cov,
            calls_used=calls,
            pages=pages,
            cap_reached=cap_reached,
            elapsed_sec=time.monotonic() - started,
        )

    def _normalize_work(
        self, work: dict[str, Any], *, snapshot_id: str
    ) -> NormalizedSourceDocument:
        return normalize_openalex_work(work, snapshot_id=snapshot_id)


@dataclass(slots=True)
class OpenAlexLiveResult:
    documents: list[NormalizedSourceDocument]
    coverage_state: CoverageState
    calls_used: int
    pages: int
    cap_reached: bool
    elapsed_sec: float


def _build_stage_a_openalex_adapter() -> OpenAlexAdapter:
    """Reuse Stage A credential path (SOURCE_API_KEY / mailto), never logged."""
    return OpenAlexAdapter(
        api_key=os.environ.get("SOURCE_API_KEY", "").strip() or None,
        mailto=os.environ.get("OPENALEX_MAILTO", "").strip() or None,
        base_url=os.environ.get("SOURCE_BASE_URL", "").strip() or "https://api.openalex.org",
    )
