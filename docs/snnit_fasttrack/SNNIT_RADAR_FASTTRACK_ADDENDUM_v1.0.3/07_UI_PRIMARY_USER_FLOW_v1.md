# 07 — UI PRIMARY USER FLOW v1

**Project:** СННИТ РАДАР (WSR)  
**Decision ID:** `UI_PRIMARY_USER_FLOW_v1`  
**Addendum:** `SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.3`  
**Status:** `APPROVED / FROZEN FOR UI IMPLEMENTATION`

## 1. Брендинг

На всех экранах:

```text
СННИТ РАДАР (WSR)
Радар сигнала новой научно-исследовательской технологии
```

Палитра: синий + белый. Использовать текущую сине-белую / Gazprom-like оболочку.

## 2. Основной пользовательский путь

```text
Главная
→ запрос
→ обработка
→ TOP-15
→ Technology Card
→ назад к TOP-15 / на главную
```

Source Document Registry, Candidate Registry, все дополнительные реестры и Methodology обязательны, но являются вторым уровнем интерфейса.

## 3. Главная

Обязательные элементы:

```text
СННИТ РАДАР (WSR)
Радар сигнала новой научно-исследовательской технологии
```

Подсказка:

```text
Введите отрасль или технологическое направление,
в котором хотите найти ранние сигналы новых технологий
```

Кнопка:

```text
Найти ранние сигналы
```

Default mode: `LIVE`.

Выбор `LIVE / CACHE / SNAPSHOT` разместить как компактную дополнительную настройку, чтобы не перегружать главный экран.

## 4. Обработка

После запуска:

- spinner;
- введённый запрос;
- сообщение:

```text
Мы обрабатываем ваш запрос.
Анализ может занять несколько минут.
```

Не показывать неподтверждённое `до 20 минут`.

Можно показывать реальные backend stages, но нельзя показывать фиктивный progress percentage.

При ошибке:

```text
Повторить
Вернуться на главную
```

## 5. TOP-15

После успешного анализа по умолчанию:

```text
TOP-15 ранних сигналов новых технологий
```

Для каждой технологии минимум:

```text
rank
название
итоговый score
краткое «Почему это ранний сигнал»
A / B / C / D / E availability/values
```

Клик открывает Technology Card.

На экране:

```text
← Вернуться на главную
```

## 6. Technology Card

Показывает минимум:

- название;
- rank;
- итоговый score;
- mode = LIVE / CACHE / SNAPSHOT;
- run_id / snapshot_id где уместно;
- «Почему система считает эту технологию ранним сигналом»;
- A–E: raw, percentile, weight, contribution, availability/status;
- data sufficiency;
- passed/failed filters;
- reason codes;
- evidence;
- source;
- stable document ID;
- title;
- date;
- organization/author;
- original URL;
- availability status;
- provenance;
- uncertainty/limitations.

Не превращать `UNKNOWN` в 0.

Навигация:

```text
← Назад к TOP-15
← Вернуться на главную
```

## 7. Вторичный уровень

Доступны разделы:

```text
Все результаты
Документы
Кандидаты
Методология
```

### Все результаты

Раздельно:

```text
TOP-15
RANKED_BELOW_15
REJECTED
UNKNOWN / INSUFFICIENT
```

### Документы

Source Document Registry с source, type, stable ID, title, date/year, organization/author, original availability, URL, duplicate status, extraction status, extracted technologies, provenance.

### Кандидаты

Candidate Registry с candidate, aliases, stage, document count, organization count, source coverage, technical signature availability, final registry/status.

### Методология

Кратко показывать A–E, weights, score profile, data sufficiency, filters, embedding profile, source roles, runtime mode, limitations.

## 8. Навигация

На каждом внутреннем экране:

```text
← Вернуться на главную
```

На Technology Card также:

```text
← Назад к TOP-15
```

Browser Back не является единственным способом возврата.

## 9. Только реальные данные

UI использует фактический backend.

Запрещено выдавать за LIVE:
- hardcoded TOP-15;
- fixture;
- статическую Technology Card;
- фиктивные A–E;
- фиктивный provenance;
- фиктивный progress.

Fixture разрешён только с явной маркировкой `CACHE`, `SNAPSHOT`, `benchmark/demo dataset`.

## 10. UI states

Минимум:

```text
IDLE
RUNNING
COMPLETED
FAILED
PARTIAL
```

Для PARTIAL показывать недоступный source/component.

## 11. P0 acceptance

Пользователь должен без прямой работы с API:

1. открыть главную;
2. ввести отрасль/направление;
3. принять default mode или выбрать режим;
4. запустить анализ;
5. увидеть RUNNING state;
6. получить TOP-15;
7. открыть Technology Card;
8. увидеть A–E, причины, evidence и источники;
9. вернуться в TOP-15;
10. вернуться на главную;
11. открыть Все результаты / Документы / Кандидаты / Методологию;
12. отличить LIVE от CACHE/SNAPSHOT.

## 12. Non-goals P0

Не требуются:
- сложная анимация;
- декоративные графики;
- отдельная design system;
- мобильное приложение;
- неподтверждённый SLA/ETA;
- отдельная admin-панель.

Приоритет:

```text
functional correctness
→ transparency
→ navigation
→ clean blue-white presentation
→ visual polish
```
