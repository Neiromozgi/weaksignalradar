"""OpenAlex adapter unit tests (mocked HTTP only — no live network).

SEC-001 (stage_a_contract.json / A-03 TEST): a fake API key must never appear
in errors, logs, URLs, or snapshot files under 403/503/timeout/connection.
These tests exercise that rule with httpx.MockTransport only; they do not
claim a live Discovery PASS.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from weaksignalradar.discovery.contracts import CoverageStatus
from weaksignalradar.discovery.errors import DisallowedOriginError, DiscoveryFetchError
from weaksignalradar.discovery.openalex import OpenAlexAdapter

FAKE_KEY = "FAKE-KEY-SEC001-DO-NOT-LEAK"


def _assert_no_secret(text: str) -> None:
    assert FAKE_KEY not in text


def _adapter(tmp_path: Path, handler, *, max_retries: int = 2) -> OpenAlexAdapter:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, timeout=1.0)
    return OpenAlexAdapter(
        api_key=FAKE_KEY,
        http_client=client,
        snapshot_dir=tmp_path / "snapshots",
        max_retries=max_retries,
        sleep_func=lambda _seconds: None,
    )


def test_disallowed_origin_is_rejected() -> None:
    with pytest.raises(DisallowedOriginError):
        OpenAlexAdapter(base_url="https://evil.example/api", sleep_func=lambda _: None)


def test_search_403_returns_search_error_without_leaking_fake_key(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == f"Bearer {FAKE_KEY}"
        # Key must not be in the request URL (SEC-001: header-only).
        _assert_no_secret(str(request.url))
        return httpx.Response(403, json={"error": "forbidden"})

    adapter = _adapter(tmp_path, handler, max_retries=0)
    result = adapter.search(
        query="broad technology survey",
        scope={},
        as_of=None,
        params={"per_page": 5},
        cursor=None,
        run_id="run-403",
    )

    assert result.coverage == CoverageStatus.SEARCH_ERROR
    assert result.documents == []
    assert result.error is not None
    assert result.error.http_status == 403
    assert result.error.error_code == "HTTP_403"
    _assert_no_secret(result.error.message)
    _assert_no_secret(result.model_dump_json())


def test_search_503_exhausts_retries_as_search_error(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["n"] += 1
        return httpx.Response(503, text="unavailable")

    adapter = _adapter(tmp_path, handler, max_retries=2)
    result = adapter.search("q", {}, None, {}, None, run_id="run-503")

    assert result.coverage == CoverageStatus.SEARCH_ERROR
    assert result.error is not None
    assert result.error.http_status == 503
    assert result.error.retryable is True
    assert result.error.attempts == 3  # initial + 2 retries
    assert calls["n"] == 3
    _assert_no_secret(result.error.message)


def test_search_timeout_returns_search_error_without_leaking_key(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        raise httpx.TimeoutException(
            f"timed out while calling https://api.openalex.org/works?api_key={FAKE_KEY}"
        )

    adapter = _adapter(tmp_path, handler, max_retries=0)
    result = adapter.search("q", {}, None, {}, None, run_id="run-timeout")

    assert result.coverage == CoverageStatus.SEARCH_ERROR
    assert result.error is not None
    assert result.error.error_code == "TIMEOUT"
    _assert_no_secret(result.error.message)


def test_search_connection_error_returns_search_error_without_leaking_key(
    tmp_path: Path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        raise httpx.ConnectError(f"connection failed; key={FAKE_KEY}")

    adapter = _adapter(tmp_path, handler, max_retries=0)
    result = adapter.search("q", {}, None, {}, None, run_id="run-conn")

    assert result.coverage == CoverageStatus.SEARCH_ERROR
    assert result.error is not None
    assert result.error.error_code == "CONNECTION_ERROR"
    _assert_no_secret(result.error.message)


def test_search_success_builds_documents_and_snapshot(tmp_path: Path) -> None:
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "doi": "https://doi.org/10.1/xyz",
                "title": "Example work",
                "publication_date": "2020-01-01",
                "language": "en",
            }
        ],
        "meta": {"next_cursor": "cursor-2"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "api_key" not in str(request.url)
        return httpx.Response(200, json=payload)

    adapter = _adapter(tmp_path, handler, max_retries=0)
    result = adapter.search("lidar sensing", {}, None, {"per_page": 1}, None, run_id="run-ok")

    assert result.coverage == CoverageStatus.SEARCHED_OK
    assert result.error is None
    assert result.next_cursor == "cursor-2"
    assert len(result.documents) == 1
    doc = result.documents[0]
    assert doc.source_id == "openalex:https://openalex.org/W123"
    assert doc.run_id == "run-ok"
    assert doc.title == "Example work"
    assert doc.published_at == "2020-01-01"
    assert doc.content_hash
    assert Path(doc.snapshot_pointer).exists()
    snapshot_bytes = Path(doc.snapshot_pointer).read_bytes()
    assert json.loads(snapshot_bytes) == payload
    _assert_no_secret(snapshot_bytes.decode("utf-8"))
    _assert_no_secret(doc.model_dump_json())


def test_fetch_error_raises_discovery_fetch_error_without_leaking_key(
    tmp_path: Path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(403, json={"message": "no"})

    adapter = _adapter(tmp_path, handler, max_retries=0)
    with pytest.raises(DiscoveryFetchError) as exc_info:
        adapter.fetch("W999", run_id="run-fetch")

    _assert_no_secret(str(exc_info.value))
    _assert_no_secret(exc_info.value.error.message)
