"""SEC-001 redaction helper unit tests."""

from __future__ import annotations

import json
import traceback

from weaksignalradar.discovery.security import (
    REDACTED,
    format_exception_redacted,
    prepare_json_snapshot,
    redact_secrets_in_bytes,
    redact_secrets_in_json,
    redact_secrets_in_text,
    redact_url,
    sanitize_exception_message,
)


def test_redact_url_removes_sensitive_query_param_values() -> None:
    url = "https://api.openalex.org/works?search=lidar&api_key=SUPER-SECRET-123&mailto=a@b.com"
    redacted = redact_url(url)

    assert "SUPER-SECRET-123" not in redacted
    assert "api_key=%5BREDACTED%5D" in redacted or "api_key=[REDACTED]" in redacted
    assert "search=lidar" in redacted
    assert "mailto=a%40b.com" in redacted or "mailto=a@b.com" in redacted


def test_redact_url_preserves_urls_without_sensitive_params() -> None:
    url = "https://api.openalex.org/works?search=lidar"
    assert redact_url(url) == url


def test_redact_secrets_in_text_removes_literal_secret() -> None:
    text = (
        "auth failed for token FAKE-KEY-abc123 while calling "
        "https://api.openalex.org/works?api_key=FAKE-KEY-abc123"
    )
    redacted = redact_secrets_in_text(text, "FAKE-KEY-abc123")

    assert "FAKE-KEY-abc123" not in redacted


def test_redact_secrets_in_text_handles_none_and_empty_secrets() -> None:
    text = "no secrets here"
    assert redact_secrets_in_text(text, None, "") == text


def test_free_text_url_regex_does_not_consume_json_delimiters() -> None:
    """Regression for PRECHECK: \\S+ must not swallow quotes/commas after URLs."""
    fragment = '{"id":"https://openalex.org/W1","x":1}'
    # Free-text helper may touch URLs but must not encode " or , into the URL.
    redacted = redact_secrets_in_text(fragment)
    assert "%22" not in redacted
    assert "%2C" not in redacted
    assert '"https://openalex.org/W1"' in redacted


def test_sanitize_exception_message_redacts_secret_from_exception_str() -> None:
    exc = ValueError("failed calling https://api.openalex.org/works?api_key=FAKE-KEY-999")
    message = sanitize_exception_message(exc, "FAKE-KEY-999")

    assert "FAKE-KEY-999" not in message


def test_sanitize_exception_message_walks_cause_chain() -> None:
    secret = "FAKE-KEY-CAUSE-CHAIN"
    root = ValueError(f"inner has {secret}")
    outer = RuntimeError("outer")
    outer.__cause__ = root
    message = sanitize_exception_message(outer, secret)
    assert secret not in message


def test_format_exception_redacted_covers_full_traceback_and_cause() -> None:
    secret = "FAKE-KEY-TRACEBACK-LEAK"
    try:
        try:
            raise ValueError(f"cause carries {secret}")
        except ValueError as cause:
            raise RuntimeError("wrapper") from cause
    except RuntimeError as exc:
        raw = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        assert secret in raw
        redacted = format_exception_redacted(exc, secret)
        assert secret not in redacted


def test_prepare_json_snapshot_preserves_urls_before_quotes_and_commas() -> None:
    raw = b'{"id":"https://openalex.org/W1","doi":"https://doi.org/10.1/x","n":1}'
    safe, payload = prepare_json_snapshot(raw)
    assert json.loads(safe) == payload
    assert payload["id"] == "https://openalex.org/W1"
    assert "%22" not in safe.decode("utf-8")
    assert "%2C" not in safe.decode("utf-8")


def test_prepare_json_snapshot_nested_unicode_and_escapes() -> None:
    payload = {
        "title": 'Кавычки "внутри" и emoji 🧪',
        "nested": {"note": "line\\nnext", "list": ["α", {"u": "https://openalex.org/W9"}]},
    }
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    safe, redacted = prepare_json_snapshot(raw)
    roundtrip = json.loads(safe)
    assert roundtrip["title"] == payload["title"]
    assert roundtrip["nested"]["list"][1]["u"] == "https://openalex.org/W9"
    assert redacted == roundtrip


def test_prepare_json_snapshot_redacts_secret_in_field_and_url() -> None:
    secret = "FAKE-KEY-JSON-STRUCT"
    payload = {
        "note": f"token {secret}",
        "api_key": secret,
        "url": f"https://api.openalex.org/works?api_key={secret}&q=1",
    }
    raw = json.dumps(payload).encode("utf-8")
    safe, redacted = prepare_json_snapshot(raw, secret)
    text = safe.decode("utf-8")
    assert secret not in text
    assert redacted["api_key"] == REDACTED
    assert secret not in redacted["note"]
    assert secret not in redacted["url"]
    assert "api_key=" in redacted["url"]


def test_redact_secrets_in_json_sensitive_key_without_secret_arg() -> None:
    data = {"token": "whatever", "ok": True}
    out = redact_secrets_in_json(data)
    assert out["token"] == REDACTED
    assert out["ok"] is True


def test_redact_secrets_in_bytes_uses_structural_path_for_json() -> None:
    secret = "FAKE-KEY-BYTES"
    raw = json.dumps({"id": "https://openalex.org/W1", "echo": secret}).encode()
    scrubbed = redact_secrets_in_bytes(raw, secret)
    assert secret.encode() not in scrubbed
    parsed = json.loads(scrubbed)
    assert parsed["id"] == "https://openalex.org/W1"
    assert secret not in parsed["echo"]
