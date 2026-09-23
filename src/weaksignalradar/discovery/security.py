"""SEC-001: redaction helpers.

Rule (contracts/stage_a_contract.json#security.SEC-001): neither a fake key
nor a real key/secret may ever appear in logs, URLs, error messages,
exception chains, or saved snapshots.

These helpers are deliberately conservative: they strip known-sensitive
query-string parameter values and any literal secret string that the
caller explicitly tells them about, wherever it appears in free text,
including full ``traceback.format_exception`` output and exception cause
chains.
"""

from __future__ import annotations

import re
import traceback
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTED = "[REDACTED]"

# Query-string parameter names treated as sensitive regardless of source.
SENSITIVE_QUERY_PARAM_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "key",
        "token",
        "access_token",
        "secret",
        "password",
        "auth",
    }
)

_URL_PATTERN = re.compile(r"https?://\S+")


def redact_url(url: str) -> str:
    """Return ``url`` with any sensitive query-parameter values replaced.

    Path, host, and scheme are preserved (they are not secrets); only
    values of known-sensitive parameter names are redacted.
    """
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    redacted_pairs = [
        (name, REDACTED if name.lower() in SENSITIVE_QUERY_PARAM_NAMES else value)
        for name, value in pairs
    ]
    new_query = urlencode(redacted_pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def redact_secrets_in_text(text: str, *secrets: str | None) -> str:
    """Replace every occurrence of any non-empty ``secrets`` value in ``text``.

    Also redacts sensitive query parameters inside any http(s) URL found
    in the text, independent of whether a secret string was supplied.
    """
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, REDACTED)
    redacted = _URL_PATTERN.sub(lambda match: redact_url(match.group(0)), redacted)
    return redacted


def redact_secrets_in_bytes(raw: bytes, *secrets: str | None) -> bytes:
    """Return a copy of ``raw`` with known secrets removed for snapshot storage.

    Decodes as UTF-8 when possible; on decode failure, performs literal
    byte-substring replacement for each secret's UTF-8 encoding so binary
    payloads that echo a key still get scrubbed before disk write.
    """
    active = [s for s in secrets if s]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        scrubbed = raw
        for secret in active:
            scrubbed = scrubbed.replace(secret.encode("utf-8"), REDACTED.encode("utf-8"))
        return scrubbed
    return redact_secrets_in_text(text, *active).encode("utf-8")


def sanitize_exception_message(exc: BaseException, *secrets: str | None) -> str:
    """Build a redacted, loggable short message from an exception.

    Walks ``__cause__`` / ``__context__`` so a nested exception that still
    carries a secret cannot leak via ``str(exc)`` alone.
    """
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(str(current))
        current = current.__cause__ or (
            current.__context__ if not current.__suppress_context__ else None
        )
    return redact_secrets_in_text(" | ".join(parts), *secrets)


def format_exception_redacted(exc: BaseException, *secrets: str | None) -> str:
    """Return ``traceback.format_exception`` output with secrets removed.

    This is the SEC-001 boundary check for full formatted exception dumps,
    including cause/context frames that ``str(exc)`` would miss.
    """
    formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return redact_secrets_in_text(formatted, *secrets)
