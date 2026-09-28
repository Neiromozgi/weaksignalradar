# СННИТ РАДАР (WSR)

**[English](README.md) | Русский**

Радар сигнала новой научно-исследовательской технологии.

## Что это

Веб-система для поиска **ранних научно-технологических сигналов** по открытому запросу. Результат — ранжированный TOP-15 (до 15) квалифицированных направлений с прозрачными признаками A–E, фильтрами и provenance.

Система **не гарантирует** коммерческий успех технологий.

## Архитектура (кратко)

- FastAPI backend + PostgreSQL (`ft_*` persistence)
- UI v1.0.3: Главная → обработка → TOP-15 → Technology Card
- Режимы: LIVE / CACHE / SNAPSHOT
- Источники: OpenAlex (reference), CORDIS/EURIO, EPO LOD (fail-soft)
- Embedding: `intfloat/multilingual-e5-small` (frozen revision)
- LLM: structured extraction (OpenAI profile; ключ локально)

## Требования

- Windows: Git, Docker Desktop, браузер
- Интернет: для `docker compose build`, первой загрузки весов E5, LIVE-источников (по необходимости)
- CACHE/SNAPSHOT **не требуют** персональных API-ключей

## Быстрый запуск (Docker — основной путь)

```powershell
git clone <repository-url>
cd weaksignalradar
git checkout snnit-fasttrack   # или release tag
Copy-Item .env.example .env
# Заполните POSTGRES_* (обязательно). SOURCE_API_KEY / OPENAI_API_KEY — для LIVE/LLM.
.\run.ps1 -Build
```

Открыть: http://127.0.0.1:8000/

```powershell
.\manage.ps1 status
.\manage.ps1 sources
.\manage.ps1 llm-status
.\manage.ps1 snapshots
.\manage.ps1 logs -Tail 50
.\manage.ps1 diagnostics
.\manage.ps1 help
```

## CACHE / SNAPSHOT

- **CACHE** — benchmark `ft_bench_v1`, без внешних вызовов (явная маркировка в UI).
- **SNAPSHOT** — воспроизведение зафиксированного корпуса (`POST /api/v1/refresh` создаёт новый `snap_*`).

## LIVE

Bounded caps OpenAlex/CORDIS/EPO (см. README English). Требуются разрешённые credentials в `.env`.

## PostgreSQL / Alembic

Compose использует `@db:5432`. Миграции: `a04_001` → `ft_001` → `ft_002`. `docker compose` выполняет `alembic upgrade head` при старте backend.

## UI

Primary flow v1.0.3. Secondary: Все результаты, Документы, Кандидаты, Методология.

## Методология (пользовательская)

См. страницу «Методология» в UI или addendum `08_USER_METHODOLOGY_CONTENT_v1.md`.

Score: `0.30A + 0.20B + 0.25C + 0.15D + 0.10E`.

## Логи и диагностика

- Файл: `logs/snnit-radar.jsonl` (volume `logs_data`, переживает restart контейнера)
- `.\manage.ps1 logs`
- `.\manage.ps1 diagnostics`
- API: `/api/v1/diagnostics`, `/api/v1/observability/events`

Secrets **не** пишутся в лог.

## Первый запуск E5

При первом encode Docker может **скачать** модель Hugging Face (~сотни МБ). Полностью offline без предварительной загрузки **не заявляется**.

## Тесты

```powershell
pip install -e ".[dev]"
pytest
ruff check src tests
```

## Остановка

```powershell
docker compose down
```

**Внимание:** `docker compose down -v` удаляет volumes (PostgreSQL, snapshots, logs).

## Эксперт / жюри (clean machine)

1. Fresh clone + новый `.env` из `.env.example`
2. `.\run.ps1 -Build`
3. UI: режим CACHE + `ft_bench_v1` для воспроизводимой проверки
4. `.\manage.ps1 diagnostics`

Не требуются: Cursor, локальный venv разработчика, существующий PostgreSQL хоста.

## Статус компонентов

| Компонент | Статус |
|-----------|--------|
| UI v1.0.3 primary flow | **IMPLEMENTED** |
| PostgreSQL persistence | **IMPLEMENTED** |
| Observability jsonl | **IMPLEMENTED** |
| Bootstrap ON_DEMAND | **PARTIAL** |
| Full manage.ps1 admin (handoff §26) | **ROADMAP** |

## Troubleshooting

- `503 PERSISTENCE_UNAVAILABLE` — PostgreSQL недоступен; `manage.ps1 status`
- Embedding UNAVAILABLE — проверьте образ backend и первую загрузку модели
- LIVE partial — см. diagnostics и Technology Card «Ограничения»
