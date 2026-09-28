# 16 — CACHE, LIVE refresh, SNAPSHOT

## CACHE — простое определение

CACHE означает:

> система уже ранее получила данные от источников и сохранила локальный corpus/snapshot; повторный анализ использует эти данные и не делает новые внешние source calls.

CACHE — не заранее зашитый TOP-15.

При CACHE:
- external source calls = 0 по умолчанию;
- candidate formation/features/filters/ranking могут пересчитываться;
- используется существующий corpus/snapshot.

## LIVE refresh

LIVE refresh — отдельная явная операция:

`external APIs → new records → normalize → stable-ID dedup → compare/merge → new immutable snapshot → update local corpus → analysis`

LIVE refresh расходует API budget.

Повторный одинаковый query сам по себе не обязан обновлять источники.

## SNAPSHOT

SNAPSHOT — immutable bounded набор реальных source API responses + metadata/hash.

Snapshot:
- не подменяет алгоритм готовым ответом;
- тот же pipeline заново вычисляет candidates/features/ranking;
- versioned;
- старая версия не перезаписывается.

## Originals

Baseline:
- оригинальные PDF/full-text files **не сохраняем**;
- сохраняем canonical URL, stable ID, availability status, metadata;
- bounded raw API response snapshots сохраняются для replay/provenance;
- derived signature/metrics сохраняются.

> СННИТ РАДАР (WSR)
