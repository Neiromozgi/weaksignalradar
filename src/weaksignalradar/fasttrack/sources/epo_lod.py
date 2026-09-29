"""EPO Linked Open EP Data SPARQL adapter (addendum v1.0.2)."""

from __future__ import annotations

import hashlib
import os
import re
from datetime import UTC, datetime

from .contract import (
    CoverageState,
    NormalizedSourceDocument,
    OriginalAvailability,
    SourceBatch,
    SourceHealth,
)
from .sparql import binding_value, run_sparql

DEFAULT_ENDPOINT = "https://data.epo.org/linked-data/query"


class EpoLodAdapter:
    source_id = "epo_lod"
    source_class = "REQUIRED_ATTEMPT_FAIL_SOFT"

    def __init__(self, *, endpoint: str | None = None) -> None:
        self._endpoint = (
            endpoint or os.environ.get("EPO_SPARQL_ENDPOINT") or DEFAULT_ENDPOINT
        ).strip()

    def health(self) -> SourceHealth:
        return SourceHealth(
            source_id=self.source_id,
            status="CONFIGURED",
            detail="EPO Linked Open EP Data SPARQL",
        )

    def search(self, query: str, budget_remaining: int, cursor: str | None = None) -> SourceBatch:
        del cursor
        if budget_remaining <= 0:
            return SourceBatch(
                documents=[], coverage_state=CoverageState.RATE_LIMITED, calls_used=0
            )
        if os.environ.get("EPO_LIVE_DISABLED", "").strip().lower() in {"1", "true", "yes"}:
            return SourceBatch(documents=[], coverage_state=CoverageState.NOT_RUN, calls_used=0)
        token = _safe_token(query)
        if not token:
            return SourceBatch(documents=[], coverage_state=CoverageState.SEARCHED_OK, calls_used=0)
        sparql = f"""
PREFIX patent: <http://data.epo.org/linked-data/def/patent/>
SELECT ?pub ?title ?date WHERE {{
  ?pub patent:titleOfInvention ?title .
  OPTIONAL {{ ?pub patent:publicationDate ?date }}
  FILTER(CONTAINS(LCASE(STR(?title)), "{token}"))
}} LIMIT 25
"""
        result = run_sparql(self._endpoint, sparql, timeout_s=60.0)
        if not result.ok:
            safe_error = result.error or "search_error"
            if safe_error == "timeout":
                return SourceBatch(
                    documents=[],
                    coverage_state=CoverageState.PARTIAL,
                    calls_used=1,
                    error=safe_error,
                )
            return SourceBatch(
                documents=[],
                coverage_state=CoverageState.SEARCH_ERROR,
                calls_used=1,
                error=safe_error,
            )
        docs: list[NormalizedSourceDocument] = []
        for row in result.bindings:
            pub = binding_value(row, "pub") or ""
            title = binding_value(row, "title") or "Untitled patent"
            date_s = binding_value(row, "date")
            year = int(date_s[:4]) if date_s and len(date_s) >= 4 and date_s[:4].isdigit() else None
            if not pub:
                continue
            docs.append(
                NormalizedSourceDocument(
                    source_document_id=f"doc_{hashlib.sha256(pub.encode()).hexdigest()[:16]}",
                    source_id=pub,
                    source_type="epo_publication",
                    stable_external_id=pub,
                    title=title,
                    year=year,
                    canonical_url=pub
                    if pub.startswith("http")
                    else f"https://data.epo.org/publication-databank/{pub}",
                    original_availability_status=OriginalAvailability.METADATA_ONLY,
                    metadata_json={"epo": {"publication": pub, "title": title, "date": date_s}},
                    source_snapshot_id="epo_lod_sparql_live",
                    retrieved_at=datetime.now(UTC).isoformat(),
                    content_hash_of_api_record=hashlib.sha256(f"{pub}{title}".encode()).hexdigest(),
                    coverage_state=CoverageState.FOUND,
                    organization_names=[],
                    abstract=None,
                )
            )
        cov = (
            CoverageState.SEARCHED_OK
            if result.ok and not docs
            else CoverageState.FOUND
            if docs
            else CoverageState.PARTIAL
        )
        if result.ok and not docs:
            cov = CoverageState.SEARCHED_OK
        return SourceBatch(documents=docs, coverage_state=cov, calls_used=1)


def _safe_token(query: str) -> str:
    words = re.findall(r"[\w\u0080-\uFFFF]{3,}", query.lower())
    return words[0].replace('"', "") if words else ""
