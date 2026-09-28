# 06 — Source Adapter Contract

## Conceptual interface

```python
class SourceAdapter:
    source_id: str
    source_class: str
    capabilities: set[str]

    def health(self) -> SourceHealth: ...
    def search(self, query, budget, cursor=None) -> SourceBatch: ...
    def normalize(self, raw_record) -> NormalizedSourceDocument: ...
    def stable_id(self, raw_record) -> str: ...
```

## NormalizedSourceDocument

Provide where available:
- stable external ID;
- source class;
- title;
- date/year;
- canonical URL;
- organization IDs/names;
- abstract/metadata;
- original availability;
- provenance;
- coverage state.

## Current roles

### OpenAlex
`REQUIRED_REFERENCE_SOURCE`

Reference corpus for A/B/E, historical corpus for C, discovery foundation, organization IDs.

### CORDIS/EURIO
`REQUIRED_ATTEMPT / FAIL_SOFT`

Independent project/grant evidence and D confirmation.

### EPO Linked Open Data
`REQUIRED_ATTEMPT / FAIL_SOFT`

Patent/IP evidence, family/publication IDs/classifications and D confirmation.

If CORDIS/EPO fail: app continues with `coverage=PARTIAL`.

## New source acceptance

A source may be added only if:
1. stable identity strategy exists;
2. access/terms permit intended use;
3. mapping to normalized schema exists;
4. source role is declared;
5. resource budget is set;
6. adapter contract tests pass.

Source addition must not silently modify A–E formulas.

> СННИТ РАДАР (WSR)
