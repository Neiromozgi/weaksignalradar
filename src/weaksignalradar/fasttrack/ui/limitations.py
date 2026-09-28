"""Human-readable limitation lines for Technology Card (DEFECT-UI-002)."""

from __future__ import annotations

from typing import Any


def limitations_lines(
    *,
    d_diagnostics: dict[str, Any] | None,
    features: dict[str, dict[str, Any]] | None,
    source_runs: list[dict[str, Any]] | None,
    coverage: dict[str, Any] | None,
) -> list[str]:
    lines: list[str] = []
    d = d_diagnostics or {}
    if d.get("lineage_count") is not None:
        lines.append(f"Наблюдаемых линий доказательства: {d['lineage_count']}.")
    if d.get("independent_org_count") is not None:
        lines.append(f"Независимых организаций в evidence: {d['independent_org_count']}.")
    if d.get("source_class_count") is not None:
        lines.append(f"Классов источников с наблюдениями: {d['source_class_count']}.")
    unc = d.get("coverage_uncertainty") or []
    if unc:
        lines.append("Неопределённость покрытия: " + ", ".join(str(x) for x in unc) + ".")
    feats = features or {}
    for code in "ABCDE":
        f = feats.get(code) or {}
        avail = f.get("availability")
        if avail and avail not in {"OK"}:
            lines.append(f"Признак {code}: {avail}.")
    cov = coverage or {}
    for key in ("openalex", "cordis", "epo_lod"):
        val = cov.get(key)
        ok_cov = {"FOUND", "CACHE_REUSE", "SNAPSHOT_REPLAY", "SEARCHED_OK"}
        if val and str(val).upper() not in ok_cov:
            lines.append(f"Источник {key}: {val}.")
    for sr in source_runs or []:
        st = sr.get("execution_status")
        if st and str(st).upper() in {"PARTIAL", "SEARCH_ERROR", "RATE_LIMITED", "ERROR"}:
            src = sr.get("source", "source")
            lines.append(f"Компонент {src}: {st}.")
    if not lines:
        lines.append("Существенных ограничений по доступным diagnostic-полям не зафиксировано.")
    return lines
