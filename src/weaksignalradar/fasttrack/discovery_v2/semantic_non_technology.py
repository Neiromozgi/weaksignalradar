"""Domain-independent non-technology semantic classes (bilingual phrases)."""

from __future__ import annotations

from .text_norm import normalize_text

NON_TECHNOLOGY_PHRASES = (
    "conceptual model",
    "relationship model",
    "market model",
    "development model",
    "economic framework",
    "assessment method",
    "general methodology",
    "generalized algorithm",
    "algorithm for assessing",
    "conceptual adaptation",
    "systemic approach",
    "marketing theory",
    "методика",
    "методический",
    "обобщенный алгоритм",
    "концептуальной адаптации",
    "business model",
    "conceptual framework",
    "theoretical framework",
    "analytical framework",
    "digital transformation",
    "концептуальная модель",
    "модель отношений",
    "рыночная модель",
    "экономическая модель",
    "общая методология",
    "цифровая трансформация",
)

_ENGINEERING_MARKERS = (
    "algorithm",
    "protocol",
    "architecture",
    "encryption",
    "compiler",
    "interferometer",
    "waveguide",
    "photonic",
    "microcontroller",
    "sensor",
    "antenna",
    "blockchain",
    "consensus",
    "neural network",
    "алгоритм",
    "протокол",
    "архитектура",
    "шифрование",
    "микроконтроллер",
)


def matches_non_technology_semantic(text: str) -> bool:
    norm = normalize_text(text)
    if not norm:
        return False
    for phrase in NON_TECHNOLOGY_PHRASES:
        if phrase in norm:
            return True
    for token in ("regulation", "ecosystem", "регулирование", "экосистема"):
        if f" {token} " in f" {norm} ":
            return True
    return False


def has_concrete_engineering_marker(text: str) -> bool:
    norm = normalize_text(text)
    return any(marker in norm for marker in _ENGINEERING_MARKERS)


def reject_technology_mechanism_label(*, mechanism: str, evidence_span: str) -> bool:
    """True if TECHNOLOGY_MECHANISM label must not stand (non-tech semantic)."""
    combined = f"{mechanism} {evidence_span}"
    norm = normalize_text(combined)
    if matches_non_technology_semantic(combined):
        return not has_concrete_engineering_marker(combined)
    for phrase in (
        "generalized algorithm",
        "algorithm for assessing",
        "обобщенный алгоритм",
        "оценки кандидат",
        "conceptual adaptation",
        "концептуальной адаптации",
        "systemic approach",
        "системного подхода",
        "marketing",
        "маркетинг",
        "алгоритмическую обработку",
        "algorithmic processing",
    ):
        if phrase in norm:
            return True
    return False
