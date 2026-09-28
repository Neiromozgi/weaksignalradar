# 12 — Sufficiency, Filters, Registries

## A. Data Sufficiency Gate

Not substantive rejection.

Required:
1. `deduplicated OpenAlex Works >= 10` inside analysis window;
2. `independent normalized organizations >= 3`;
3. sufficient temporal history;
4. required canonical features available.

Failure → `UNKNOWN / INSUFFICIENT_INFORMATION`.

Document count = stable deduplicated works, not URLs.

Organization count = normalized top-level identity; aliases/parents collapsed.

## B. Weak-signal heuristic filters

### Current share < P90
OpenAlex reference corpus only.

Failure → `REJECTED_BY_HEURISTIC_FILTER: MAINSTREAM_SHARE`.

### q < 0.10 for positive trend
Use one-sided Mann–Kendall on yearly domain share; Benjamini–Hochberg FDR across candidates in same frozen run.

`q < 0.10` does **not** mean 90% probability of weak signal.

Insufficient history → `INSUFFICIENT`.

### Observed research age <= 8

`observed_age = current_year - first_observed_OpenAlex_year + 1`

If first observation is left-censored/coverage partial → `age=UNKNOWN`.

Failure → `REJECTED_BY_HEURISTIC_FILTER: AGE`.

## Registries

- `CANDIDATES`
- `TOP15`
- `RANKED_BELOW_15`
- `REJECTED`
- `UNKNOWN_INSUFFICIENT`

`Rejected ≠ Unknown ≠ rank 16+`.

## Noise

Possible noise:
- irrelevant/out-of-domain;
- duplicate/equivalent rename;
- extraction artefact;
- unsupported observation.

Insufficient evidence is not automatically noise.

> СННИТ РАДАР (WSR)
