# 19 — Cursor PRECHECK Instructions

## Goal

Проверить репозиторий и контракты до feature coding. PRECHECK может чинить environment blockers, но не менять методологию.

## Inputs

Нужно приложить:
- весь `SNNIT_RADAR_24H_FASTTRACK_HANDOFF_v1.0`;
- текущий Stage A repo;
- существующий frontend shell;
- текущий `.env.example`;
- имеющиеся source-adapter tests.

## Checklist

### Baseline
- зафиксировать current commit;
- run existing tests;
- inspect DB/Alembic/FastAPI/Docker;
- verify no secrets tracked.

### Environment
- Docker works;
- PostgreSQL works;
- migrations pass;
- FastAPI health works;
- static UI served;
- record OS/CPU/RAM/free disk/Docker/WSL versions for README.

### Sources
For each:
- health;
- config;
- cap enforcement;
- stable IDs;
- declared role.
OpenAlex must be viable as reference source.
CORDIS/EPO must fail-soft.

### Models
- pin `EMBEDDING_MODEL_ID` + exact revision;
- record LLM provider/model or `DISABLED`;
- test structured extraction fixture;
- verify boot without optional LLM key.

### Contracts
Confirm:
- Source Document Registry;
- Candidate Registry;
- A–E;
- percentile universe;
- sufficiency vs rejection;
- API schema;
- data modes.

## Output

`PRECHECK_REPORT.md`:
- `PASS` / `BLOCKED`;
- current commit;
- environment;
- source statuses;
- embedding model;
- LLM status;
- migrations/tests;
- deviations;
- blockers.

> СННИТ РАДАР (WSR)
