"""CORDIS / EURIO public SPARQL adapter (addendum v1.0.2)."""

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

DEFAULT_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"
MAX_PROJECTS = 250


class CordisAdapter:
    source_id = "cordis"
    source_class = "REQUIRED_ATTEMPT_FAIL_SOFT"

    def __init__(self, *, endpoint: str | None = None) -> None:
        self._endpoint = (
            endpoint or os.environ.get("CORDIS_SPARQL_ENDPOINT") or DEFAULT_ENDPOINT
        ).strip()

    def health(self) -> SourceHealth:
        return SourceHealth(
            source_id=self.source_id,
            status="CONFIGURED",
            detail="public SPARQL (EURIO LOD); no API key required for P0",
        )

    def search(self, query: str, budget_remaining: int, cursor: str | None = None) -> SourceBatch:
        del cursor
        if budget_remaining <= 0:
            return SourceBatch(
                documents=[], coverage_state=CoverageState.RATE_LIMITED, calls_used=0
            )
        token = _safe_token(query)
        if not token:
            return SourceBatch(documents=[], coverage_state=CoverageState.SEARCHED_OK, calls_used=0)
        sparql = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?project ?title WHERE {{
  ?project rdfs:label ?title .
  FILTER(CONTAINS(LCASE(STR(?title)), "{token}"))
}} LIMIT 25
"""
        result = run_sparql(self._endpoint, sparql, timeout_s=60.0)
        if not result.ok:
            if result.error == "timeout":
                return SourceBatch(documents=[], coverage_state=CoverageState.PARTIAL, calls_used=1)
            return SourceBatch(
                documents=[], coverage_state=CoverageState.SEARCH_ERROR, calls_used=1
            )
        docs: list[NormalizedSourceDocument] = []
        for row in result.bindings[:MAX_PROJECTS]:
            pid = binding_value(row, "project") or ""
            title = binding_value(row, "title") or "Untitled project"
            if not pid:
                continue
            docs.append(
                NormalizedSourceDocument(
                    source_document_id=f"doc_{hashlib.sha256(pid.encode()).hexdigest()[:16]}",
                    source_id=pid,
                    source_type="cordis_project",
                    stable_external_id=pid,
                    title=title,
                    year=None,
                    canonical_url=pid
                    if pid.startswith("http")
                    else f"https://cordis.europa.eu/project/id/{pid}",
                    original_availability_status=OriginalAvailability.METADATA_ONLY,
                    metadata_json={"cordis": {"project": pid, "title": title}},
                    source_snapshot_id="cordis_sparql_live",
                    retrieved_at=datetime.now(UTC).isoformat(),
                    content_hash_of_api_record=hashlib.sha256(f"{pid}{title}".encode()).hexdigest(),
                    coverage_state=CoverageState.FOUND,
                    organization_names=[],
                    abstract=None,
                )
            )
        cov = CoverageState.SEARCHED_OK if result.ok else CoverageState.PARTIAL
        if result.ok and not docs:
            cov = CoverageState.SEARCHED_OK
        elif docs:
            cov = CoverageState.FOUND
        return SourceBatch(documents=docs, coverage_state=cov, calls_used=1)


def _safe_token(query: str) -> str:
    words = re.findall(r"[\w\u0080-\uFFFF]{3,}", query.lower())
    return words[0].replace('"', "") if words else ""
