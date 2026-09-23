"""SEC-001: redaction helpers.

Rule (contracts/stage_a_contract.json#security.SEC-001): neither a fake key
nor a real key/secret may ever appear in logs, URLs, error messages,
exception chains, or saved snapshots.

JSON response bodies MUST be redacted structurally after a successful
``json.loads`` (see ``prepare_json_snapshot``). Blind URL regex over the
entire JSON text is forbidden: PRECHECK against OpenAlex showed that
``https?://\\S+`` swallowed closing quotes/commas and re-encoded them as
``%22``/``%2C``, producing INVALID_JSON. That corrupted first PRECHECK
snapshot is diagnostic evidence of the failure mode only — not a valid
search result or reusable source artifact.
"""

from __future__ import annotations

import json
import re
import traceback
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTED = "[REDACTED]"

# Query-string / JSON object keys treated as sensitive regardless of source.
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

# Free-text URL matcher for logs/exceptions only. Stops before whitespace,
# quotes, and angle brackets so JSON delimiters are never captured.
_URL_PATTERN = re.compile(r"https?://[^\s\"'<>\\]+")
_URL_TRAILING_PUNCT = ".,;:!?)]}"


def redact_url(url: str) -> str:
    """Return ``url`` with any sensitive query-parameter values replaced.

    Path, host, and scheme are preserved (they are not secrets); only
    values of known-sensitive parameter names are redacted. The input must
    already be a single URL string (not a JSON document fragment).
    """
    cleaned = url.rstrip(_URL_TRAILING_PUNCT)
    parts = urlsplit(cleaned)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    redacted_pairs = [
        (name, REDACTED if name.lower() in SENSITIVE_QUERY_PARAM_NAMES else value)
        for name, value in pairs
    ]
    new_query = urlencode(redacted_pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def redact_secrets_in_text(text: str, *secrets: str | None) -> str:
    """Replace secrets in free text (logs, exception dumps).

    Literal secret strings are removed first. URL query redaction then runs
    only on bounded URL matches — never on a whole JSON document. Use
    ``prepare_json_snapshot`` / ``redact_secrets_in_json`` for JSON bodies.
    """
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, REDACTED)

    def _replace_url(match: re.Match[str]) -> str:
        return redact_url(match.group(0))

    return _URL_PATTERN.sub(_replace_url, redacted)


def redact_secrets_in_json(value: Any, *secrets: str | None) -> Any:
    """Return a deep copy of ``value`` with secrets removed structurally.

    - Object keys in ``SENSITIVE_QUERY_PARAM_NAMES`` → value becomes REDACTED.
    - String values: literal secret substrings replaced; if the whole string
      looks like an http(s) URL, sensitive query params are redacted via
      ``redact_url`` without touching surrounding JSON syntax.
    - Lists/dicts are walked recursively. Non-string scalars are unchanged.
    """
    active = [s for s in secrets if s]

    def _walk(node: Any, parent_key: str | None = None) -> Any:
        if parent_key is not None and parent_key.lower() in SENSITIVE_QUERY_PARAM_NAMES:
            return REDACTED
        if isinstance(node, dict):
            return {k: _walk(v, parent_key=str(k)) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(item, parent_key=None) for item in node]
        if isinstance(node, str):
            text = node
            for secret in active:
                text = text.replace(secret, REDACTED)
            stripped = text.strip()
            if stripped.lower().startswith(("http://", "https://")):
                leading = text[: len(text) - len(text.lstrip())]
                trailing = text[len(text.rstrip()) :]
                text = leading + redact_url(stripped) + trailing
                for secret in active:
                    text = text.replace(secret, REDACTED)
            return text
        return node

    return _walk(value)


def prepare_json_snapshot(raw: bytes, *secrets: str | None) -> tuple[bytes, Any]:
    """Parse JSON, redact structurally, return safe bytes + redacted object.

    Does not write to disk. Raises ``UnicodeDecodeError`` or
    ``json.JSONDecodeError`` before any snapshot is produced so a damaged
    or unsafe body is never persisted as a successful capture.
    """
    text = raw.decode("utf-8")
    payload = json.loads(text)
    redacted_payload = redact_secrets_in_json(payload, *secrets)
    safe_bytes = json.dumps(redacted_payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    for secret in secrets:
        if secret and secret.encode("utf-8") in safe_bytes:
            # Defensive: structural walk must have removed every secret.
            raise ValueError("SEC-001: secret still present after JSON redaction")
    return safe_bytes, redacted_payload


def redact_secrets_in_bytes(raw: bytes, *secrets: str | None) -> bytes:
    """Scrub secrets from bytes for non-adapter/diagnostic use.

    Prefer ``prepare_json_snapshot`` for Discovery responses. If ``raw`` is
    valid UTF-8 JSON, this delegates to structural redaction. Otherwise only
    literal secret byte-replacement is applied — no URL regex over the body.
    """
    active = [s for s in secrets if s]
    try:
        safe_bytes, _payload = prepare_json_snapshot(raw, *active)
        return safe_bytes
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        scrubbed = raw
        for secret in active:
            scrubbed = scrubbed.replace(secret.encode("utf-8"), REDACTED.encode("utf-8"))
        return scrubbed


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
