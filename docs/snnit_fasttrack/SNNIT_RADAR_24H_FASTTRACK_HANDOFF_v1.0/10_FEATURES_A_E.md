# 10 — Feature Contract A–E

Canonical profile: `ABCDE_v1`.

## A — Рост доли (Growth Share)

Reference corpus: OpenAlex.

For candidate `c`, year `t`:

`share(c,t) = deduplicated_works(c,t) / deduplicated_domain_works(t)`

Fit Poisson/log-link trend on candidate yearly counts with `log(domain_count_t)` as offset over configured window.

`A_raw = exp(beta_year)` — multiplicative annual change factor.

Higher `A_raw` = stronger relative growth.

Insufficient history → `A=UNKNOWN`.

## B — Ускорение (Acceleration)

Use domain share time series.

`g_recent = [ln(share_t + eps) - ln(share_{t-2}+eps)] / 2`

`g_prev = [ln(share_{t-2}+eps) - ln(share_{t-4}+eps)] / 2`

`B_raw = g_recent - g_prev`

`eps` is fixed/versioned in runtime config and recorded in manifest.

Higher B_raw = accelerating growth.

## C — Новизна содержания (Content Novelty)

LLM extracts technical signature only:
- object_class — 10%
- function — 20%
- mechanism — 35%
- architecture_or_process — 20%
- key_technical_property — 15%

For candidate `c` and historical analogue `h`:

`sim(c,h) = 0.10*s_object + 0.20*s_function + 0.35*s_mechanism + 0.20*s_architecture + 0.15*s_property`

Each `s` = cosine similarity using one pinned embedding model.

`sim_max = max_h sim(c,h)`

`C_raw = 100 * (1 - sim_max)`

Then `C_raw → percentile C`.

Rules:
- market/application is not novelty facet;
- missing mechanism/property is not guessed;
- equivalence guard can flag rename/equivalent;
- model/version/preprocessing frozen per run.

## D — Независимое подтверждение (Confirmation)

FWCI is **diagnostic only** in v1.

Let:
- `L` = independent evidence lineages;
- `O` = independent normalized top-level organizations;
- `S` = positively observed source classes among OpenAlex/CORDIS/EPO (0..3);
- `R` = reference recurrence: 0=no recurrence; 0.5 = recurrence >0 and ≤50%; 1 = recurrence >50%.

Normalize:
`L_n = min(ln(1+L)/ln(6), 1)`
`O_n = min(ln(1+O)/ln(6), 1)`
`S_n = S/3`

`D_raw = 100 * (0.35*L_n + 0.30*O_n + 0.25*S_n + 0.10*R)`

Then `D_raw → percentile D`.

Independent organization = distinct normalized top-level organization after alias/parent collapse.

Reference recurrence uses stable IDs: DOI, patent/publication ID, project ID. Reposts/copies from same lineage do not create independent evidence.

### FWCI

If available:
- persist as diagnostic;
- display on Candidate Registry/Technology Card;
- do not modify D_v1.

## E — Слабость (Weakness)

`share_current` = current OpenAlex candidate share.

`E = 100 - percentile(share_current)`

Lower current share → higher E.

## Missing

Candidate-specific missing:
- not 0;
- not median;
- no personal weight redistribution;
- canonical comparable ranking → `INSUFFICIENT` unless an explicitly separate partial registry is introduced.

> СННИТ РАДАР (WSR)
