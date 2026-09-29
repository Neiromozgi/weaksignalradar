"""FastTrack /api/v1 routes (handoff 13)."""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from weaksignalradar.observability.event_log import emit_event, read_recent_events

from ..config.embedding_profile import E5_SMALL_V1
from ..config.scoring import ABCDE_V1, FEATURE_CONTRACT_VERSION
from ..corpus.snapshot_registry import get_snapshot_metadata, list_snapshot_catalog
from ..embedding.backend import embedding_runtime_status, get_embedding_backend
from ..llm.base import llm_runtime_status
from ..llm.profile import LLM_MODEL, LLM_PROFILE_ID, LLM_PROVIDER
from ..persistence_guard import (
    ensure_persistence_operational,
    ensure_postgres_persistence,
    is_persistence_failure,
)
from ..pipeline.runner import refresh_corpus, start_analysis
from ..sources.cordis import CordisAdapter
from ..sources.epo_lod import EpoLodAdapter
from ..sources.openalex_ft import OpenAlexFastTrackAdapter
from .deps import get_run_repository, load_run
from .schemas import (
    AnalysisCreateRequest,
    AnalysisCreateResponse,
    MethodologyRuntimeResponse,
    RefreshRequest,
)
from .serialize import candidate_to_api, document_row

router = APIRouter(prefix="/api/v1", tags=["fasttrack"])


@router.post("/analyses", response_model=AnalysisCreateResponse)
def create_analysis(body: AnalysisCreateRequest, request: Request) -> AnalysisCreateResponse:
    ensure_persistence_operational(request)
    repo = get_run_repository(request)
    emit_event(
        "ANALYSIS_STARTED",
        run_id=None,
        mode=body.data_mode,
        component="pipeline",
        extra={"query_len": len(body.query or "")},
    )
    try:
        state = start_analysis(
            query=body.query,
            data_mode=body.data_mode,
            score_profile_id=body.score_profile_id,
            snapshot_id=body.snapshot_id,
            repository=repo,
        )
    except Exception as exc:
        if is_persistence_failure(exc):
            emit_event(
                "PERSISTENCE_UNAVAILABLE",
                level="ERROR",
                mode=body.data_mode,
                component="persistence",
                reason_code="db_unavailable",
            )
            raise HTTPException(status_code=503, detail="PERSISTENCE_UNAVAILABLE") from exc
        raise
    if state.status == "FAILED":
        emit_event(
            "ANALYSIS_FAILED",
            level="ERROR",
            run_id=state.run_id,
            mode=state.data_mode,
            component="pipeline",
            reason_code=(state.coverage_summary or {}).get("error"),
        )
    else:
        emit_event(
            "ANALYSIS_COMPLETED",
            run_id=state.run_id,
            mode=state.data_mode,
            component="pipeline",
            status=state.status,
        )
    return AnalysisCreateResponse(
        run_id=state.run_id,
        status=state.status,
        data_mode=state.data_mode,
        snapshot_id=state.snapshot_id,
        coverage=state.coverage_summary,
    )


@router.get("/analyses/{run_id}")
def get_analysis(run_id: str, request: Request) -> dict[str, Any]:
    state = load_run(run_id, request)
    return {
        "run_id": state.run_id,
        "status": state.status,
        "normalized_query": state.normalized_query,
        "data_mode": state.data_mode,
        "snapshot_id": state.snapshot_id,
        "coverage": state.coverage_summary,
        "provenance": state.provenance,
        "registries": state.registries,
        "source_runs": state.source_runs,
        "started_at": state.started_at,
        "finished_at": state.finished_at,
    }


@router.post("/refresh")
def post_refresh(body: RefreshRequest, request: Request) -> dict[str, Any]:
    engine = ensure_postgres_persistence(request)
    try:
        result = refresh_corpus(query=body.query, engine=engine)
    except Exception as exc:
        if is_persistence_failure(exc):
            emit_event(
                "PERSISTENCE_UNAVAILABLE",
                level="ERROR",
                component="persistence",
                reason_code="db_unavailable",
            )
            raise HTTPException(status_code=503, detail="PERSISTENCE_UNAVAILABLE") from exc
        raise
    snap_id = result.get("snapshot_id")
    if snap_id:
        emit_event(
            "SNAPSHOT_CREATED",
            component="snapshot",
            extra={"snapshot_id": snap_id, "documents": result.get("documents_added")},
        )
    return result


@router.get("/analyses/{run_id}/documents")
def list_documents(
    run_id: str,
    request: Request,
    source: str | None = None,
    year: int | None = None,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    state = load_run(run_id, request)
    rows = state.documents
    if source:
        rows = [
            d for d in rows if d.source_id.startswith(source) or d.source_type.startswith(source)
        ]
    if year is not None:
        rows = [d for d in rows if d.year == year]
    if candidate_id:
        cand = next((c for c in state.candidates if c.candidate_id == candidate_id), None)
        if cand:
            ids = set(cand.document_ids)
            rows = [d for d in rows if d.source_document_id in ids]
    return {"run_id": run_id, "documents": [document_row(d) for d in rows]}


@router.get("/documents/{source_document_id}")
def get_document(
    source_document_id: str,
    request: Request,
    run_id: str = Query(...),
) -> dict[str, Any]:
    state = load_run(run_id, request)
    for d in state.documents:
        if d.source_document_id == source_document_id:
            return document_row(d)
    raise HTTPException(status_code=404, detail="document_not_found")


@router.get("/analyses/{run_id}/candidates")
def list_candidates(run_id: str, request: Request, state: str = Query("all")) -> dict[str, Any]:
    run = load_run(run_id, request)
    items = run.candidates
    if state != "all":
        mapping = {
            "top15": run.registries.get("TOP15", []),
            "below15": run.registries.get("RANKED_BELOW_15", []),
            "rejected": run.registries.get("REJECTED", []),
            "insufficient": run.registries.get("UNKNOWN_INSUFFICIENT", []),
        }
        if state in mapping:
            allowed = set(mapping[state])
            items = [c for c in items if c.candidate_id in allowed]
        else:
            items = [c for c in items if c.state.lower().startswith(state.lower())]
    return {
        "run_id": run_id,
        "candidates": [candidate_to_api(c, run) for c in items],
    }


@router.get("/analyses/{run_id}/candidates/{candidate_id}")
def get_candidate(run_id: str, candidate_id: str, request: Request) -> dict[str, Any]:
    run = load_run(run_id, request)
    for c in run.candidates:
        if c.candidate_id == candidate_id:
            return candidate_to_api(c, run)
    raise HTTPException(status_code=404, detail="candidate_not_found")


@router.get("/analyses/{run_id}/registries/{registry_name}")
def get_registry(run_id: str, registry_name: str, request: Request) -> dict[str, Any]:
    norm = registry_name.lower().replace("-", "")
    alias = {
        "top15": "TOP15",
        "below15": "RANKED_BELOW_15",
        "rejected": "REJECTED",
        "insufficient": "UNKNOWN_INSUFFICIENT",
    }
    key = alias.get(norm, registry_name.upper().replace("-", "_"))
    if key == "BELOW15":
        key = "RANKED_BELOW_15"
    run = load_run(run_id, request)
    ids = run.registries.get(key, [])
    cands = [c for c in run.candidates if c.candidate_id in ids]
    return {
        "registry": key,
        "candidate_ids": ids,
        "candidates": [candidate_to_api(c, run) for c in cands],
    }


@router.get("/methodology/runtime", response_model=MethodologyRuntimeResponse)
def methodology_runtime() -> MethodologyRuntimeResponse:
    return MethodologyRuntimeResponse(
        score_profile_id=ABCDE_V1.score_profile_id,
        feature_contract_version=FEATURE_CONTRACT_VERSION,
        embedding_profile_id=E5_SMALL_V1.embedding_profile_id,
        embedding_model_id=E5_SMALL_V1.embedding_model_id,
        embedding_model_revision=E5_SMALL_V1.embedding_model_revision,
    )


@router.get("/config/sources")
def config_sources() -> dict[str, Any]:
    return {
        "sources": [
            asdict(OpenAlexFastTrackAdapter().health()),
            asdict(CordisAdapter().health()),
            asdict(EpoLodAdapter().health()),
        ]
    }


@router.get("/config/llm")
def config_llm() -> dict[str, Any]:
    return {
        "provider": LLM_PROVIDER,
        "profile_id": LLM_PROFILE_ID,
        "model": LLM_MODEL,
        "status": llm_runtime_status(),
        "openai_api_key": "CONFIGURED"
        if os.environ.get("OPENAI_API_KEY", "").strip()
        else "MISSING",
    }


@router.get("/snapshots")
def list_snapshots(request: Request) -> dict[str, Any]:
    engine = getattr(request.app.state, "engine", None)
    return {"snapshots": list_snapshot_catalog(engine)}


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: str, request: Request) -> dict[str, Any]:
    engine = getattr(request.app.state, "engine", None)
    meta = get_snapshot_metadata(engine, snapshot_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="snapshot_not_found")
    return meta


@router.get("/config/embedding")
def config_embedding() -> dict[str, Any]:
    backend = None
    backend_name = None
    try:
        backend = get_embedding_backend(allow_none=True)
        backend_name = backend.backend_name if backend else None
    except Exception:
        backend_name = None
    return {
        "embedding_profile_id": E5_SMALL_V1.embedding_profile_id,
        "embedding_model_id": E5_SMALL_V1.embedding_model_id,
        "embedding_model_revision": E5_SMALL_V1.embedding_model_revision,
        "vector_dimension": E5_SMALL_V1.vector_dimension,
        "runtime_status": embedding_runtime_status(),
        "active_backend": backend_name,
    }


@router.post("/analyses/{run_id}/bootstrap")
def post_bootstrap(run_id: str, request: Request) -> dict[str, str]:
    load_run(run_id, request)
    return {
        "bootstrap_request_id": f"bs_{run_id[:8]}",
        "status": "NOT_REQUESTED",
        "message": "Bootstrap is ON_DEMAND plumbing only in FastTrack P0",
    }


@router.get("/diagnostics")
def diagnostics_summary(request: Request) -> dict[str, Any]:
    live = config_embedding()
    llm = config_llm()
    sources = config_sources()
    events = read_recent_events(limit=200)
    analyses = [e for e in events if e.get("event", "").startswith("ANALYSIS_")]
    last_analysis = analyses[-1] if analyses else None
    snapshots = [e for e in events if e.get("event") == "SNAPSHOT_CREATED"]
    last_snap = snapshots[-1] if snapshots else None
    eng = getattr(request.app.state, "engine", None)
    db_ready = False
    if eng is not None:
        from weaksignalradar.storage.db import check_db_ready

        db_ready = check_db_ready(eng)
    return {
        "service": "READY" if db_ready else "NOT_READY",
        "database": "READY" if db_ready else "NOT_READY",
        "embedding": live.get("runtime_status"),
        "llm": llm.get("status"),
        "openai_api_key": llm.get("openai_api_key"),
        "sources": {s["source_id"]: s["status"] for s in sources.get("sources", [])},
        "analyses_recorded": len(analyses),
        "last_run_id": last_analysis.get("run_id") if last_analysis else None,
        "last_run_status": last_analysis.get("status") if last_analysis else None,
        "last_snapshot_id": last_snap.get("snapshot_id") if last_snap else None,
    }


@router.get("/observability/events")
def observability_events(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    return {"events": read_recent_events(limit=limit)}


@router.get("/metrics")
def metrics(request: Request) -> dict[str, Any]:
    repo = getattr(request.app.state, "run_repository", None)
    return {
        "persistence": type(repo).__name__ if repo is not None else "UNAVAILABLE",
    }
