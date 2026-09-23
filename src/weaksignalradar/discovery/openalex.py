"""OpenAlex DiscoveryAdapter (Stage A-03 candidate source).

Scope note (07_STAGED_TASKS/STAGE_A_TICKETS_ACTIVE.md#A-03): OpenAlex 1.6
code from the historical research repository was not accessible in this
session (no verified path/commit was provided), so this adapter is a
fresh implementation written directly against
``contracts/stage_a_contract.json``, not an import of 1.6 code. It has
only been exercised against a mocked HTTP transport (see
``tests/unit/discovery/test_openalex_adapter.py``); no real network
request has been made against the live OpenAlex API. Real-source
verification is explicitly PRECHECK/TEST work, not a DEV self-PASS.

Security (SEC-001): an API key, if configured, is only ever sent as an
``Authorization`` header, never as a URL query parameter, and is never
included in any error message, log line, exception cause chain, or
snapshot. See ``discovery.security`` for the redaction helpers.
"""

from __future__ import annotations

import json
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx

from ..provenance.snapshot_store import SnapshotResult, SnapshotStore
from .contracts import CoverageStatus, SearchError, SourceDocument, SourceSearchResult
from .errors import DisallowedOriginError, DiscoveryFetchError
from .security import (
    SENSITIVE_QUERY_PARAM_NAMES,
    redact_secrets_in_bytes,
    sanitize_exception_message,
)

# HTTPS-origin allowlist (stage_a_contract.json#security.external_requests).
# Only hosts listed here may be contacted by this adapter.
ALLOWED_ORIGINS: frozenset[str] = frozenset({"api.openalex.org"})

_RETRYABLE_STATUS_CODES = frozenset({429, 503})
_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
_MAX_BACKOFF_SECONDS = 2.0


@dataclass
class OpenAlexAdapter:
    """Discovery adapter for the OpenAlex ``/works`` search endpoint.

    Not authorized/implemented here: LLM extraction, V2/V3 verification,
    classification, ranking (contracts/stage_a_contract.json#not_authorized).
    """

    base_url: str = "https://api.openalex.org"
    api_key: str | None = None
    mailto: str | None = None
    timeout_seconds: float = 10.0
    max_retries: int = 3
    snapshot_dir: str | Path = "snapshots"
    http_client: httpx.Client | None = None
    sleep_func: Callable[[float], None] = field(default=time.sleep)

    def __post_init__(self) -> None:
        parts = urlsplit(self.base_url)
        if parts.scheme != "https" or parts.hostname not in ALLOWED_ORIGINS:
            raise DisallowedOriginError(
                f"Refusing to configure adapter for non-allowlisted origin: "
                f"scheme={parts.scheme!r} host={parts.hostname!r}. "
                f"Allowed origins: {sorted(ALLOWED_ORIGINS)}"
            )
        if self.http_client is None:
            # Never auto-follow redirects: a Location off the allowlist must
            # not be contacted, and 3xx must become SEARCH_ERROR, not success.
            self.http_client = httpx.Client(timeout=self.timeout_seconds, follow_redirects=False)
        self._snapshot_store = SnapshotStore(base_dir=Path(self.snapshot_dir))

    # -- public contract ---------------------------------------------------

    def search(
        self,
        query: str,
        scope: dict[str, Any],
        as_of: str | None,
        params: dict[str, Any],
        cursor: str | None,
        *,
        run_id: str,
    ) -> SourceSearchResult:
        del scope, as_of  # accepted per contract signature; not used yet
        request_params: dict[str, Any] = {
            "search": query,
            "per-page": (params or {}).get("per_page", 25),
            "cursor": cursor or "*",
        }
        if self.mailto:
            request_params["mailto"] = self.mailto

        response, error = self._request_with_retries(f"{self.base_url}/works", request_params)
        if error is not None:
            return self._search_error_result(run_id, error)

        assert response is not None
        try:
            return self._build_success_result(run_id, response, request_params)
        except json.JSONDecodeError as exc:
            return self._search_error_result(
                run_id,
                self._make_error(
                    "INVALID_JSON",
                    attempts=1,
                    retryable=False,
                    http_status=response.status_code,
                    exc=exc,
                ),
            )

    def fetch(self, document_id: str, *, run_id: str) -> SourceDocument:
        response, error = self._request_with_retries(f"{self.base_url}/works/{document_id}", {})
        if error is not None:
            raise DiscoveryFetchError(error)

        assert response is not None
        retrieved_at = datetime.now(UTC)
        try:
            snapshot, payload = self._snapshot_and_parse(
                response, prefix=f"openalex_fetch_{run_id}"
            )
        except json.JSONDecodeError as exc:
            raise DiscoveryFetchError(
                self._make_error(
                    "INVALID_JSON",
                    attempts=1,
                    retryable=False,
                    http_status=response.status_code,
                    exc=exc,
                )
            ) from None

        if not isinstance(payload, dict):
            raise DiscoveryFetchError(
                self._make_error(
                    "INVALID_JSON",
                    attempts=1,
                    retryable=False,
                    http_status=response.status_code,
                )
            )
        return self._parse_document(payload, run_id, retrieved_at, {}, snapshot)

    # -- internals ----------------------------------------------------------

    def _redacted_secrets(self) -> list[str]:
        return [self.api_key] if self.api_key else []

    def _build_headers(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    def _backoff_sleep(self, attempt: int) -> None:
        base = 0.1 * (2 ** (attempt - 1))
        jittered = base + random.uniform(0, base * 0.1)
        self.sleep_func(min(jittered, _MAX_BACKOFF_SECONDS))

    def _make_error(
        self,
        error_code: str,
        attempt: int | None = None,
        *,
        attempts: int | None = None,
        retryable: bool,
        http_status: int | None = None,
        exc: BaseException | None = None,
    ) -> SearchError:
        resolved_attempts = attempts if attempts is not None else (attempt or 1)
        if exc is not None:
            message = sanitize_exception_message(exc, *self._redacted_secrets())
        elif http_status is not None:
            # Deliberately do not include the response body: it is not
            # ours to redact/trust, and the status code alone is enough
            # to classify the failure without risking a secret echo.
            message = f"source responded with HTTP {http_status}"
        else:
            message = error_code
        return SearchError(
            error_code=error_code,
            message=message,
            http_status=http_status,
            retryable=retryable,
            attempts=resolved_attempts,
        )

    @staticmethod
    def _search_error_result(run_id: str, error: SearchError) -> SourceSearchResult:
        return SourceSearchResult(
            run_id=run_id,
            documents=[],
            next_cursor=None,
            coverage=CoverageStatus.SEARCH_ERROR,
            error=error,
        )

    def _is_allowlisted_location(self, location: str) -> bool:
        absolute = urljoin(self.base_url.rstrip("/") + "/", location)
        parts = urlsplit(absolute)
        return parts.scheme == "https" and parts.hostname in ALLOWED_ORIGINS

    def _redirect_error(self, response: httpx.Response, attempt: int) -> SearchError:
        location = response.headers.get("Location")
        if location and not self._is_allowlisted_location(location):
            return self._make_error(
                "REDIRECT_DISALLOWED_ORIGIN",
                attempt,
                retryable=False,
                http_status=response.status_code,
            )
        return self._make_error(
            f"HTTP_{response.status_code}",
            attempt,
            retryable=False,
            http_status=response.status_code,
        )

    def _request_with_retries(
        self, url: str, request_params: dict[str, Any]
    ) -> tuple[httpx.Response | None, SearchError | None]:
        """bounded retry only; 403 auth error, 429/503 bounded backoff;
        3xx never followed; terminal error SEARCH_ERROR, never fixture fallback
        (stage_a_contract.json#search_interface.error_policy).
        """
        attempt = 0
        last_error: SearchError | None = None

        while attempt <= self.max_retries:
            attempt += 1
            try:
                # follow_redirects=False on every call so a caller-supplied
                # Client cannot silently hop to a non-allowlisted host.
                response = self.http_client.get(
                    url,
                    params=request_params,
                    headers=self._build_headers(),
                    follow_redirects=False,
                )
            except httpx.TimeoutException as exc:
                last_error = self._make_error("TIMEOUT", attempt, retryable=True, exc=exc)
                if attempt <= self.max_retries:
                    self._backoff_sleep(attempt)
                    continue
                return None, last_error
            except httpx.ConnectError as exc:
                last_error = self._make_error("CONNECTION_ERROR", attempt, retryable=True, exc=exc)
                if attempt <= self.max_retries:
                    self._backoff_sleep(attempt)
                    continue
                return None, last_error
            except httpx.HTTPError as exc:
                last_error = self._make_error(
                    "HTTP_CLIENT_ERROR", attempt, retryable=False, exc=exc
                )
                return None, last_error

            if response.status_code in _REDIRECT_STATUS_CODES:
                return None, self._redirect_error(response, attempt)

            if response.status_code == 403:
                return None, self._make_error("HTTP_403", attempt, retryable=False, http_status=403)

            if response.status_code in _RETRYABLE_STATUS_CODES:
                last_error = self._make_error(
                    f"HTTP_{response.status_code}",
                    attempt,
                    retryable=True,
                    http_status=response.status_code,
                )
                if attempt <= self.max_retries:
                    self._backoff_sleep(attempt)
                    continue
                return None, last_error

            if response.status_code >= 400:
                return None, self._make_error(
                    f"HTTP_{response.status_code}",
                    attempt,
                    retryable=False,
                    http_status=response.status_code,
                )

            if response.status_code < 200 or response.status_code >= 300:
                # Any non-2xx that slipped past (including other 3xx) is error.
                return None, self._make_error(
                    f"HTTP_{response.status_code}",
                    attempt,
                    retryable=False,
                    http_status=response.status_code,
                )

            return response, None

        return None, last_error

    def _snapshot_and_parse(
        self, response: httpx.Response, *, prefix: str
    ) -> tuple[SnapshotResult, Any]:
        """Redact secrets, persist bytes, hash those bytes, then parse JSON.

        content_hash on SourceDocument must equal sha256 of the saved
        snapshot bytes (stage_a_contract.json#SourceDocument.notes).
        """
        safe_bytes = redact_secrets_in_bytes(response.content, *self._redacted_secrets())
        snapshot = self._snapshot_store.save(safe_bytes, prefix=prefix)
        payload = json.loads(safe_bytes)
        return snapshot, payload

    def _build_success_result(
        self, run_id: str, response: httpx.Response, request_params: dict[str, Any]
    ) -> SourceSearchResult:
        retrieved_at = datetime.now(UTC)
        snapshot, payload = self._snapshot_and_parse(response, prefix=f"openalex_search_{run_id}")
        if not isinstance(payload, dict):
            raise json.JSONDecodeError("payload is not an object", "", 0)
        results = payload.get("results", [])
        next_cursor = (payload.get("meta") or {}).get("next_cursor")

        documents = [
            self._parse_document(item, run_id, retrieved_at, request_params, snapshot)
            for item in results
            if isinstance(item, dict)
        ]
        return SourceSearchResult(
            run_id=run_id,
            documents=documents,
            next_cursor=next_cursor,
            coverage=CoverageStatus.SEARCHED_OK,
            error=None,
        )

    @staticmethod
    def _parse_document(
        item: dict[str, Any],
        run_id: str,
        retrieved_at: datetime,
        request_params: dict[str, Any],
        snapshot: SnapshotResult,
    ) -> SourceDocument:
        openalex_id = item.get("id") or "UNKNOWN"
        doi = item.get("doi")
        origin = doi or openalex_id
        title = item.get("title") or item.get("display_name") or "UNTITLED"
        published_at = item.get("publication_date")
        language = item.get("language")
        safe_params = {
            k: v for k, v in request_params.items() if k.lower() not in SENSITIVE_QUERY_PARAM_NAMES
        }

        return SourceDocument(
            source_id=f"openalex:{openalex_id}",
            run_id=run_id,
            origin_url_or_official_id=origin,
            title=title,
            retrieved_at=retrieved_at,
            request_params=safe_params,
            # Contract: hash snapshot bytes (not the per-item JSON).
            content_hash=snapshot.content_hash,
            snapshot_pointer=snapshot.path,
            source_type="scholarly_work",
            coverage=CoverageStatus.SEARCHED_OK,
            language=language,
            published_at=published_at,
            primary_origin_id=openalex_id,
        )
