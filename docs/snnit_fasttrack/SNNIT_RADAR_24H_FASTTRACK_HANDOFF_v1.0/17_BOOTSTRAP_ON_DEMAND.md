# 17 — Bootstrap — отдельный запрос

## Status

`ON_DEMAND / NOT_P0_BLOCKER / NOT_RUN_BY_DEFAULT`

Bootstrap остаётся в документации/архитектуре, но:
- не блокирует end-to-end;
- не выполняется автоматически;
- не показывает выдуманный interval;
- запускается отдельной API-командой/кнопкой.

UI:
- `NOT REQUESTED`
- `RUNNING`
- `COMPLETED: [low, high]`
- `FAILED`

## Interpretation

Bootstrap interval отражает чувствительность score/rank к конкретной resampling procedure. Это не вероятность того, что технология является слабым сигналом.

## До реализации

Отдельно зафиксировать:
- unit of resampling;
- number of replicates;
- seed policy;
- stages recalculated;
- interval statistic.

Пока это не зафиксировано и не протестировано: `DESIGNED / ON_DEMAND`.

> СННИТ РАДАР (WSR)
