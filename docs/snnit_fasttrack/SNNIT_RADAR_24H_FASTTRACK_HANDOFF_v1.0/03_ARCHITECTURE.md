# 03 — Модульная архитектура

```text
Browser / Web UI
      |
      v
FastAPI API Router
      |
      v
Orchestrator
  |       |        |
  |       |        +--> LLMAdapter --------> provider/local model
  |       |
  |       +-----------> SourceManager -----> SourceAdapter[*]
  |                                      OpenAlex
  |                                      CORDIS/EURIO
  |                                      EPO Linked Open Data
  |
  +--> Cache/Snapshot Manager
  +--> Source Document Registry
  +--> Candidate Discovery / Normalization
  +--> Candidate Registry
  +--> Feature Engine A–E
  +--> Sufficiency Gate
  +--> Heuristic Filters
  +--> Scoring / Ranking
  +--> Result Registries
  +--> Technology Card / Explain Service
      |
      v
PostgreSQL + bounded raw API snapshots + logs
```

## Источники

Core получает `NormalizedSourceDocument` через общий `SourceAdapter`.

Добавить источник:
1. adapter;
2. source role/capabilities;
3. config;
4. contract tests;
5. enable.

Выключить: config flag. Алгоритм не переписывается.

## LLM

Все LLM вызовы только через `LLMAdapter`. Provider/model/base URL/key меняются в config. Core ranking не зависит от бренда модели.

## Data modes

- `CACHE` — анализ локального корпуса, без внешних source calls.
- `LIVE` — явное обновление через источники.
- `SNAPSHOT` — воспроизводимый запуск по конкретному immutable snapshot.

> СННИТ РАДАР (WSR)
