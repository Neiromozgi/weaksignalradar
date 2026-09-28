"""Minimal SPARQL client for public LOD endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class SparqlResult:
    bindings: list[dict[str, Any]]
    ok: bool
    error: str | None = None


def run_sparql(
    endpoint: str,
    query: str,
    *,
    timeout_s: float = 45.0,
    client: httpx.Client | None = None,
) -> SparqlResult:
    http = client or httpx.Client(timeout=timeout_s)
    try:
        resp = http.post(
            endpoint,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
    except httpx.TimeoutException:
        return SparqlResult(bindings=[], ok=False, error="timeout")
    except httpx.HTTPError as exc:
        return SparqlResult(bindings=[], ok=False, error=type(exc).__name__)
    if resp.status_code >= 400:
        return SparqlResult(bindings=[], ok=False, error=f"http_{resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        return SparqlResult(bindings=[], ok=False, error="invalid_json")
    bindings = data.get("results", {}).get("bindings", [])
    return SparqlResult(bindings=list(bindings), ok=True)


def binding_value(row: dict[str, Any], key: str) -> str | None:
    cell = row.get(key)
    if not cell:
        return None
    return cell.get("value")
