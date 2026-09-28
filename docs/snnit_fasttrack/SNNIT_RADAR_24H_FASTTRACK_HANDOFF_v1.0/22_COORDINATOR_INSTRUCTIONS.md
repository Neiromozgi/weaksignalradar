# 22 — Coordinator Instructions

Coordinator owns:
- routing;
- completeness;
- versions/status;
- freeze discipline;
- gate reporting.

Coordinator does NOT:
- invent formulas;
- change thresholds/weights;
- override PO;
- silently broaden scope.

## Gates

- H0 PRECHECK
- H6 real documents + Candidate Registry
- H12 full browser vertical slice
- H18 enhancements only
- H20 FEATURE FREEZE
- H22 release candidate
- H24 tested ship

At each gate record:
- PASS;
- PARTIAL;
- BLOCKED;
- DEFERRED;
- active score profile;
- active source/model config.

Missing decision:
1. mark `BLOCKED_BY_DECISION`;
2. ask one concrete question;
3. continue independent work.

> СННИТ РАДАР (WSR)
