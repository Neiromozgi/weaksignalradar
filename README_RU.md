# СННИТ РАДАР (WSR)

**[English](README.md) | Русский**

**Радар сигнала новой научно-исследовательской технологии.**

Веб-система для поиска ранних научно-технологических сигналов по открытому запросу. Результат — до 15 квалифицированных направлений (TOP-15 **без искусственного дополнения**), реестры кандидатов, документы и карточка технологии с признаками A–E и provenance.

## Быстрый запуск (fresh clone → браузер)

```cmd
git clone <repository-url>
cd weaksignalradar
git checkout snnit-fasttrack
copy .env.example .env
run.cmd -Build
```

Проверка:

```cmd
docker compose ps
curl http://127.0.0.1:8000/health/ready
```

Открыть: **http://127.0.0.1:8000/**

Путь **не требует** прав администратора и изменения ExecutionPolicy (Windows CMD: `run.cmd`, `manage.cmd`).

### Порты

| Сервис | Адрес | Назначение |
|--------|--------|------------|
| Backend + UI | `127.0.0.1:8000` | API и интерфейс |
| PostgreSQL | `127.0.0.1:5432` (опционально с хоста) | Только для Alembic/pytest с Windows; **backend в Docker ходит на `db:5432` внутри сети compose** |

Публикация PostgreSQL на loopback не обязательна для работы приложения в Docker.

## Демонстрация без внешних API (CACHE / SNAPSHOT)

Для конкурса и офлайн-показа:

1. В UI на главной выберите режим **CACHE** (snapshot `ft_bench_v1`) или **SNAPSHOT**.
2. Запустите анализ.

**Честное пояснение:** это **воспроизведение сохранённого корпуса и TMF-кэша**, не новый LIVE-поиск. Внешние источники (OpenAlex/CORDIS/EPO) и **LLM-провайдер не вызываются** (`offline_replay` в provenance, `external_calls=0`, `llm_provider_calls=0`).

В `.env` для demo достаточно:

- `DISCOVERY_V2_ENABLED=true` (по умолчанию в `.env.example`)
- `WSR_ALLOW_LLM_PROVIDER=0` (по умолчанию)
- пустые `OPENAI_API_KEY` и `SOURCE_API_KEY`

Локальный **E5 embedding** в Docker может работать — это не внешний LLM/API источник.

UI: **Главная → обработка (без текста про внешний поиск) → Результаты → карточка технологии**. Пустой TOP-15 при наличии UNKNOWN — нормальный исход, не ошибка.

## LIVE

Требуется:

- сеть до OpenAlex / CORDIS / EPO (bounded caps);
- `OPENAI_API_KEY` в локальном `.env` (не коммитить);
- `WSR_ALLOW_LLM_PROVIDER=1` в `.env` для вызовов planner/TMF/signatures.

Пример (без ключей в репозитории):

```env
OPENAI_API_KEY=<ваш ключ>
WSR_ALLOW_LLM_PROVIDER=1
```

Если LIVE недоступен (сеть, ключи), используйте CACHE/SNAPSHOT — приложение остаётся работоспособным для офлайн-demo.

## После перезагрузки / восстановление

```cmd
cd weaksignalradar
docker compose up -d
```

**Не используйте** `docker compose down -v` для обычного recovery — это удалит volumes (`db_data`, `snapshot_data`, `logs_data`).

Безопасное выключение:

```cmd
docker compose down
docker compose up -d
```

## Если запуск сломался

1. `manage.cmd diagnostics` / `docker compose logs backend`
2. Проверить `.env` (скопирован из `.env.example`, без лишних кавычек)
3. `docker compose up -d --build` после изменений кода
4. Recovery **без** `-v` (см. выше)

## Безопасность

- Секреты только в **`.env`** (файл в `.gitignore`).
- В git: **только** `.env.example` без реальных ключей.
- Не коммитить: `.env`, ключи OpenAI/OpenAlex, персональные данные.

## Ограничения MVP

- Bounded retrieval в LIVE; partial coverage источников возможен.
- Недостаточность evidence → TOP-15 может быть **пустым**; система **не дополняет** список искусственно.
- Bootstrap — plumbing only, не продуктовый блокер.

## Тесты (разработчик)

```cmd
pip install -e ".[dev]"
pytest tests -q
ruff check src tests
git diff --check
```

Офлайн-guarantee: `tests/unit/fasttrack/test_offline_cache_snapshot.py`.

## Оператор

```cmd
manage.cmd status
manage.cmd snapshots
manage.cmd diagnostics
```

Логи событий: volume `logs_data` → `/app/logs/snnit-radar.jsonl`.
