# 07 — Source Usage Budget

## Frozen per-run caps

| Source | Calls/run | Record cap | Timing |
|---|---:|---:|---|
| OpenAlex | 15 | 500 normal Work records before candidate extraction | 15s normal / 20s semantic; hard cutoff 90s |
| CORDIS/EURIO | 8 bounded SPARQL requests | 250 bindings/projects | 20–30s/query; hard cutoff 120s |
| EPO Linked Open Data | 12 | 300 raw bindings total; ≤50 discovery family observations downstream | 25s/call; hard cutoff 90s |

Combined ceiling: **35 external calls/run**.

OpenAlex engineering cost ceiling under frozen cap: **≤ $0.015/run**.

## DEV / jury reserve

### OpenAlex
- up to 3 controlled DEV full live-runs before review;
- protect 3 full runs for jury/acceptance;
- if remaining provider budget approaches reserve → `SNAPSHOT_ONLY` for DEV.

### CORDIS / EPO
- prefer ≤2 DEV live-runs each after adapter stability;
- preserve ≥2 bounded jury/acceptance attempts where applicable;
- repeated tests use snapshots.

Operational guard, not methodology.

## Cache-first

`1 bounded live acquisition → immutable snapshot → many replay tests`.

## Failure semantics

- cap reached → `PARTIAL`;
- timeout/429/5xx after retry → `SEARCH_ERROR/PARTIAL`;
- disabled → `NOT_RUN`;
- quota affects **coverage, not truth**.

> СННИТ РАДАР (WSR)
