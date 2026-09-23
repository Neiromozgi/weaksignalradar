"""Data contracts for the Stage A Discovery interface.

These models mirror the required/optional fields defined in
``contracts/stage_a_contract.json`` (SourceSearchResult, SourceDocument,
coverage enum). They intentionally do not add any V2/V3 verification,
bucket, or ranking fields, which are out of scope for Stage A.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class CoverageStatus(StrEnum):
    """Exact enum from stage_a_contract.json#coverage.enum.

    Never infer absence of a technology/market from a coverage value;
    coverage only describes how the search run/source behaved.
    """

    SEARCHED_OK = "SEARCHED_OK"
    PARTIAL = "PARTIAL"
    SEARCH_ERROR = "SEARCH_ERROR"
    NOT_SEARCHED = "NOT_SEARCHED"
    UNAVAILABLE = "UNAVAILABLE"


class SearchError(BaseModel):
    """Structured, redacted error (stage_a_contract.json#SourceSearchResult.error).

    ``message`` MUST already be redacted (no API keys, no secrets, no raw
    exception chain) by the time this object is constructed. See
    ``discovery.security`` for the redaction helpers used to build it.
    """

    model_config = ConfigDict(frozen=True)

    error_code: str
    message: str
    http_status: int | None = None
    retryable: bool = False
    attempts: int = 1


class SourceDocument(BaseModel):
    """stage_a_contract.json#SourceDocument."""

    model_config = ConfigDict(frozen=True)

    # required
    source_id: str
    run_id: str
    origin_url_or_official_id: str
    title: str
    retrieved_at: datetime
    request_params: dict
    content_hash: str
    snapshot_pointer: str
    source_type: str
    coverage: CoverageStatus

    # optional_nullable
    author_or_org: str | None = None
    language: str | None = None
    published_at: str | None = None
    event_at: str | None = None
    publicly_available_at: str | None = None
    primary_origin_id: str | None = None


class SourceSearchResult(BaseModel):
    """stage_a_contract.json#SourceSearchResult.

    ``documents`` is empty on error: an empty list is NOT itself a
    successful empty search unless ``coverage`` says so.
    """

    model_config = ConfigDict(frozen=True)

    run_id: str
    documents: list[SourceDocument]
    next_cursor: str | None
    coverage: CoverageStatus
    error: SearchError | None
