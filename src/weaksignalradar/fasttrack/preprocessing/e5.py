"""E5 prefix and text construction (addendum 01)."""

from __future__ import annotations

FACET_ORDER = (
    "object_class",
    "function",
    "mechanism",
    "architecture_or_process",
    "key_technical_property",
)

MISSING_FACET = "UNKNOWN"


def prefix_query(text: str) -> str:
    return f"query: {text.strip()}"


def prefix_passage(text: str) -> str:
    return f"passage: {text.strip()}"


def passage_from_document(title: str, abstract_or_evidence: str | None) -> str | None:
    title = (title or "").strip()
    body = (abstract_or_evidence or "").strip()
    if not title and not body:
        return None
    if body:
        return prefix_passage(f"{title} {body}".strip())
    return prefix_passage(title)


def facet_query(facet_value: str | None) -> str | None:
    if facet_value is None:
        return None
    val = facet_value.strip()
    if not val or val.upper() == MISSING_FACET:
        return None
    return prefix_query(val)


def canonical_technical_signature(facets: dict[str, str | None]) -> str | None:
    parts: list[str] = []
    for key in FACET_ORDER:
        raw = facets.get(key)
        if raw is None or not str(raw).strip() or str(raw).strip().upper() == MISSING_FACET:
            val = MISSING_FACET
        else:
            val = str(raw).strip()
        parts.append(f"{key}: {val}")
    if all(p.endswith(f": {MISSING_FACET}") for p in parts):
        return None
    return prefix_query("\n".join(parts))
