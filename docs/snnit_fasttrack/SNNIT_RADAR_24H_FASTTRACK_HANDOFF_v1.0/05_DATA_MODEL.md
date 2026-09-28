# 05 — Data Model

## analysis_run

- `run_id`
- `normalized_query`
- `domain_id`
- `started_at`, `finished_at`
- `data_mode`: CACHE/LIVE/SNAPSHOT
- `snapshot_id`
- `candidate_universe_version`
- `feature_contract_version`
- `score_profile_id`
- `embedding_model_id`
- `llm_model_id`
- `status`
- `coverage_summary`

## source_document

Храним **metadata/reference**, не оригинальный PDF/full text.

- `source_document_id`
- `source_id`
- `source_type`
- `stable_external_id`
- `doi` nullable
- `title`
- `year/date`
- `canonical_url`
- `original_availability_status`
- `original_stored = false`
- `metadata_json`
- `source_snapshot_id`
- `retrieved_at`
- `content_hash_of_api_record`
- `coverage_state`

`original_availability_status`:
- `FULL_TEXT_AVAILABLE_BY_LINK`
- `ABSTRACT_AVAILABLE`
- `METADATA_ONLY`
- `LINK_ONLY`
- `ACCESS_RESTRICTED`
- `UNAVAILABLE`
- `UNKNOWN`

### Storage rule

Не сохранять оригинальные PDF/full-text как baseline.

Разрешено:
- IDs;
- URL;
- metadata;
- source-provided abstract/fields из bounded API response;
- derived extraction;
- bounded raw API response snapshots для replay/provenance.

## candidate_technology

- `candidate_id`
- `canonical_name`
- `name_ru`, `name_en`
- `aliases[]`
- `domain_id`
- `state`
- `ambiguity_status`
- `equivalent_to_candidate_id` nullable
- `first_observed_year`
- `document_count`
- `organization_count`
- `source_class_count`

## candidate_document_link

- `candidate_id`
- `source_document_id`
- `relation`
- `mention_confidence`
- `evidence_ref`

## candidate_year_stat

- `candidate_id`
- `year`
- `candidate_doc_count`
- `domain_doc_count`
- `share`
- `organization_count`

## technical_signature

- `candidate_id`
- `object_class`
- `function`
- `mechanism`
- `architecture_or_process`
- `key_technical_property`
- `evidence_span_refs[]`
- `extraction_status`
- `llm_model_id`
- `prompt_version`

## feature_value

- `candidate_id`
- `feature_code` A/B/C/D/E
- `raw_value`
- `percentile`
- `availability`
- `method_version`
- `diagnostics_json`

D diagnostics:
- `lineage_count`
- `independent_org_count`
- `source_class_count`
- `reference_recurrence`
- `fwci` nullable **diagnostic only**

## filter_result

- `candidate_id`
- `filter_code`
- `raw_value`
- `threshold`
- `passed`
- `failure_class`: INSUFFICIENT / HEURISTIC_REJECT
- `reason_code`

## ranking_result

- `candidate_id`
- `score`
- `rank`
- `score_profile_id`
- `contributions_json`
- `ranking_status`

## bootstrap_result

Optional/on-demand:
- `bootstrap_request_id`
- `run_id`
- `candidate_id`
- `status`: NOT_REQUESTED / QUEUED / RUNNING / COMPLETED / FAILED
- `method_version`
- `interval_low`, `interval_high`
- timestamps

> СННИТ РАДАР (WSR)
