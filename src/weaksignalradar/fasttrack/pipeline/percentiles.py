"""Mid-rank percentiles on scorable universe (handoff 11)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PercentileQuality:
    n: int
    flag: str


def percentile_quality(n: int) -> PercentileQuality:
    if n >= 30:
        flag = "NORMAL"
    elif n >= 20:
        flag = "USABLE_WARNING"
    elif n >= 15:
        flag = "UNSTABLE"
    else:
        flag = "TOO_SMALL_FOR_TOP15_UNIVERSE"
    return PercentileQuality(n=n, flag=flag)


def midrank_percentiles(
    values: dict[str, float], *, higher_is_better: bool = True
) -> dict[str, float]:
    """P(x) = 100 * (average_rank(x) - 0.5) / N with tie average ranks."""
    keys = list(values.keys())
    n = len(keys)
    if n == 0:
        return {}
    sorted_keys = sorted(keys, key=lambda k: values[k], reverse=higher_is_better)
    ranks: dict[str, float] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[sorted_keys[j + 1]] == values[sorted_keys[i]]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[sorted_keys[k]] = 100.0 * (avg_rank - 0.5) / n
        i = j + 1
    return ranks


def inverse_percentiles(values: dict[str, float]) -> dict[str, float]:
    """For E: lower raw share → higher percentile."""
    return midrank_percentiles(values, higher_is_better=False)
