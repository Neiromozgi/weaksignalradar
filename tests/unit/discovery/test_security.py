"""SEC-001 redaction helper unit tests."""

from weaksignalradar.discovery.security import (
    redact_secrets_in_text,
    redact_url,
    sanitize_exception_message,
)


def test_redact_url_removes_sensitive_query_param_values() -> None:
    url = "https://api.openalex.org/works?search=lidar&api_key=SUPER-SECRET-123&mailto=a@b.com"
    redacted = redact_url(url)

    assert "SUPER-SECRET-123" not in redacted
    assert "api_key=%5BREDACTED%5D" in redacted or "api_key=[REDACTED]" in redacted
    # non-sensitive params are preserved
    assert "search=lidar" in redacted
    assert "mailto=a%40b.com" in redacted or "mailto=a@b.com" in redacted


def test_redact_url_preserves_urls_without_sensitive_params() -> None:
    url = "https://api.openalex.org/works?search=lidar"
    assert redact_url(url) == url


def test_redact_secrets_in_text_removes_literal_secret() -> None:
    text = "auth failed for token FAKE-KEY-abc123 while calling https://api.openalex.org/works?api_key=FAKE-KEY-abc123"
    redacted = redact_secrets_in_text(text, "FAKE-KEY-abc123")

    assert "FAKE-KEY-abc123" not in redacted


def test_redact_secrets_in_text_handles_none_and_empty_secrets() -> None:
    text = "no secrets here"
    assert redact_secrets_in_text(text, None, "") == text


def test_sanitize_exception_message_redacts_secret_from_exception_str() -> None:
    exc = ValueError("failed calling https://api.openalex.org/works?api_key=FAKE-KEY-999")
    message = sanitize_exception_message(exc, "FAKE-KEY-999")

    assert "FAKE-KEY-999" not in message
