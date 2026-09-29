"""Normalization for span grounding checks."""

from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    lowered = text.lower().replace("ё", "е")
    lowered = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
    return re.sub(r"\s+", " ", lowered).strip()


def significant_tokens(text: str, *, min_len: int = 4) -> list[str]:
    norm = normalize_text(text)
    return [t for t in norm.split() if len(t) >= min_len]


def span_in_source(span: str, title: str, abstract: str | None) -> bool:
    hay = normalize_text(f"{title} {abstract or ''}")
    needle = normalize_text(span)
    if not needle:
        return False
    return needle in hay
