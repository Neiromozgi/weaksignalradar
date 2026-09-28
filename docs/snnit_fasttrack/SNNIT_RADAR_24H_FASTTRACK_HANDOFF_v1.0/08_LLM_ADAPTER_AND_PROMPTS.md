# 08 — LLM Adapter & Prompt Contract

LLM — заменяемый extraction component, **не ranker и не судья новизны**.

## Configurable

- `provider`
- `model`
- `base_url`
- `api_key_env`
- `structured_output_mode`
- `timeout`
- `max_retries`

App должен стартовать без optional LLM key и честно показывать `LLM_DISABLED`.

## Requirements

- instruction following;
- structured JSON / deterministic parseable output;
- configured context/chunk support;
- lowest practical randomness;
- stable model ID;
- prompt version logged;
- no silent external browsing/tools.

## Canonical C extraction

```json
{
  "object_class": null,
  "function": null,
  "mechanism": null,
  "architecture_or_process": null,
  "key_technical_property": null,
  "evidence_span_refs": [],
  "status": "OK|PARTIAL|UNKNOWN"
}
```

Rules:
- only supplied source content;
- no guessing missing mechanism/property;
- new market/application is not novelty;
- aliases normalized;
- ambiguity → UNKNOWN/PARTIAL;
- never output numeric novelty score.

## D support

LLM may normalize organization names, roles, reference mentions and evidence type. Structured source IDs override LLM guesses.

## Prompt bundle IDs

- `TECH_SIGNATURE_EXTRACT_v1`
- `ORG_NORMALIZE_v1`
- `REFERENCE_RECURRENCE_EXTRACT_v1`
- `EXPLANATION_RENDER_v1`

Explanation may verbalize only already-computed facts.

> СННИТ РАДАР (WSR)
