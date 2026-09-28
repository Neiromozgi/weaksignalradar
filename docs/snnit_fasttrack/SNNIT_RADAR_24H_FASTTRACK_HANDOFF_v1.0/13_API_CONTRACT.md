# 13 — API Contract

Prefix: `/api/v1`

## Health
`GET /health/live`  
`GET /health/ready`

## Analysis

`POST /api/v1/analyses`

```json
{
  "query": "искусственный интеллект",
  "data_mode": "CACHE",
  "score_profile_id": "ABCDE_v1",
  "snapshot_id": null
}
```

Response:
```json
{
  "run_id": "run_...",
  "status": "QUEUED|RUNNING|COMPLETED|PARTIAL|FAILED",
  "data_mode": "CACHE",
  "snapshot_id": "snap_...",
  "coverage": {}
}
```

`GET /api/v1/analyses/{run_id}`

## LIVE refresh

`POST /api/v1/refresh`

Creates a new acquisition/snapshot version. Never trigger silently when user only requests analysis.

## Source Document Registry

`GET /api/v1/analyses/{run_id}/documents`

Filters: source, year, original_availability_status, extraction_status, candidate_id.

Each row: source, stable ID, title/date, canonical URL, original availability, snapshot/provenance, candidate links.

`GET /api/v1/documents/{source_document_id}`

No endpoint is required to serve a locally stored original PDF because originals are not baseline-stored.

## Candidate Registry

`GET /api/v1/analyses/{run_id}/candidates?state=...`

States:
`all|discovered|normalized|scorable|qualified|ranked|top15|below15|rejected|insufficient`

`GET /api/v1/analyses/{run_id}/candidates/{candidate_id}`

Returns A–E raw/percentiles/contributions, filters, coverage, evidence, FWCI diagnostic, source links, explanation.

## Result registries

- `GET /api/v1/analyses/{run_id}/registries/top15`
- `GET /api/v1/analyses/{run_id}/registries/below15`
- `GET /api/v1/analyses/{run_id}/registries/rejected`
- `GET /api/v1/analyses/{run_id}/registries/insufficient`

## Methodology

`GET /api/v1/methodology/runtime`

Active formulas/method versions/profile/filters/source roles/model IDs/bootstrap status.

## Config

Read:
- `GET /api/v1/config/sources`
- `GET /api/v1/config/llm`

Change:
- `PATCH /api/v1/config/sources`
- `PATCH /api/v1/config/llm`

Mutation should be disabled/auth-protected in public/jury mode.

## Snapshots

`GET /api/v1/snapshots`  
`GET /api/v1/snapshots/{snapshot_id}`

## Bootstrap — ON DEMAND

`POST /api/v1/analyses/{run_id}/bootstrap`

`GET /api/v1/analyses/{run_id}/bootstrap/{bootstrap_request_id}`

Do not display interval until `COMPLETED`.

## Metrics

`GET /api/v1/metrics`

Operational only; no secrets.

> СННИТ РАДАР (WSR)
