"""Domain-agnostic macro/policy vocabulary (bilingual)."""

from __future__ import annotations

from .text_norm import normalize_text

MACRO_POLICY_TOKENS = frozenset(
    {
        "market",
        "development",
        "regulation",
        "digitalization",
        "economy",
        "ecosystem",
        "transformation",
        "policy",
        "sector",
        "innovation",
        "financial",
        "industry",
        "рынок",
        "развитие",
        "регулирование",
        "цифровизация",
        "экономика",
        "экосистема",
        "трансформация",
        "политика",
        "отрасль",
        "инновации",
        "финансовый",
    }
)


def is_generic_macro_mechanism(mechanism: str) -> bool:
    tokens = normalize_text(mechanism).split()
    if not tokens:
        return True
    if len(tokens) == 1 and tokens[0] in MACRO_POLICY_TOKENS:
        return True
    if all(t in MACRO_POLICY_TOKENS for t in tokens):
        return True
    return False
