"""OpenAlex FastTrack normalization (REQUIRED_REFERENCE_SOURCE)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from weaksignalradar.discovery.openalex import OpenAlexAdapter

from .budget import OPENALEX_HARD_CUTOFF_SEC, OPENALEX_MAX_PAGES, OPENALEX_MAX_WORKS
from .contract import (
    CoverageState,
    NormalizedSourceDocument,
    OriginalAvailability,
    SourceBatch,
    SourceHealth,
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
            )
        snapshot_id = f"snap_{run_id}_openalex"
        if result.documents:
            snapshot_id = result.documents[0].snapshot_pointer or snapshot_id
        docs: list[NormalizedSourceDocument] = []
        for doc in result.documents:
            meta = {
                "origin_url_or_official_id": doc.origin_url_or_official_id,
                "coverage": doc.coverage,
            }
            year = None
            if doc.published_at:
                try:
                    year = int(str(doc.published_at)[:4])
                except ValueError:
                    year = None
            docs.append(
                NormalizedSourceDocument(
                    source_document_id=f"doc_{hashlib.sha256(doc.source_id.encode()).hexdigest()[:16]}",
                    source_id=doc.source_id,
                    source_type="openalex_work",
                    stable_external_id=doc.source_id,
                    title=doc.title,
                    year=year,
                    canonical_url=doc.origin_url_or_official_id,
                    original_availability_status=OriginalAvailability.METADATA_ONLY,
                    metadata_json=meta,
                    source_snapshot_id=snapshot_id,
                    retrieved_at=doc.retrieved_at.isoformat(),
                    content_hash_of_api_record=doc.content_hash,
                    coverage_state=CoverageState.FOUND,
                    abstract=None,
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
        wid = work.get("id") or work.get("openalex_id") or ""
        title = (work.get("title") or work.get("display_name") or "Untitled").strip()
        abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
        year = work.get("publication_year")
        ids_map = work.get("ids") or {}
        doi = ids_map.get("doi") if isinstance(ids_map, dict) else None
        landing = (work.get("primary_location") or {}).get("landing_page_url") or wid
        raw_hash = hashlib.sha256(json.dumps(work, sort_keys=True).encode()).hexdigest()
        orgs = []
        for auth in work.get("authorships") or []:
            inst = (auth.get("institutions") or [{}])[0]
            name = inst.get("display_name")
            if name:
                orgs.append(name)
        avail = (
            OriginalAvailability.ABSTRACT_AVAILABLE
            if abstract
            else OriginalAvailability.METADATA_ONLY
        )
        return NormalizedSourceDocument(
            source_document_id=f"doc_{hashlib.sha256(wid.encode()).hexdigest()[:16]}",
            source_id=wid,
            source_type="openalex_work",
            stable_external_id=wid,
            title=title,
            year=int(year) if year is not None else None,
            canonical_url=str(landing),
            doi=doi,
            original_availability_status=avail,
            metadata_json={"openalex": work},
            source_snapshot_id=snapshot_id,
            retrieved_at=datetime.now(UTC).isoformat(),
            content_hash_of_api_record=raw_hash,
            coverage_state=CoverageState.FOUND,
            organization_names=orgs,
            abstract=abstract,
        )


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


def _reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str | None:
    if not inverted:
        return None
    max_pos = max((max(positions) for positions in inverted.values()), default=-1)
    if max_pos < 0:
        return None
    words: list[str] = [""] * (max_pos + 1)
    for word, positions in inverted.items():
        for p in positions:
            words[p] = word
    text = " ".join(w for w in words if w).strip()
    return text or None
