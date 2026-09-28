# weaksignalradar — СННИТ РАДАР (FastTrack)

**English | [Русский](README_RU.md)**

Branch: `snnit-fasttrack`. Release finalization (UI v1.0.3 / observability).

Persistent local events: `logs/snnit-radar.jsonl` (Docker volume `logs_data:/app/logs`). Use `.\manage.ps1 logs` / `diagnostics`.

## Status (factual)

| Component | Status |
|-----------|--------|
| PostgreSQL `ft_*` persistence | **IMPLEMENTED** (fail-closed; no silent memory fallback) |
| Restart persistence | **IMPLEMENTED** |
| Frozen E5 embedding in Docker | **IMPLEMENTED** (`sentence-transformers` + `intfloat/multilingual-e5-small` @ revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`) |
| Embedding degraded state | **IMPLEMENTED** (`EMBEDDING_UNAVAILABLE` on feature C when runtime missing; tests use `WSR_EMBEDDING_BACKEND=deterministic`) |
| LIVE refresh → immutable snapshot | **IMPLEMENTED** (`POST /api/v1/refresh`, `ft_snapshots` + `/app/snapshots` volume) |
| `/api/v1` + UI P0 surfaces | **IMPLEMENTED** (real API; CACHE labelled) |
| OpenAI LLM LIVE | **IMPLEMENTED** (local `OPENAI_API_KEY` in `.env` only) |
| Bootstrap | **ON_DEMAND / PARTIAL** (not a blocker) |
| Full `manage.ps1` admin (handoff §26 superset) | **ROADMAP** |

## Quick start

```powershell
copy .env.example .env
# POSTGRES_*, SOURCE_API_KEY, OPENAI_API_KEY (never commit .env)

pip install -e ".[dev]"
.\run.ps1 -Build
.\manage.ps1 status
```

Compose backend uses `@db:5432` for `DATABASE_URL`, mounts `snapshot_data` at `/app/snapshots`, and passes through source/LLM env vars from `.env` (names only in `.env.example`).

## Embedding (frozen `e5_small_v1`)

| Field | Value |
|-------|--------|
| Model | `intfloat/multilingual-e5-small` |
| Revision | `614241f622f53c4eeff9890bdc4f31cfecc418b3` |
| Dimension | 384 |
| Pooling / norm / metric | mean / L2 / cosine |

Default Docker path: `WSR_EMBEDDING_BACKEND=auto` → `SentenceTransformerBackend` when package is installed.

Explicit states via `/api/v1/config/embedding` and run provenance (`embedding_runtime_status`, `embedding_backend`). Feature **C** uses `availability=EMBEDDING_UNAVAILABLE` when runtime is missing — not fabricated scores.

Unit tests: `WSR_EMBEDDING_BACKEND=deterministic`.

## Persistence fail-closed

If PostgreSQL is unavailable (including **after startup**):

- `/health/live` → 200  
- `/health/ready` → 503 (`database_*` or `persistence_unavailable`)  
- `/api/v1/analyses`, `/api/v1/refresh`, and other persistence routes → **503** with `detail=PERSISTENCE_UNAVAILABLE` (no SQL stack trace / secrets in JSON response)

Analysis is checked **before** pipeline work when DB check fails.

`MemoryRunRepository` is only for explicit test injection, not production default.

## LIVE refresh & snapshots

```http
POST /api/v1/refresh  {"query":"..."}
```

Bounded LIVE acquisition → dedup → new `snap_*` id → `corpus.json` on disk + `ft_snapshots` row. `GET /api/v1/snapshots` lists benchmark `ft_bench_v1` plus registered LIVE snapshots. **SNAPSHOT** analysis replays stored corpus with **zero** external source calls.

## UI v1.0.3 (primary flow)

Addendum `07_UI_PRIMARY_USER_FLOW_v1`: blue/white shell, black body text.

Primary path: **HOME → RUNNING → TOP-15 → Technology Card** (human-readable card, not raw JSON).

- HOME: default mode **LIVE**; compact CACHE/SNAPSHOT settings  
- Secondary (after results): **Все результаты**, **Документы**, **Кандидаты**, **Методология**  
- Explicit navigation: «← Вернуться на главную», «← Назад к TOP-15»  
- CACHE/SNAPSHOT/benchmark labelled; no fake LIVE TOP-15  
- States: IDLE / RUNNING / COMPLETED / FAILED / PARTIAL

## Operator CLI

```powershell
.\manage.ps1 status | sources | llm-status | snapshots | logs | diagnostics | help
.\manage.ps1 logs -Tail 50
```

Expert/jury clean machine: clone → `.env.example` → `.env` → `.\run.ps1 -Build` → http://127.0.0.1:8000/ (CACHE + `ft_bench_v1` needs no personal API keys). Shutdown: `docker compose down` (avoid `down -v` unless you intend to wipe DB/snapshots/logs volumes).

## Tests

```powershell
pytest tests/unit
pytest tests/integration   # DATABASE_URL loopback
$env:RUN_LIVE_SMOKE=1; pytest tests/integration/test_source_live_smoke.py
$env:RUN_LIVE_LLM=1; pytest tests/integration/test_llm_live_smoke.py
ruff check src tests
```

## Limitations

- CORDIS/EPO normalization remains endpoint-dependent (**PARTIAL**).
- Bootstrap API is plumbing only.
- Independent TEST is Coordinator-driven (not run by DEV).
