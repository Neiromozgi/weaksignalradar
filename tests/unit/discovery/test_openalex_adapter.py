"""OpenAlex adapter unit tests (mocked HTTP only — no live network).

SEC-001 (stage_a_contract.json / A-03 TEST): a fake API key must never appear
in errors, logs, URLs, snapshots, or full traceback dumps (including cause
chains). These tests use httpx.MockTransport only; they do not claim a live
Discovery PASS.
"""

from __future__ import annotations

import hashlib
import json
import traceback
from pathlib import Path

import httpx
import pytest

from weaksignalradar.discovery.contracts import CoverageStatus
from weaksignalradar.discovery.errors import DisallowedOriginError, DiscoveryFetchError
from weaksignalradar.discovery.openalex import OpenAlexAdapter
from weaksignalradar.discovery.security import format_exception_redacted

FAKE_KEY = "FAKE-KEY-SEC001-DO-NOT-LEAK"


def _assert_no_secret(text: str) -> None:
    assert FAKE_KEY not in text


def _adapter(tmp_path: Path, handler, *, max_retries: int = 2) -> OpenAlexAdapter:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, timeout=1.0, follow_redirects=False)
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


@pytest.mark.parametrize("status", [301, 302, 307])
def test_search_redirect_statuses_are_search_error_not_success(tmp_path: Path, status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            status,
            headers={"Location": "https://api.openalex.org/works?cursor=next"},
        )

    adapter = _adapter(tmp_path, handler, max_retries=0)
    result = adapter.search("q", {}, None, {}, None, run_id=f"run-{status}")

    assert result.coverage == CoverageStatus.SEARCH_ERROR
    assert result.documents == []
    assert result.error is not None
    assert result.error.http_status == status
    assert result.error.error_code == f"HTTP_{status}"
    _assert_no_secret(result.error.message)


def test_search_redirect_to_disallowed_origin(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(302, headers={"Location": "https://evil.example/steal?api_key=x"})

    adapter = _adapter(tmp_path, handler, max_retries=0)
    result = adapter.search("q", {}, None, {}, None, run_id="run-redir-evil")

    assert result.coverage == CoverageStatus.SEARCH_ERROR
    assert result.error is not None
    assert result.error.error_code == "REDIRECT_DISALLOWED_ORIGIN"
    assert result.error.http_status == 302
    _assert_no_secret(result.error.message)


def test_search_200_with_invalid_json_is_search_error(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, content=b"not-json{{{")

    adapter = _adapter(tmp_path, handler, max_retries=0)
    result = adapter.search("q", {}, None, {}, None, run_id="run-bad-json")

    assert result.coverage == CoverageStatus.SEARCH_ERROR
    assert result.documents == []
    assert result.error is not None
    assert result.error.error_code == "INVALID_JSON"
    _assert_no_secret(result.error.message)


def test_fetch_200_with_invalid_json_raises_without_leaking_key(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, content=b"<html>not json</html>")

    adapter = _adapter(tmp_path, handler, max_retries=0)
    with pytest.raises(DiscoveryFetchError) as exc_info:
        adapter.fetch("W1", run_id="run-fetch-bad-json")

    assert exc_info.value.error.error_code == "INVALID_JSON"
    _assert_no_secret(str(exc_info.value))
    _assert_no_secret(exc_info.value.error.message)
    formatted = "".join(
        traceback.format_exception(
            type(exc_info.value), exc_info.value, exc_info.value.__traceback__
        )
    )
    _assert_no_secret(formatted)
    _assert_no_secret(format_exception_redacted(exc_info.value, FAKE_KEY))


def test_search_echoes_key_in_body_is_redacted_from_snapshot(tmp_path: Path) -> None:
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "title": "Echo test",
                "echoed_key": FAKE_KEY,
            }
        ],
        "meta": {},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json=payload)

    adapter = _adapter(tmp_path, handler, max_retries=0)
    result = adapter.search("q", {}, None, {}, None, run_id="run-echo")

    assert result.coverage == CoverageStatus.SEARCHED_OK
    assert len(result.documents) == 1
    doc = result.documents[0]
    snapshot_bytes = Path(doc.snapshot_pointer).read_bytes()
    _assert_no_secret(snapshot_bytes.decode("utf-8"))
    assert hashlib.sha256(snapshot_bytes).hexdigest() == doc.content_hash
    assert doc.content_hash == hashlib.sha256(snapshot_bytes).hexdigest()


def test_content_hash_matches_saved_snapshot_bytes(tmp_path: Path) -> None:
    payload = {
        "results": [{"id": "https://openalex.org/W2", "title": "Hash check"}],
        "meta": {},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json=payload)

    adapter = _adapter(tmp_path, handler, max_retries=0)
    result = adapter.search("q", {}, None, {}, None, run_id="run-hash")
    doc = result.documents[0]
    saved = Path(doc.snapshot_pointer).read_bytes()
    assert doc.content_hash == hashlib.sha256(saved).hexdigest()


def test_exception_cause_chain_does_not_leak_key_in_full_traceback(
    tmp_path: Path,
) -> None:
    """Adapter boundary must not leave a secret-bearing __cause__ attached."""

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        # Simulate a library error whose message embeds the key; then wrap
        # in a way that would historically leak via cause chains.
        raise httpx.ConnectError(f"dial failed key={FAKE_KEY}")

    adapter = _adapter(tmp_path, handler, max_retries=0)
    with pytest.raises(DiscoveryFetchError) as exc_info:
        adapter.fetch("Wleak", run_id="run-chain")

    err = exc_info.value
    assert err.__cause__ is None
    assert err.__context__ is None
    raw = "".join(traceback.format_exception(type(err), err, err.__traceback__))
    _assert_no_secret(raw)
    _assert_no_secret(format_exception_redacted(err, FAKE_KEY))
    _assert_no_secret(err.error.message)


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
    assert result.error.attempts == 3
    assert calls["n"] == 3
    _assert_no_secret(result.error.message)


def test_search_429_exhausts_bounded_retries(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["n"] += 1
        return httpx.Response(429, text="rate limited")

    adapter = _adapter(tmp_path, handler, max_retries=2)
    result = adapter.search("q", {}, None, {}, None, run_id="run-429")

    assert result.coverage == CoverageStatus.SEARCH_ERROR
    assert result.error is not None
    assert result.error.http_status == 429
    assert result.error.retryable is True
    assert result.error.attempts == 3
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
    snapshot_bytes = Path(doc.snapshot_pointer).read_bytes()
    assert doc.content_hash == hashlib.sha256(snapshot_bytes).hexdigest()
    assert json.loads(snapshot_bytes) == payload
    _assert_no_secret(snapshot_bytes.decode("utf-8"))
    _assert_no_secret(doc.model_dump_json())


def test_fetch_success_provenance_without_key_leak(tmp_path: Path) -> None:
    item = {
        "id": "https://openalex.org/W777",
        "title": "Fetched work",
        "publication_date": "2021-02-03",
        "language": "en",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "api_key" not in str(request.url)
        assert request.headers.get("Authorization") == f"Bearer {FAKE_KEY}"
        return httpx.Response(200, json=item)

    adapter = _adapter(tmp_path, handler, max_retries=0)
    doc = adapter.fetch("W777", run_id="run-fetch-ok")

    assert doc.source_id == "openalex:https://openalex.org/W777"
    assert doc.run_id == "run-fetch-ok"
    assert doc.title == "Fetched work"
    saved = Path(doc.snapshot_pointer).read_bytes()
    assert doc.content_hash == hashlib.sha256(saved).hexdigest()
    _assert_no_secret(saved.decode("utf-8"))
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


def test_fetch_redirect_disallowed_origin(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(307, headers={"Location": "http://evil.example/x"})

    adapter = _adapter(tmp_path, handler, max_retries=0)
    with pytest.raises(DiscoveryFetchError) as exc_info:
        adapter.fetch("Wredir", run_id="run-fetch-redir")

    assert exc_info.value.error.error_code == "REDIRECT_DISALLOWED_ORIGIN"
    _assert_no_secret(str(exc_info.value))
