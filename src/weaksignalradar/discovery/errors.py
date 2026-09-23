"""Discovery-adapter exceptions.

These carry an already-redacted ``SearchError`` (see ``security.py`` for
how the message is sanitized) so callers never need to re-inspect raw
exception chains that might contain secrets.
"""

from __future__ import annotations

from .contracts import SearchError


class DisallowedOriginError(ValueError):
    """Raised when a configured base URL is not on the HTTPS allowlist."""


class DiscoveryFetchError(RuntimeError):
    """Raised by ``fetch()`` when a document could not be retrieved.

    ``error`` is a redacted, structured ``SearchError`` safe to log.
    """

    def __init__(self, error: SearchError) -> None:
        super().__init__(error.message)
        self.error = error
