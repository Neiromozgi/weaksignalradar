# 11 — RELEASE DOCUMENTATION POLICY v1

**Status:** APPROVED

Финальный repository должен содержать:

- `README.md` — English, основной технический README;
- `README_RU.md` — полноценная русская версия.

В начале обоих: `English | Русский` с относительными ссылками.

`README_RU.md` создаётся на базе фактического `README.md`, актуального runtime и прошедших TEST результатов; он не должен быть свободным пересказом, расходящимся с English README.

Минимальные разделы README_RU:

СННИТ РАДАР (WSR); Что это; Архитектура; Требования; Быстрый запуск; CACHE/SNAPSHOT; LIVE; `.env`; Docker/PostgreSQL/migrations; UI; Методология; Источники и лимиты; Embedding; LLM; Snapshots; Логи и диагностика; Tests; Ограничения; Troubleshooting; IMPLEMENTED/PARTIAL/ROADMAP.

UI-методология должна быть человекочитаемой; README — техническим и воспроизводимым.

PASS если EN/RU README не противоречат друг другу, команды реально работают, ссылки рабочие, secrets отсутствуют, статусы IMPLEMENTED/PARTIAL/ROADMAP честны.
