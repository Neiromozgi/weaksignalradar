# 09 — OBSERVABILITY AND DIAGNOSTICS v1

**Status:** APPROVED RELEASE REQUIREMENT

## Цель

Эксперт должен локально понять: запускался ли сервис, был ли он ready, какие analyses выполнялись, чем закончился последний run, какие source-components ошибались, создавался ли snapshot, были ли persistence/embedding/LLM ошибки.

Логи остаются локально. Скрытая удалённая telemetry не добавляется.

## Persistent log

Рекомендуемый формат: `logs/snnit-radar.jsonl` или эквивалентный structured log, сохраняемый через Docker volume/bind mount.

Минимальные поля:

`timestamp`, `event`, `level`, `run_id`, `mode`, `component`, `status`, `reason_code`, `duration_ms`.

Минимальные события:

`SERVICE_STARTED`, `SERVICE_READY`, `SERVICE_NOT_READY`,  
`ANALYSIS_STARTED`, `ANALYSIS_COMPLETED`, `ANALYSIS_FAILED`,  
`SOURCE_STARTED`, `SOURCE_COMPLETED`, `SOURCE_PARTIAL`, `SOURCE_ERROR`, `SOURCE_RATE_LIMITED`,  
`SNAPSHOT_CREATED`, `EMBEDDING_AVAILABLE`, `EMBEDDING_UNAVAILABLE`,  
`LLM_STARTED`, `LLM_COMPLETED`, `LLM_FAILED`, `PERSISTENCE_UNAVAILABLE`.

## Secrets

Не логировать API keys, PostgreSQL password, полный credential-bearing `DATABASE_URL`, `.env`, Authorization headers.

Показывать только безопасные статусы: `CONFIGURED`, `MISSING`, `AVAILABLE`, `UNAVAILABLE`.

## manage.ps1

Добавить:

`manage.ps1 logs` — последние безопасные события.  
`manage.ps1 diagnostics` — компактный отчёт по Service, DB, Embedding, LLM, OpenAlex, CORDIS, EPO, числу analyses, последнему run и snapshot.

PostgreSQL registries остаются authoritative; application log их не заменяет.

## Acceptance

PASS если события сохраняются после restart, ошибки имеют reason-code, `logs`/`diagnostics` работают, secrets отсутствуют, скрытой outbound telemetry нет.
