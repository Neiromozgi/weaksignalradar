"""Pydantic API schemas for /api/v1."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalysisCreateRequest(BaseModel):
    query: str = Field(min_length=1)
    data_mode: Literal["CACHE", "LIVE", "SNAPSHOT"] = "CACHE"
    score_profile_id: str = "ABCDE_v1"
    snapshot_id: str | None = None


class AnalysisCreateResponse(BaseModel):
    run_id: str
    status: str
    data_mode: str
    snapshot_id: str | None
    coverage: dict[str, Any]


class RefreshRequest(BaseModel):
    query: str = Field(min_length=1)


class MethodologyRuntimeResponse(BaseModel):
    score_profile_id: str
    feature_contract_version: str
    embedding_profile_id: str
    embedding_model_id: str
    embedding_model_revision: str
    bootstrap_status: str = "ON_DEMAND_NOT_P0_BLOCKER"
