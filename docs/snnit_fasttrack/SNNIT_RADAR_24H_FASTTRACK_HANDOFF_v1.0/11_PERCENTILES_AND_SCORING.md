# 11 — Percentiles & Scoring

## Reference population

For each feature:

`SCORABLE_CANDIDATES(domain_id, snapshot_id, feature_contract_version)`

Candidate is:
- resolved;
- deduplicated;
- same domain/snapshot;
- sufficiently observed for that feature;
- evaluated **before substantive weak-signal filters**.

Never calculate percentiles only among finalists.

## Mid-rank percentile

`P(x) = 100 * (average_rank(x) - 0.5) / N`

Ties use average rank.

A/B/C/D: higher raw → higher percentile.

E: inverse percentile of current share.

Quality flags:
- `N>=30` NORMAL
- `20–29` USABLE_WARNING
- `15–19` UNSTABLE
- `<15` TOO_SMALL_FOR_TOP15_UNIVERSE

Flags are operational warnings, not statistical laws.

## Canonical score

`score_profile_id = ABCDE_v1`

`Score = 0.30*A + 0.20*B + 0.25*C + 0.15*D + 0.10*E`

Interpretation:
- relative-domain ranking heuristic;
- not probability;
- not calibrated confidence;
- weights are versioned start coefficients.

## Whole-run degraded profiles

If one feature is unavailable for **the whole run**, a separate profile may be explicitly enabled:

`Score_M = sum(w_i * P_i) / sum(w_i)` over active features.

Rules:
- global per run only;
- new `score_profile_id`;
- different profiles are not silently comparable;
- candidate-specific missing does not trigger renormalization.

## Reproducibility key

Store:
- domain_id
- snapshot_id
- candidate_universe_version
- feature_contract_version
- score_profile_id
- embedding_model_id

> СННИТ РАДАР (WSR)
