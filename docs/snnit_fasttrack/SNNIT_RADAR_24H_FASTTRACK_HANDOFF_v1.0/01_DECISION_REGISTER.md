# 01 — Реестр закрытых решений

| ID | Решение | Статус |
|---|---|---|
| D-001 | Продукт: **СННИТ РАДАР** — «радар сигнала новой научно-исследовательской технологии» | CLOSED |
| D-002 | Имя существующего git-репозитория не менять | CLOSED |
| D-003 | WSR — target architecture, не полный реализованный runtime | CLOSED |
| D-004 | До Candidate Registry есть отдельный Source Document Registry | CLOSED |
| D-005 | Оригинальные PDF/full text не храним; храним stable ID, URL, metadata, availability status, provenance; bounded raw API snapshots разрешены | CLOSED |
| D-006 | Каноническая feature model = A/B/C/D/E | CLOSED |
| D-007 | `Score = 0.30A + 0.20B + 0.25C + 0.15D + 0.10E` | CLOSED |
| D-008 | C: LLM извлекает technical signature; numeric C считается детерминированно через embeddings | CLOSED |
| D-009 | Новый рынок / применение ≠ новая технология | CLOSED |
| D-010 | D: deterministic confirmation subscore; FWCI — diagnostic only | CLOSED |
| D-011 | Data sufficiency failure → INSUFFICIENT, не REJECTED | CLOSED |
| D-012 | Weak-signal filters: share<P90; q<0.10; observed research age≤8 | CLOSED |
| D-013 | OpenAlex = REQUIRED_REFERENCE_SOURCE; CORDIS/EPO = REQUIRED_ATTEMPT / FAIL_SOFT | CLOSED |
| D-014 | Источники добавляются/убираются через SourceAdapter + config | CLOSED |
| D-015 | LLM заменяется через LLMAdapter + config | CLOSED |
| D-016 | CACHE = повторное использование локального корпуса без новых внешних source calls | CLOSED |
| D-017 | LIVE refresh = явный новый сбор, merge/dedup, новый snapshot, затем анализ | CLOSED |
| D-018 | Immutable snapshots не перезаписываются | CLOSED |
| D-019 | Bootstrap = `ON_DEMAND / NOT_P0_BLOCKER`; запускается отдельным запросом | CLOSED |
| D-020 | FWCI показывается пользователю как диагностическое поле при наличии | CLOSED |
| D-021 | UI — фирменная сине-белая палитра Газпрома, существующий shell переиспользуется | CLOSED |
| D-022 | Docker/local-first; localhost основной; public URL optional | CLOSED |
| D-023 | `.env` вне git; `.env.example` без секретов; optional key не мешает boot | CLOSED |
| D-024 | README — обязательный P0 acceptance artifact | CLOSED |

## PRECHECK должен только зафиксировать, а не решать продуктово

- точный `EMBEDDING_MODEL_ID` + revision;
- точный LLM provider/model или `DISABLED`;
- measured hardware/runtime;
- фактический статус adapters на машине;
- совместимость API routes с текущим Stage A.

> СННИТ РАДАР (WSR)
