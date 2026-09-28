# СННИТ РАДАР (WSR) — 24H FastTrack Handoff v1.0

**Назначение:** единый version-locked контракт для `PRECHECK → DEV → TEST` в Cursor.

**Продукт:** **СННИТ РАДАР** — «радар сигнала новой научно-исследовательской технологии».

**WSR / WeakSignalRadar:** целевая расширенная архитектура после хакатона. Текущий runtime не должен выдавать полный WSR B0/B за реализованный.

## Читать в таком порядке

1. `00_READ_FIRST.md`
2. `01_DECISION_REGISTER.md`
3. `02_PRODUCT_SCOPE.md`
4. `03_ARCHITECTURE.md`
5. `04_PIPELINE_AND_STATE_MACHINE.md`
6. `05_DATA_MODEL.md`
7. `06_SOURCE_ADAPTER_CONTRACT.md`
8. `07_SOURCE_USAGE_BUDGET.md`
9. `08_LLM_ADAPTER_AND_PROMPTS.md`
10. `09_CANDIDATE_DISCOVERY.md`
11. `10_FEATURES_A_E.md`
12. `11_PERCENTILES_AND_SCORING.md`
13. `12_FILTERS_AND_REGISTRIES.md`
14. `13_API_CONTRACT.md`
15. `14_UI_CONTRACT.md`
16. `15_GENSPARK_UI_PROMPT.md`
17. `16_CACHE_LIVE_SNAPSHOT.md`
18. `17_BOOTSTRAP_ON_DEMAND.md`
19. `18_DEPLOYMENT_README_REQUIREMENTS.md`
20. `19_PRECHECK_INSTRUCTIONS.md`
21. `20_DEV_INSTRUCTIONS.md`
22. `21_TEST_INSTRUCTIONS.md`
23. `22_COORDINATOR_INSTRUCTIONS.md`
24. `23_ACCEPTANCE_CRITERIA.md`
25. `24_24H_GANTT.md`
26. `25_REPOSITORY_STRUCTURE.md`
27. `26_OPERATIONS_COMMANDS.md`
28. `27_PERFORMANCE_AND_HARDWARE.md`
29. `28_IMPLEMENTED_PARTIAL_TARGET.md`
30. `29_VERSION_MANIFEST.md`
31. `30_SOURCE_BASIS.md`
32. `31_CURSOR_START_HERE.md`
33. `prompts/PRECHECK_PROMPT.md`, `DEV_PROMPT.md`, `TEST_PROMPT.md`, `COORDINATOR_PROMPT.md`

## Абсолютные правила

- Не менять принятый алгоритм молча.
- Не считать ranking на frontend.
- Не хранить оригинальные PDF/full-text документы как базовый контракт.
- Не путать `UNKNOWN / INSUFFICIENT` с `REJECTED`.
- Недоступность источника/квота не означает отсутствие технологии.
- Канонический профиль — A/B/C/D/E.
- Новый рынок или область применения сами по себе не являются новой технологией.
- Источники и LLM подключаются через adapter + config.
- Повторный анализ использует CACHE; LIVE refresh выполняется только явно.
- Bootstrap — отдельный запрос, не P0 blocker.
- README продукта — обязательный P0 deliverable.

> СННИТ РАДАР (WSR)
