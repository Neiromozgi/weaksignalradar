# 15 — Official Genspark UI Prompt

Создай web UI аналитического сервиса **«СННИТ РАДАР»** в спокойной фирменной сине-белой палитре Газпрома. Не делай маркетинговый лендинг. Сохрани существующий visual shell, где возможно.

Нужны экраны:

1. **Поиск**
   - запрос отрасли/технологического домена;
   - дата локального корпуса;
   - число документов;
   - режим CACHE/LIVE/SNAPSHOT;
   - «Запустить анализ»;
   - «Обновить данные из источников».

2. **Найденные документы**
   Таблица:
   source, source type, stable ID, title, year/date, organization, original availability status, external original link, snapshot, extraction status, candidate mentions.
   Не показывай, будто оригинальные PDF хранятся локально.

3. **Реестр кандидатов**
   candidate ID, technology, stage/state, docs, independent orgs, source classes, A/B/C/D/E, FWCI diagnostic, sufficiency.

4. **Результаты**
   TOP-15 / Ниже TOP-15 / Rejected / Unknown-Insufficient.

5. **Карточка технологии**
   A–E raw/percentile/weights/contributions, filters, data sufficiency, real share-by-year chart, evidence links, original availability, provenance, coverage, C signature, D confirmation, FWCI diagnostic.
   Bootstrap показывается отдельно: до запуска «Интервал не рассчитан».

6. **Методология**
   Runtime formulas/method versions должны приходить из backend API.

Требования:
- никакого hardcoded TOP-15 на competition route;
- API service layer;
- no ranking in JS;
- explicit loading/error/partial/unknown;
- REJECTED визуально отличается от INSUFFICIENT;
- новый рынок не показывается как novelty;
- external links явные;
- фирменные цвета Газпрома; логотип не использовать без отдельного разрешения;
- подпись: «СННИТ РАДАР (WSR)».

> СННИТ РАДАР (WSR)
