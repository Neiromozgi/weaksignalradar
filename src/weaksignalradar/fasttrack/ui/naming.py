"""Display-only technology naming (addendum v1.0.4 §12). Does not affect candidate_id or scoring."""

from __future__ import annotations

import re

from ..domain.run_state import CandidateRecord

_ACRONYM = re.compile(r"^[A-Z0-9]{2,12}$")


def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())


def technology_display_names(c: CandidateRecord) -> dict[str, str | list[str]]:
    original = (c.name_en or c.canonical_name or "").strip()
    ru = (c.name_ru or "").strip()
    if not ru:
        ru = original
    label = ru
    if original and _norm(ru) != _norm(original) and not _ACRONYM.match(original):
        label = f"{ru} ({original})"
    elif original and _ACRONYM.match(original) and ru and _norm(ru) != _norm(original):
        label = f"{ru} ({original})"
    return {
        "name_ru": ru,
        "name_original": original or ru,
        "display_label": label,
        "aliases": list(c.aliases or []),
    }
