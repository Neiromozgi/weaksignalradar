# 09 — Candidate Discovery Contract

## Input

Normalized domain query + Source Document Registry.

## Stages

1. semantic domain expansion;
2. phrase/key concept extraction;
3. embeddings;
4. clustering/grouping;
5. candidate naming;
6. alias/synonym merge;
7. semantic-equivalence guard;
8. stable candidate ID;
9. links back to source documents.

## Mandatory separation

`Source Document Registry` exists **before** candidate formation.

User must be able to inspect what real source records were found:
- source;
- stable ID;
- title/date;
- canonical URL;
- original availability;
- snapshot/provenance.

## Alias / equivalence

High embedding similarity proposes a merge; final merge additionally checks:
- same object class;
- same mechanism/function at substantive level;
- no new key technical property.

Rule “>50% facets match” is an **equivalence guard**, not C formula. If majority of essential facets match and mechanism/property do not show substantive difference → `POSSIBLE_RENAME_OR_EQUIVALENT`.

## Ambiguity

If a term denotes multiple technical objects:
- split where context supports it;
- otherwise `AMBIGUOUS / UNKNOWN`.

## Implementation flexibility

Product requirement = semantic candidate discovery, not a sacred library.

Preferred chain:
`keyphrase extraction + multilingual embeddings + clustering`.

Fallback:
`embedding clustering → source taxonomy/topics + normalized keyphrases`.

Record the fallback/method in run metadata.

> СННИТ РАДАР (WSR)
