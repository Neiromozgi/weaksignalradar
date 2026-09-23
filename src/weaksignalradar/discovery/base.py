"""Discovery adapter interface (stage_a_contract.json#search_interface).

Contract:
    search(query, scope, as_of, params, cursor) -> SourceSearchResult
    fetch(document_id) -> SourceDocument + snapshot

``run_id`` is required on every returned record but is not part of the
literal contract snippet's parameter list; the orchestrator that owns a
``SearchRun`` (Stage A-04+) supplies it. For Stage A-03, adapters accept
it as an explicit keyword argument so results are correctly stamped
without silently inventing an orchestration layer that is out of scope.
"""

from __future__ import annotations

from typing import Any, Protocol

from .contracts import SourceDocument, SourceSearchResult


class DiscoveryAdapter(Protocol):
    """Structural interface every Stage A source adapter must implement."""

    def search(
        self,
        query: str,
        scope: dict[str, Any],
        as_of: str | None,
        params: dict[str, Any],
        cursor: str | None,
        *,
        run_id: str,
    ) -> SourceSearchResult: ...

    def fetch(self, document_id: str, *, run_id: str) -> SourceDocument: ...
