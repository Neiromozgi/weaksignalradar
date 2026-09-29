"""FastTrack analysis pipeline orchestrator."""

from __future__ import annotations

import hashlib
import math
import uuid
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from weaksignalradar.observability.event_log import emit_event

from ..config.embedding_profile import E5_SMALL_V1, embedding_provenance_fields
from ..config.scoring import ABCDE_V1, FEATURE_CONTRACT_VERSION
from ..corpus.snapshot_loader import load_openalex_works
from ..corpus.snapshot_registry import load_snapshot_documents, register_live_snapshot
from ..db.repository import RunRepository
from ..domain.run_state import AnalysisRunState, CandidateRecord
from ..embedding.backend import (
    EmbeddingBackend,
    embedding_runtime_status,
    get_embedding_backend,
)
from ..llm.base import TechnicalSignature, get_llm_adapter, llm_runtime_status
from ..llm.profile import LLM_MODEL, LLM_PROFILE_ID
from ..persistence_guard import is_persistence_failure
from ..sources.budget import BudgetTracker
from ..sources.contract import CoverageState, NormalizedSourceDocument
from ..sources.cordis import CordisAdapter
from ..sources.epo_lod import EpoLodAdapter
from ..sources.openalex_ft import OpenAlexFastTrackAdapter
from .candidates import discover_candidates
from .features import (
    YearStat,
    compute_a_raw,
    compute_b_raw,
    compute_c_raw,
    compute_d_raw,
    compute_e_percentile_input,
    mann_kendall_q,
)
from .llm_diagnostics import LLMDiagnostics
from .percentiles import inverse_percentiles, midrank_percentiles, percentile_quality


def start_analysis(
    *,
    query: str,
    data_mode: str,
    score_profile_id: str,
    snapshot_id: str | None,
    domain_id: str = "default",
    repository: RunRepository,
) -> AnalysisRunState:
    repo = repository
    run_id = f"run_{uuid.uuid4().hex[:16]}"
    now = datetime.now(UTC).isoformat()
    state = AnalysisRunState(
        run_id=run_id,
        normalized_query=query.strip(),
        domain_id=domain_id,
        data_mode=data_mode,  # type: ignore[arg-type]
        snapshot_id=snapshot_id,
        status="RUNNING",
        score_profile_id=score_profile_id,
        feature_contract_version=FEATURE_CONTRACT_VERSION,
        candidate_universe_version="cu_v1",
        embedding_model_id=E5_SMALL_V1.embedding_model_id,
        llm_model_id=LLM_MODEL if llm_runtime_status() == "CONFIGURED" else None,
        coverage_summary={},
        started_at=now,
        provenance={
            **embedding_provenance_fields(),
            "discovery_method": None,
            "llm_profile_id": LLM_PROFILE_ID,
            "llm_status": llm_runtime_status(),
        },
    )
    try:
        _execute_pipeline(state, repo)
        state.status = "COMPLETED"
    except Exception as exc:
        if is_persistence_failure(exc):
            raise
        state.status = "FAILED"
        state.coverage_summary = {"error": type(exc).__name__, "message": str(exc)[:500]}
    state.finished_at = datetime.now(UTC).isoformat()
    try:
        repo.save(state)
    except Exception as exc:
        if is_persistence_failure(exc):
            raise
        raise
    return state


def refresh_corpus(
    *,
    query: str,
    engine,
    run_id: str | None = None,
) -> dict[str, Any]:
    """LIVE refresh → bounded retrieval → new immutable snapshot registration."""
    from sqlalchemy.engine import Engine

    if not isinstance(engine, Engine):
        raise TypeError("engine required for snapshot registration")
    rid = run_id or f"refresh_{uuid.uuid4().hex[:12]}"
    budgets = BudgetTracker()
    oa = OpenAlexFastTrackAdapter()
    t0 = datetime.now(UTC).isoformat()
    oa_result = oa.search_live_bounded(
        query,
        run_id=rid,
        max_calls=budgets.for_source("openalex").remaining,
    )
    budgets.for_source("openalex").consume(oa_result.calls_used)
    cordis = CordisAdapter().search(query, budgets.for_source("cordis").remaining)
    budgets.for_source("cordis").consume(cordis.calls_used)
    epo = EpoLodAdapter().search(query, budgets.for_source("epo_lod").remaining)
    budgets.for_source("epo_lod").consume(epo.calls_used)
    t1 = datetime.now(UTC).isoformat()
    docs = _dedupe_documents(
        list(oa_result.documents) + list(cordis.documents) + list(epo.documents)
    )
    source_coverage = {
        "openalex": oa_result.coverage_state.value,
        "cordis": cordis.coverage_state.value,
        "epo_lod": epo.coverage_state.value,
        "openalex_calls": oa_result.calls_used,
        "started_at": t0,
        "completed_at": t1,
    }
    out: dict[str, Any] = {
        "refresh_id": rid,
        "openalex": oa_result.coverage_state.value,
        "documents_added": len(docs),
        "cordis": cordis.coverage_state.value,
        "epo_lod": epo.coverage_state.value,
        "budgets": {k: v.calls_used for k, v in budgets.budgets.items()},
    }
    if not docs:
        out["snapshot"] = None
        out["message"] = "no_documents_to_snapshot"
        return out
    snap = register_live_snapshot(
        engine=engine,
        query=query.strip(),
        documents=docs,
        source_coverage=source_coverage,
        refresh_id=rid,
    )
    out["snapshot"] = snap
    out["snapshot_id"] = snap["snapshot_id"]
    return out


def _execute_pipeline(state: AnalysisRunState, repo: RunRepository) -> None:
    documents, coverage, source_runs = _acquire_documents(state)
    state.documents = documents
    state.coverage_summary = coverage
    state.source_runs = source_runs

    llm = get_llm_adapter()
    backend: EmbeddingBackend | None
    try:
        backend = get_embedding_backend(allow_none=True)
        emb_label = backend.backend_name if backend else embedding_runtime_status()
    except Exception:
        backend = None
        emb_label = "EMBEDDING_UNAVAILABLE"

    cand_dicts, method, cluster_prov = discover_candidates(
        documents, domain_id=state.domain_id, backend=backend
    )
    state.provenance["discovery_method"] = method
    state.provenance.update(cluster_prov)
    if cluster_prov.get("discovery_status") == "EMBEDDING_UNAVAILABLE":
        state.provenance["discovery_status"] = "EMBEDDING_UNAVAILABLE"
    state.provenance["embedding_backend"] = emb_label
    state.provenance["embedding_runtime_status"] = embedding_runtime_status()
    if backend is None:
        emit_event(
            "EMBEDDING_UNAVAILABLE",
            run_id=state.run_id,
            mode=state.data_mode,
            component="embedding",
        )
    else:
        emit_event(
            "EMBEDDING_AVAILABLE",
            run_id=state.run_id,
            mode=state.data_mode,
            component="embedding",
        )
    signatures: list[TechnicalSignature] = []
    llm_diag = LLMDiagnostics()

    candidates: list[CandidateRecord] = []
    doc_by_id = {d.source_document_id: d for d in documents}
    for cd in cand_dicts:
        llm_diag.begin_candidate()
        evidence = []
        for did in cd["document_ids"]:
            doc = doc_by_id.get(did)
            if doc and doc.abstract:
                evidence.append(doc.abstract)
            elif doc:
                evidence.append(doc.title)
        evidence_hash = hashlib.sha256("\n".join(evidence).encode("utf-8")).hexdigest()
        sig = repo.get_extraction_replay(state.snapshot_id, cd["candidate_id"], evidence_hash)
        if sig is None:
            llm_diag.begin_provider_call()
            sig = llm.extract_signature(
                candidate_name=cd["canonical_name"], evidence_texts=evidence
            )
            llm_diag.finish_provider_call(sig)
            if sig.validation_status == "PASSED":
                repo.save_extraction(
                    run_id=state.run_id,
                    candidate_id=cd["candidate_id"],
                    evidence_hash=evidence_hash,
                    signature=sig,
                    extraction_payload={"signature": _sig_payload(sig)},
                    provenance={"snapshot_id": state.snapshot_id, "mode": state.data_mode},
                )
        else:
            llm_diag.mark_replay(sig)
        signatures.append(sig)
        yearly = _build_yearly_stats(cd, documents)
        candidates.append(
            CandidateRecord(
                candidate_id=cd["candidate_id"],
                canonical_name=cd["canonical_name"],
                name_ru=cd.get("name_ru"),
                name_en=cd.get("name_en"),
                aliases=cd.get("aliases") or [],
                state="DISCOVERED",
                document_ids=cd["document_ids"],
                first_observed_year=cd.get("first_observed_year"),
                document_count=cd["document_count"],
                organization_count=cd["organization_count"],
                source_class_count=cd["source_class_count"],
                signature=sig,
                yearly_stats=[asdict(y) for y in yearly],
            )
        )

    _compute_features(
        candidates,
        yearly_map={c.candidate_id: _parse_yearly(c) for c in candidates},
        backend=backend,
        documents=documents,
    )
    _apply_sufficiency_and_filters(candidates, documents)
    _score_and_rank(candidates)
    state.candidates = candidates
    state.registries = _build_registries(candidates)
    state.provenance["llm_diagnostics"] = llm_diag.as_dict()
    emit_event(
        "LLM_EXTRACTION_SUMMARY",
        run_id=state.run_id,
        mode=state.data_mode,
        component="llm",
        extra=llm_diag.as_dict(),
    )


def _sig_payload(sig: TechnicalSignature) -> dict[str, Any]:
    return {
        "object_class": sig.object_class,
        "function": sig.function,
        "mechanism": sig.mechanism,
        "architecture_or_process": sig.architecture_or_process,
        "key_technical_property": sig.key_technical_property,
        "extraction_status": sig.extraction_status,
        "evidence_span_refs": sig.evidence_span_refs,
        "llm_model_id": sig.llm_model_id,
        "prompt_version": sig.prompt_version,
        "validation_status": sig.validation_status,
        "llm_profile_id": sig.llm_profile_id,
    }


def _source_run(
    *,
    source: str,
    execution_status: str,
    external_calls: int,
    records_received: int,
    cap_reached: bool = False,
    error: str | None = None,
    started_at: str,
    completed_at: str | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "execution_status": execution_status,
        "external_calls": external_calls,
        "records_received": records_received,
        "cap_reached": cap_reached,
        "error": error,
        "started_at": started_at,
        "completed_at": completed_at,
    }


def _acquire_documents(
    state: AnalysisRunState,
) -> tuple[list[NormalizedSourceDocument], dict[str, Any], list[dict[str, Any]]]:
    mode = state.data_mode
    coverage: dict[str, Any] = {"data_mode": mode}
    source_runs: list[dict[str, Any]] = []
    oa = OpenAlexFastTrackAdapter()
    now = datetime.now(UTC).isoformat()
    if mode == "SNAPSHOT":
        sid = state.snapshot_id or "ft_bench_v1"
        state.snapshot_id = sid
        stored = load_snapshot_documents(sid)
        if stored is not None:
            coverage["openalex"] = "SNAPSHOT_REPLAY"
            coverage["snapshot_id"] = sid
            coverage["external_calls"] = 0
            source_runs.append(
                _source_run(
                    source="openalex",
                    execution_status="SNAPSHOT_REPLAY",
                    external_calls=0,
                    records_received=len(stored),
                    started_at=now,
                    completed_at=now,
                )
            )
            return stored, coverage, source_runs
        works = load_openalex_works(sid)
        batch = oa.search_from_fixture(works, snapshot_id=sid)
        coverage["openalex"] = batch.coverage_state.value
        coverage["snapshot_id"] = sid
        source_runs.append(
            _source_run(
                source="openalex",
                execution_status=batch.coverage_state.value,
                external_calls=0,
                records_received=len(batch.documents),
                started_at=now,
                completed_at=now,
            )
        )
        return batch.documents, coverage, source_runs
    if mode == "CACHE":
        sid = state.snapshot_id or "ft_bench_v1"
        state.snapshot_id = sid
        works = load_openalex_works(sid)
        batch = oa.search_from_fixture(works, snapshot_id=sid)
        coverage["openalex"] = "CACHE_REUSE"
        coverage["snapshot_id"] = sid
        coverage["external_calls"] = 0
        source_runs.append(
            _source_run(
                source="openalex",
                execution_status="CACHE_REUSE",
                external_calls=0,
                records_received=len(batch.documents),
                started_at=now,
                completed_at=now,
            )
        )
        return batch.documents, coverage, source_runs
    if mode == "LIVE":
        budgets = BudgetTracker()
        t0 = datetime.now(UTC).isoformat()
        oa_result = oa.search_live_bounded(
            state.normalized_query,
            run_id=state.run_id,
            max_calls=budgets.for_source("openalex").remaining,
        )
        budgets.for_source("openalex").consume(oa_result.calls_used)
        cordis = CordisAdapter().search(
            state.normalized_query, budgets.for_source("cordis").remaining
        )
        budgets.for_source("cordis").consume(cordis.calls_used)
        epo = EpoLodAdapter().search(
            state.normalized_query, budgets.for_source("epo_lod").remaining
        )
        budgets.for_source("epo_lod").consume(epo.calls_used)
        t1 = datetime.now(UTC).isoformat()
        coverage["openalex"] = oa_result.coverage_state.value
        coverage["cordis"] = cordis.coverage_state.value
        coverage["epo_lod"] = epo.coverage_state.value
        coverage["openalex_pages"] = oa_result.pages
        coverage["openalex_cap_reached"] = oa_result.cap_reached
        docs = _dedupe_documents(
            list(oa_result.documents) + list(cordis.documents) + list(epo.documents)
        )
        source_runs.extend(
            [
                _source_run(
                    source="openalex",
                    execution_status=oa_result.coverage_state.value,
                    external_calls=oa_result.calls_used,
                    records_received=len(oa_result.documents),
                    cap_reached=oa_result.cap_reached,
                    started_at=t0,
                    completed_at=t1,
                ),
                _source_run(
                    source="cordis",
                    execution_status=cordis.coverage_state.value,
                    external_calls=cordis.calls_used,
                    records_received=len(cordis.documents),
                    started_at=t0,
                    completed_at=t1,
                ),
                _source_run(
                    source="epo_lod",
                    execution_status=epo.coverage_state.value,
                    external_calls=epo.calls_used,
                    records_received=len(epo.documents),
                    error=epo.error,
                    started_at=t0,
                    completed_at=t1,
                ),
            ]
        )
        if epo.coverage_state == CoverageState.SEARCH_ERROR and epo.error:
            emit_event(
                "SOURCE_ERROR",
                run_id=state.run_id,
                mode=mode,
                component="epo_lod",
                reason_code=epo.error,
            )
        if oa_result.coverage_state == CoverageState.SEARCH_ERROR:
            coverage["reference_source"] = "REFERENCE_SOURCE_UNAVAILABLE"
        return docs, coverage, source_runs
    raise ValueError(f"unsupported data_mode: {mode}")


def _dedupe_documents(docs: list[NormalizedSourceDocument]) -> list[NormalizedSourceDocument]:
    seen: set[str] = set()
    out: list[NormalizedSourceDocument] = []
    for doc in docs:
        key = doc.stable_external_id
        if key in seen:
            continue
        seen.add(key)
        out.append(doc)
    return out


def _build_yearly_stats(cd: dict, documents: list[NormalizedSourceDocument]) -> list[YearStat]:
    doc_ids = set(cd["document_ids"])
    by_year: dict[int, int] = defaultdict(int)
    domain_by_year: dict[int, int] = defaultdict(int)
    for doc in documents:
        if doc.year is None:
            continue
        domain_by_year[doc.year] += 1
        if doc.source_document_id in doc_ids:
            by_year[doc.year] += 1
    years = sorted(set(by_year) | set(domain_by_year))
    return [
        YearStat(
            year=y,
            candidate_doc_count=by_year.get(y, 0),
            domain_doc_count=max(domain_by_year.get(y, 1), 1),
        )
        for y in years
    ]


def _parse_yearly(c: CandidateRecord) -> list[YearStat]:
    out: list[YearStat] = []
    for row in c.yearly_stats:
        out.append(
            YearStat(
                year=int(row["year"]),
                candidate_doc_count=int(row["candidate_doc_count"]),
                domain_doc_count=int(row["domain_doc_count"]),
            )
        )
    return out


def _compute_features(
    candidates: list[CandidateRecord],
    *,
    yearly_map: dict[str, list[YearStat]],
    backend: EmbeddingBackend | None,
    documents: list[NormalizedSourceDocument],
) -> None:
    embedding_missing = backend is None
    doc_by_id = {d.source_document_id: d for d in documents}
    a_raw: dict[str, float] = {}
    b_raw: dict[str, float] = {}
    c_raw: dict[str, float] = {}
    d_raw: dict[str, float] = {}
    e_raw: dict[str, float] = {}

    for c in candidates:
        yearly = yearly_map[c.candidate_id]
        ar = compute_a_raw(yearly)
        br = compute_b_raw(yearly)
        others = [
            oc.signature
            for oc in candidates
            if oc.candidate_id != c.candidate_id and oc.signature is not None
        ]
        cr = compute_c_raw(c.signature, others, backend) if c.signature else None
        d_diag = _d_diagnostics(c, doc_by_id)
        c.d_diagnostics = d_diag
        dr = compute_d_raw(
            lineage_count=d_diag["lineage_count"],
            independent_org_count=d_diag["independent_org_count"],
            source_class_count=d_diag["source_class_count"],
            reference_recurrence=d_diag["reference_recurrence"],
        )
        share = yearly[-1].share if yearly else 0.0
        if ar is not None:
            a_raw[c.candidate_id] = ar
        if br is not None:
            b_raw[c.candidate_id] = br
        if cr is not None:
            c_raw[c.candidate_id] = cr
        d_raw[c.candidate_id] = dr
        e_raw[c.candidate_id] = compute_e_percentile_input(share)

    p_a = midrank_percentiles(a_raw) if a_raw else {}
    p_b = midrank_percentiles(b_raw) if b_raw else {}
    p_c = midrank_percentiles(c_raw) if c_raw else {}
    p_d = midrank_percentiles(d_raw) if d_raw else {}
    p_e = inverse_percentiles(e_raw) if e_raw else {}
    pq = percentile_quality(len(candidates))

    for c in candidates:
        feats: dict[str, dict[str, Any]] = {}
        for code, raw_map, pmap in [
            ("A", a_raw, p_a),
            ("B", b_raw, p_b),
            ("C", c_raw, p_c),
            ("D", d_raw, p_d),
            ("E", e_raw, p_e),
        ]:
            raw = raw_map.get(c.candidate_id)
            pct = pmap.get(c.candidate_id)
            if code == "C" and embedding_missing:
                avail = "EMBEDDING_UNAVAILABLE"
            elif pct is not None:
                avail = "OK"
            else:
                avail = "UNKNOWN"
            feats[code] = {
                "raw": raw,
                "percentile": pct,
                "availability": avail,
                "percentile_quality": pq.flag,
            }
        if "D" in feats:
            feats["D"]["diagnostics"] = c.d_diagnostics
        c.features = feats
        c.state = "SCORABLE"


def _d_diagnostics(
    c: CandidateRecord, doc_by_id: dict[str, NormalizedSourceDocument]
) -> dict[str, Any]:
    docs = [doc_by_id[did] for did in c.document_ids if did in doc_by_id]
    lineages = {d.stable_external_id for d in docs}
    orgs: set[str] = set()
    sources_observed: set[str] = set()
    for d in docs:
        orgs.update(d.organization_names)
        if d.source_type.startswith("openalex"):
            sources_observed.add("openalex")
        elif d.source_type.startswith("cordis"):
            sources_observed.add("cordis")
        elif d.source_type.startswith("epo"):
            sources_observed.add("epo_lod")
    return {
        "lineage_count": len(lineages),
        "independent_org_count": len(orgs),
        "source_class_count": len(sources_observed),
        "reference_recurrence": 0.0,
        "coverage_uncertainty": list(
            {d.coverage_state.value for d in docs if d.coverage_state != CoverageState.FOUND}
        ),
    }


def _apply_sufficiency_and_filters(
    candidates: list[CandidateRecord],
    documents: list[NormalizedSourceDocument],
) -> None:
    domain_shares = [c.features.get("E", {}).get("raw") or 0.0 for c in candidates]
    p90 = _percentile(domain_shares, 90) if domain_shares else 1.0
    current_year = datetime.now(UTC).year

    mk_ps: list[float | None] = []
    for c in candidates:
        ys = _parse_yearly(c)
        shares = [y.share for y in sorted(ys, key=lambda s: s.year)]
        mk_ps.append(mann_kendall_q(shares))

    for c in candidates:
        if c.document_count < 10 or c.organization_count < 3:
            c.state = "INSUFFICIENT"
            c.ranking_status = "UNKNOWN_INSUFFICIENT"
            c.filters.append(
                {
                    "filter_code": "DATA_SUFFICIENCY",
                    "passed": False,
                    "failure_class": "INSUFFICIENT",
                    "reason_code": "MIN_WORKS_OR_ORGS",
                }
            )
            continue
        share = c.features.get("E", {}).get("raw") or 0.0
        if share >= p90:
            c.state = "REJECTED_BY_HEURISTIC_FILTER"
            c.ranking_status = "REJECTED"
            c.filters.append(
                {
                    "filter_code": "MAINSTREAM_SHARE",
                    "passed": False,
                    "failure_class": "HEURISTIC_REJECT",
                    "reason_code": "SHARE_GTE_P90",
                    "threshold": p90,
                    "raw_value": share,
                }
            )
            continue
        idx = candidates.index(c)
        q = mk_ps[idx]
        if q is None:
            c.state = "INSUFFICIENT"
            c.ranking_status = "UNKNOWN_INSUFFICIENT"
            c.filters.append(
                {
                    "filter_code": "MK_TREND",
                    "passed": False,
                    "failure_class": "INSUFFICIENT",
                    "reason_code": "HISTORY_TOO_SHORT",
                }
            )
            continue
        if q >= 0.10:
            c.state = "REJECTED_BY_HEURISTIC_FILTER"
            c.ranking_status = "REJECTED"
            c.filters.append(
                {
                    "filter_code": "MK_TREND",
                    "passed": False,
                    "failure_class": "HEURISTIC_REJECT",
                    "reason_code": "Q_GTE_0_10",
                    "raw_value": q,
                }
            )
            continue
        age = None
        if c.first_observed_year:
            age = current_year - c.first_observed_year + 1
        if age is not None and age > 8:
            c.state = "REJECTED_BY_HEURISTIC_FILTER"
            c.ranking_status = "REJECTED"
            c.filters.append(
                {
                    "filter_code": "OBSERVED_AGE",
                    "passed": False,
                    "failure_class": "HEURISTIC_REJECT",
                    "reason_code": "AGE_GT_8",
                    "raw_value": age,
                }
            )
            continue
        c.state = "QUALIFIED"
        del documents  # referenced for future D lineage extensions


def _score_and_rank(candidates: list[CandidateRecord]) -> None:
    scored: list[CandidateRecord] = []
    for c in candidates:
        if c.state != "QUALIFIED":
            continue
        percentiles = {code: f.get("percentile") for code, f in c.features.items()}
        score = ABCDE_V1.weighted_score(percentiles)  # type: ignore[arg-type]
        if score is None:
            c.state = "INSUFFICIENT"
            c.ranking_status = "UNKNOWN_INSUFFICIENT"
            continue
        c.score = round(score, 2)
        contrib = {}
        for code, f in c.features.items():
            p = f.get("percentile")
            if p is not None:
                contrib[code] = {
                    "weight": ABCDE_V1.weights[code],
                    "contribution": round(ABCDE_V1.weights[code] * p, 2),
                }
        c.features["_contributions"] = contrib  # type: ignore[assignment]
        c.state = "RANKED"
        c.ranking_status = "RANKED"
        scored.append(c)

    scored.sort(key=lambda x: (-(x.score or 0), x.candidate_id))
    for i, c in enumerate(scored, start=1):
        c.rank = i


def _build_registries(candidates: list[CandidateRecord]) -> dict[str, list[str]]:
    top15: list[str] = []
    below: list[str] = []
    rejected: list[str] = []
    insufficient: list[str] = []
    ranked = [c for c in candidates if c.ranking_status == "RANKED"]
    ranked.sort(key=lambda x: x.rank or 9999)
    for c in ranked:
        if c.rank is not None and c.rank <= 15:
            top15.append(c.candidate_id)
        else:
            below.append(c.candidate_id)
    for c in candidates:
        if c.ranking_status == "REJECTED":
            rejected.append(c.candidate_id)
        elif c.ranking_status == "UNKNOWN_INSUFFICIENT":
            insufficient.append(c.candidate_id)
    return {
        "TOP15": top15,
        "RANKED_BELOW_15": below,
        "REJECTED": rejected,
        "UNKNOWN_INSUFFICIENT": insufficient,
    }


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    k = (len(xs) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return xs[int(k)]
    return xs[f] + (k - f) * (xs[c] - xs[f])
