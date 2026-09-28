# 04 — Pipeline и state machine

## Основной поток

```text
1. User Query
2. Normalize Query
3. CACHE available?
   YES -> local corpus
   NO  -> explicit LIVE refresh or no-local-corpus state
4. Source acquisition per enabled adapter
5. Source Document Registry
6. Candidate extraction
7. Alias / synonym / semantic-equivalence resolution
8. Candidate Registry
9. technology × year
10. Feature A/B/C/D/E
11. Percentiles
12. Data Sufficiency Gate
13. Weak-signal heuristic filters
14. Score
15. Ranking
16. Result Registries
17. Technology Card
```

## Source document states

`FOUND`, `NOT_FOUND_IN_SOURCE`, `PARTIAL`, `SEARCH_ERROR`, `BLOCKED_ACCESS`, `BLOCKED_COST`, `NOT_RUN`.

`NOT_FOUND_IN_SOURCE` допустим только после успешно выполненного bounded query. Ошибка/лимит → `PARTIAL/UNKNOWN`, не отсутствие.

## Candidate lifecycle

`DISCOVERED → NORMALIZED → SCORABLE → QUALIFIED → RANKED`

Side states:
- `INSUFFICIENT`
- `REJECTED_BY_HEURISTIC_FILTER`
- `AMBIGUOUS`
- `SEMANTIC_EQUIVALENT_TO_EXISTING`

## Final registries

- `TOP15`
- `RANKED_BELOW_15`
- `CANDIDATES`
- `REJECTED`
- `UNKNOWN_INSUFFICIENT`

`Rejected ≠ Unknown ≠ rank 16+`.

> СННИТ РАДАР (WSR)
