# weaksignalradar — СННИТ РАДАР (WSR)

**English | [Русский](README_RU.md)**

Branch: `snnit-fasttrack`. Tagline: *Радар сигнала новой научно-исследовательской технологии*.

## Quick start (fresh clone)

```cmd
copy .env.example .env
run.cmd -Build
```

Open http://127.0.0.1:8000/ — verify `GET /health/ready` → `{"status":"ready"}`.

Default `.env.example` includes local PostgreSQL demo credentials (not external secrets). **Never commit `.env`.**

## Release configuration (Docker)

Tracked in `compose.yaml`:

| Variable | Default in compose | Purpose |
|----------|-------------------|---------|
| `DISCOVERY_V2_ENABLED` | `true` | TMF + E5 discovery v2 (frozen core) |
| `WSR_ALLOW_LLM_PROVIDER` | `0` | OpenAI planner/TMF/signatures; set `1` in `.env` for **LIVE only** |
| `WSR_EMBEDDING_BACKEND` | `auto` | Frozen E5 in image |

CACHE/SNAPSHOT runs set `offline_replay` and **ignore** `WSR_ALLOW_LLM_PROVIDER` (zero LLM provider calls). LIVE semantics unchanged.

## CACHE / SNAPSHOT demo (no external APIs)

- UI mode **CACHE** + `ft_bench_v1`, or **SNAPSHOT** after `POST /api/v1/refresh`.
- `external_calls=0`, `llm_provider_calls=0`, `tmf_provider_calls=0` in run provenance.
- UI flow: HOME → RESULTS → Technology Card; empty TOP-15 with UNKNOWN is valid.

## LIVE

Requires network, source credentials as configured, `OPENAI_API_KEY` and `WSR_ALLOW_LLM_PROVIDER=1` in local `.env`.

## Ports

- Backend/UI: `127.0.0.1:8000`
- PostgreSQL: `127.0.0.1:5432` optional for host tools; backend uses `db:5432` inside compose

## Recovery after reboot

```cmd
docker compose up -d
```

Avoid `docker compose down -v` unless you intend to wipe DB/snapshot/log volumes.

## Tests

```cmd
pytest tests -q
ruff check src tests
git diff --check
```

Offline proof: `tests/unit/fasttrack/test_offline_cache_snapshot.py`.

## Status (factual)

| Component | Status |
|-----------|--------|
| PostgreSQL persistence | fail-closed 503 when unavailable |
| Discovery v2 + frozen E5 | Docker `auto` backend |
| UI Results + `name_ru_recorded` | RU-first presentation |
| Offline CACHE/SNAPSHOT | no external/LLM provider calls (release fix) |

See [README_RU.md](README_RU.md) for operator commands and security notes.
