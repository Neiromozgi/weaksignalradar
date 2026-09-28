# 24 — 24H Gantt / responsibilities

| Time | Owner | Output |
|---|---|---|
| H0–H1 | PRECHECK | environment/source/model/contract report |
| H1–H4 | DEV Core | Source Document Registry + cache/snapshot + source normalization |
| H2–H5 parallel | DEV/UI + Genspark | API-ready screens, no hardcoded ranking |
| H3–H6 | DEV Core | candidate discovery + Candidate Registry |
| H6 Gate | Coordinator + TEST | real candidates confirmed |
| H6–H9 | DEV Core | technology×year + A/B/E + percentile foundation |
| H7–H10 | DEV Core | C signature extraction + embeddings |
| H7–H10 | DEV Core | D confirmation + FWCI diagnostic |
| H9–H11 | DEV Core | sufficiency + filters + scoring |
| H9–H12 | DEV API/UI | endpoints + real UI binding |
| H12 Gate | Coordinator + TEST | query→documents→candidates→A–E→ranking→UI |
| H12–H16 | DEV | source hardening, explanation, registries/cards |
| H12–H18 | TEST | regression/failure/replay |
| H16–H18 | DEV optional | P1 diagnostics; bootstrap plumbing only if core green |
| H18 | Coordinator | no new core subsystems |
| H18–H20 | DEV+TEST | bugs/performance/README |
| H20 | Coordinator | FEATURE FREEZE |
| H20–H22 | DEV+TEST | run.ps1 + jury reproduction |
| H22 | Coordinator | release candidate |
| H22–H24 | User+TEST | rehearsal/final verification |

Critical path = working reproducible end-to-end, not bootstrap.

> СННИТ РАДАР (WSR)
