# 29 — Version Manifest

Fill/update during PRECHECK/release.

```yaml
product_name: "СННИТ РАДАР"
product_definition: "радар сигнала новой научно-исследовательской технологии"
handoff_version: "1.0"
repo_name: "<DO_NOT_RENAME_EXISTING>"
repo_commit: "<PRECHECK_FILL>"
stage_a_baseline_commit: "81fe888245b6f6d6c398d865e6000674bdc34874"

feature_contract: "ABCDE_v1"
score_profile: "ABCDE_v1"
percentile_contract: "MIDRANK_DOMAIN_SNAPSHOT_v1"
sufficiency_contract: "SUFFICIENCY_v1"
filter_contract: "WEAK_SIGNAL_FILTERS_v1"
c_contract: "C_NOVELTY_v1"
d_contract: "D_CONFIRMATION_v1"
prompt_bundle: "SNNIT_FASTTRACK_PROMPTS_v1"

embedding_model_id: "<PRECHECK_PIN>"
embedding_model_revision: "<PRECHECK_PIN>"
llm_provider: "<PRECHECK_FILL_OR_DISABLED>"
llm_model_id: "<PRECHECK_FILL_OR_DISABLED>"

sources:
  openalex: "REQUIRED_REFERENCE_SOURCE"
  cordis: "REQUIRED_ATTEMPT_FAIL_SOFT"
  epo_lod: "REQUIRED_ATTEMPT_FAIL_SOFT"

bootstrap:
  status: "ON_DEMAND_NOT_P0_BLOCKER"
  method_version: "<UNSET_UNTIL_IMPLEMENTED>"
```

> СННИТ РАДАР (WSR)
