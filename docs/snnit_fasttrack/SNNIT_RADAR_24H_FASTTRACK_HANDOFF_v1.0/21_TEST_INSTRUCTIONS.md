# 21 — Cursor TEST Instructions

TEST validates against this package and does not rewrite methodology.

## Source / coverage
- stable-ID dedup;
- timeout → PARTIAL/UNKNOWN;
- cap → PARTIAL;
- disabled optional source → boot;
- missing optional key → boot.

## Cache / LIVE
- identical CACHE analysis makes no external calls;
- LIVE refresh creates new snapshot;
- old snapshot immutable;
- merge no duplicate source records.

## Documents
- Source Document Registry exposes original availability + external link;
- original full file not persisted by baseline code path.

## Candidate discovery
- aliases merge;
- ambiguous → split/UNKNOWN;
- rename-only equivalence guard works.

## Features
- A/B/C/D/E deterministic on fixed snapshot/config;
- C = LLM signature + embedding, not LLM score;
- FWCI visible diagnostic, no D_v1 effect;
- missing feature != 0.

## Percentiles
- same universe/snapshot → same percentile;
- ties average rank;
- finalist-only percentile prohibited.

## Gates
- <10 docs → INSUFFICIENT;
- <3 independent orgs → INSUFFICIENT;
- share≥P90 → REJECTED MAINSTREAM;
- q≥0.10 → REJECTED NO_SIGNIFICANT_TREND;
- age>8 → REJECTED AGE;
- UNKNOWN != REJECTED.

## Ranking
- exact active score formula;
- TOP15 subset of qualified ranking;
- rank16+ remains below15;
- profile labelled.

## UI/API
- real API;
- document registry;
- candidate registry;
- technology card source links/status;
- no fake interval;
- Gazprom-blue shell.

## Reproducibility
fixed snapshot + config + model IDs → same result within declared deterministic tolerance.

## P1 if time
- Spearman A–E matrix;
- TOP-15 sensitivity ±10–20% weights.

> СННИТ РАДАР (WSR)
