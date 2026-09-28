# 14 — UI Contract

## Visual system

- reuse existing frontend shell;
- фирменная сине-белая палитра Газпрома;
- analytical product, not marketing landing;
- no decorative/fake metrics;
- frontend never computes ranking.

## Screen 1 — Search

Show:
- query field;
- local corpus date;
- local source-record count;
- data mode;
- buttons:
  - `Запустить анализ`
  - `Обновить данные из источников`

## Screen 2 — Найденные документы / Source Document Registry

Mandatory.

Columns:
- Source
- Type
- Stable ID
- Title
- Date/year
- Organization
- **Original availability**
- Canonical link
- Snapshot
- Extraction state
- Candidate mentions

Do not imply that original file is stored locally.

## Screen 3 — Candidate Registry

Columns:
- candidate ID;
- technology;
- lifecycle state;
- document count;
- independent organization count;
- source classes;
- A/B/C/D/E raw + percentile;
- FWCI diagnostic;
- sufficiency;
- comment/reason.

## Screen 4 — Result registries

Tabs:
- TOP-15
- Ranked below 15
- Rejected
- Unknown / Insufficient

## Screen 5 — Technology Card

Show:
- name/aliases;
- rank/score/profile;
- A–E raw;
- A–E percentile;
- weights/contribution;
- sufficiency results;
- heuristic filters;
- real share-by-year chart;
- C technical signature + nearest historical analogue;
- D confirmation diagnostics;
- FWCI diagnostic if available;
- source documents + original availability + external links;
- source coverage;
- data mode/snapshot;
- deterministic explanation;
- bootstrap section: `NOT REQUESTED / REQUEST / RESULT`.

## Status wording

Do not use “перспективная” as a separate scientific status.

Factual states are:
`TOP15`, `RANKED_BELOW_15`, `REJECTED`, `UNKNOWN/INSUFFICIENT`, plus candidate lifecycle states.

> СННИТ РАДАР (WSR)
