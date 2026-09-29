"""Query planner schema validation."""

from __future__ import annotations

import re
from typing import Any

QUERY_PLANNER_PROMPT_VERSION = "domain_query_planner_v1"


def _word_count(text: str) -> int:
    return len(re.findall(r"[\w\u0080-\uFFFF]+", text))


def validate_planner_payload(plan: dict[str, Any]) -> None:
    if not str(plan.get("domain_original") or "").strip():
        raise ValueError("missing domain_original")
    aliases = plan.get("domain_aliases") or []
    if not isinstance(aliases, list) or len(aliases) > 2:
        raise ValueError("invalid domain_aliases")
    facets = plan.get("technical_facets") or []
    if not isinstance(facets, list) or len(facets) > 6:
        raise ValueError("invalid technical_facets")
    for facet in facets:
        if not isinstance(facet, dict):
            raise ValueError("invalid facet")
        q = str(facet.get("query") or "").strip()
        if not q or _word_count(q) > 5:
            raise ValueError("facet word limit")
        if facet.get("kind") != "TECHNICAL_SEARCH_FACET":
            raise ValueError("invalid facet kind")
