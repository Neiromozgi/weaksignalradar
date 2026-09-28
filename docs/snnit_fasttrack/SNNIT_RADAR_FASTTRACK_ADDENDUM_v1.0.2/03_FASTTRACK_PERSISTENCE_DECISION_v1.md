# 03 — FASTTRACK PERSISTENCE DECISION v1

**Project:** СННИТ РАДАР  
**Decision ID:** `FASTTRACK_PERSISTENCE_v1`  
**Addendum:** `SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.2`  
**Status:** `APPROVED / FROZEN FOR DEV PASS #2`

## 1. Решение

FastTrack использует отдельный persistence layer в PostgreSQL.

Stage A `search_runs` не расширяется и не переопределяется для нового FastTrack state.

FastTrack runtime использует отдельные сущности / таблицы с префиксом:

```text
ft_*
```

Уже созданная `ft_analysis_runs` должна быть подключена к реальному FastTrack API и перестать быть schema-only артефактом.

## 2. Authoritative storage

In-memory `RunStore` допускается только как:
- transient runtime abstraction;
- cache;
- тестовая реализация.

In-memory `RunStore` НЕ является authoritative persistence.

После restart backend/container сохранённый FastTrack run должен оставаться доступным через API.

## 3. Минимальные persistent entities до независимого TEST

P0 persistence должен покрывать минимум:

```text
ft_analysis_runs
ft_source_documents
ft_candidates
ft_candidate_results
ft_snapshots
ft_source_runs
```

Допускается эквивалентная компактная схема, если она сохраняет все перечисленные ниже данные и не меняет frozen methodology.

### 3.1. Analysis run

Хранить минимум:

```text
run_id
domain_id / normalized_query
mode = LIVE | CACHE | SNAPSHOT
status
created_at
completed_at
snapshot_id
score_profile_id
embedding_profile_id
feature_contract_version
source_coverage
warnings
limitations
error
```

### 3.2. Source Document Registry

Для каждого найденного документа хранить минимум:

```text
run_id / snapshot_id
source
document_type
stable_source_id
title
publication_date / year
organization / authors if available
original_url
original_availability_status
duplicate_status
extraction_status
extracted_technologies
provenance
```

Не требуется сохранять локальную библиотеку оригинальных PDF/full text.

По умолчанию сохраняются stable IDs, metadata, links, availability status и bounded raw/source snapshots для reproducibility.

### 3.3. Candidate Registry

Хранить минимум:

```text
candidate_id
run_id
normalized_name
aliases
stage
technical_signature
evidence references
document counts
organization counts
source coverage
```

### 3.4. A–E / scoring / result state

Для кандидата хранить минимум:

```text
A_raw / A_percentile
B_raw / B_percentile
C_raw / C_percentile
D_raw / D_percentile
E_raw / E_percentile
weights
contributions
total_score
data_sufficiency_status
filter_results
final_registry
reason_codes
rank
```

Допускается использовать обычные колонки + JSONB для detail/provenance полей.

### 3.5. Snapshot metadata

Хранить связь run ↔ snapshot минимум через:

```text
snapshot_id
created_at
mode
source_set
path / storage reference
hash
document_count
parent_snapshot_id if applicable
```

Сам bounded raw snapshot может храниться в filesystem.

### 3.6. Source execution / coverage

Для каждого source attempt хранить минимум:

```text
source
execution_status
external_calls
records_received
cap_reached
error / timeout / rate_limit
started_at
completed_at
```

Различать:

```text
SEARCHED_OK + 0 records
PARTIAL
ERROR
RATE_LIMITED
NOT_RUN
```

Недоступность источника не превращается в ложный `NOT_FOUND`.

## 4. Persistence acceptance test

До передачи независимому TEST должно быть доказано:

```text
POST /api/v1/analyses
→ получить run_id
→ завершить run
→ restart backend/container
→ GET run по тому же run_id
→ run всё ещё доступен
```

После restart должны восстанавливаться минимум:
- analysis metadata;
- Source Document Registry;
- Candidate Registry;
- A–E / scoring / registry result;
- snapshot linkage;
- source coverage/provenance.

Если после restart run исчезает, persistence P0 не принят.

## 5. Stage A protection

Stage A baseline и его существующие таблицы не переписываются задним числом.

FastTrack migration должна быть additive и совместимой с текущей Alembic history.
