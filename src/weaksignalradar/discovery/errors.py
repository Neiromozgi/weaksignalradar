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
    The exception deliberately does not retain ``__cause__`` / ``__context__``
    from upstream HTTP/library failures: those chains may echo secrets, and
    SEC-001 requires redaction of the full formatted exception dump.
    """

    def __init__(self, error: SearchError) -> None:
        super().__init__(error.message)
        self.error = error
        # Prevent accidental leakage via traceback.format_exception cause chains.
        self.__cause__ = None
        self.__context__ = None
        self.__suppress_context__ = True
