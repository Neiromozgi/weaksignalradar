"""FastTrack source adapter contract (handoff 06)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class OriginalAvailability(StrEnum):
    FULL_TEXT_AVAILABLE_BY_LINK = "FULL_TEXT_AVAILABLE_BY_LINK"
    ABSTRACT_AVAILABLE = "ABSTRACT_AVAILABLE"
    METADATA_ONLY = "METADATA_ONLY"
    LINK_ONLY = "LINK_ONLY"
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class CoverageState(StrEnum):
    FOUND = "FOUND"
    SEARCHED_OK = "SEARCHED_OK"
    NOT_FOUND_IN_SOURCE = "NOT_FOUND_IN_SOURCE"
    PARTIAL = "PARTIAL"
    SEARCH_ERROR = "SEARCH_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    BLOCKED_ACCESS = "BLOCKED_ACCESS"
    BLOCKED_COST = "BLOCKED_COST"
    NOT_RUN = "NOT_RUN"


@dataclass(slots=True)
class NormalizedSourceDocument:
    source_document_id: str
    source_id: str
    source_type: str
    stable_external_id: str
    title: str
    year: int | None
    canonical_url: str
    original_availability_status: OriginalAvailability
    metadata_json: dict[str, Any]
    source_snapshot_id: str
    retrieved_at: str
    content_hash_of_api_record: str
    coverage_state: CoverageState
    doi: str | None = None
    organization_names: list[str] = field(default_factory=list)
    abstract: str | None = None


@dataclass(slots=True)
class SourceHealth:
    source_id: str
    status: str
    detail: str = ""


@dataclass(slots=True)
class SourceBatch:
    documents: list[NormalizedSourceDocument]
    coverage_state: CoverageState
    cursor: str | None = None
    calls_used: int = 0


class SourceAdapter(Protocol):
    source_id: str
    source_class: str

    def health(self) -> SourceHealth: ...
    def search(
        self,
        query: str,
        budget_remaining: int,
        cursor: str | None = None,
    ) -> SourceBatch: ...
