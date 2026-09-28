"""Feature calculators A–E (handoff 10)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..config.scoring import B_EPS, C_FACET_WEIGHTS
from ..embedding.backend import EmbeddingBackend, cosine_similarity, encode_single
from ..llm.base import TechnicalSignature
from ..preprocessing.e5 import FACET_ORDER, facet_query


@dataclass(slots=True)
class YearStat:
    year: int
    candidate_doc_count: int
    domain_doc_count: int

    @property
    def share(self) -> float:
        if self.domain_doc_count <= 0:
            return 0.0
        return self.candidate_doc_count / self.domain_doc_count


def compute_a_raw(yearly: list[YearStat]) -> float | None:
    """Poisson log-link trend; returns exp(beta_year) or None if insufficient."""
    if len(yearly) < 3:
        return None
    years = [y.year for y in yearly]
    counts = [y.candidate_doc_count for y in yearly]
    offsets = [math.log(max(y.domain_doc_count, 1)) for y in yearly]
    # Simple OLS on log(count) ~ year + offset via centered year
    mean_y = sum(years) / len(years)
    xs = [y - mean_y for y in years]
    ys = [math.log(c + 0.5) - off for c, off in zip(counts, offsets, strict=True)]
    denom = sum(x * x for x in xs)
    if denom <= 0:
        return None
    beta = sum(x * y for x, y in zip(xs, ys, strict=True)) / denom
    return math.exp(beta)


def compute_b_raw(yearly: list[YearStat]) -> float | None:
    if len(yearly) < 5:
        return None
    shares = [y.share for y in sorted(yearly, key=lambda s: s.year)]
    t = len(shares) - 1
    g_recent = (math.log(shares[t] + B_EPS) - math.log(shares[t - 2] + B_EPS)) / 2
    g_prev = (math.log(shares[t - 2] + B_EPS) - math.log(shares[t - 4] + B_EPS)) / 2
    return g_recent - g_prev


def compute_c_raw(
    signature: TechnicalSignature,
    historical: list[TechnicalSignature],
    backend: EmbeddingBackend | None,
) -> float | None:
    if backend is None:
        return None
    facets = {
        "object_class": signature.object_class,
        "function": signature.function,
        "mechanism": signature.mechanism,
        "architecture_or_process": signature.architecture_or_process,
        "key_technical_property": signature.key_technical_property,
    }
    cand_vecs: dict[str, list[float]] = {}
    for key in FACET_ORDER:
        text = facet_query(facets.get(key))
        vec = encode_single(backend, text)
        if vec is not None:
            cand_vecs[key] = vec
    if not cand_vecs:
        return None
    sim_max = 0.0
    for hist in historical:
        h_facets = {
            "object_class": hist.object_class,
            "function": hist.function,
            "mechanism": hist.mechanism,
            "architecture_or_process": hist.architecture_or_process,
            "key_technical_property": hist.key_technical_property,
        }
        sim = 0.0
        weight_sum = 0.0
        for key in FACET_ORDER:
            if key not in cand_vecs:
                continue
            ht = facet_query(h_facets.get(key))
            hvec = encode_single(backend, ht)
            if hvec is None:
                continue
            w = C_FACET_WEIGHTS[key]
            sim += w * cosine_similarity(cand_vecs[key], hvec)
            weight_sum += w
        if weight_sum > 0:
            sim /= weight_sum
            sim_max = max(sim_max, sim)
    return 100.0 * (1.0 - sim_max)


def compute_d_raw(
    *,
    lineage_count: int,
    independent_org_count: int,
    source_class_count: int,
    reference_recurrence: float,
) -> float:
    l_n = min(math.log(1 + lineage_count) / math.log(6), 1.0)
    o_n = min(math.log(1 + independent_org_count) / math.log(6), 1.0)
    s_n = source_class_count / 3.0
    r_n = max(0.0, min(1.0, reference_recurrence))
    return 100.0 * (0.35 * l_n + 0.30 * o_n + 0.25 * s_n + 0.10 * r_n)


def compute_e_percentile_input(share_current: float) -> float:
    return share_current


def mann_kendall_q(values: list[float]) -> float | None:
    """One-sided Mann–Kendall p-value (normal approx); None if too short."""
    n = len(values)
    if n < 4:
        return None
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += math.copysign(1, values[j] - values[i])
    var_s = n * (n - 1) * (2 * n + 5) / 18
    if var_s <= 0:
        return None
    if s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0
    # one-sided upper tail for positive trend
    from math import erf, sqrt

    p = 0.5 * (1 - erf(z / sqrt(2)))
    return p
