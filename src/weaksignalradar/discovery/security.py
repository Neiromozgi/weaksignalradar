"""SEC-001: redaction helpers.

Rule (contracts/stage_a_contract.json#security.SEC-001): neither a fake key
nor a real key/secret may ever appear in logs, URLs, error messages,
exception chains, or saved snapshots.

These helpers are deliberately conservative: they strip known-sensitive
query-string parameter values and any literal secret string that the
caller explicitly tells them about, wherever it appears in free text.
"""

from __future__ import annotations

import re
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


def sanitize_exception_message(exc: BaseException, *secrets: str | None) -> str:
    """Build a redacted, loggable message from an exception.

    Never returns the raw ``repr()``/exception chain; only a short,
    sanitized ``str(exc)`` with secrets and sensitive URL params removed.
    """
    return redact_secrets_in_text(str(exc), *secrets)
