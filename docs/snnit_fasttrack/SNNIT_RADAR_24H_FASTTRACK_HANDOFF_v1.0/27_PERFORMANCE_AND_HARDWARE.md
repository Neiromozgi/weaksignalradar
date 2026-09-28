# 27 — Performance & Hardware

## Performance truth policy

Only:
- `MEASURED`
- `TARGET`
- `NOT_MEASURED`

No invented UI timings.

Existing source-acquisition engineering envelopes:
- OpenAlex expected 10–30s; hard 90s;
- CORDIS expected 10–30s; hard 120s;
- EPO LOD expected 20–45s; hard 90s.

These are source-acquisition envelopes, not full-service latency.

## Measure in PRECHECK/TEST

- cold Docker start;
- warm start;
- CACHE analysis;
- LIVE acquisition;
- candidate formation;
- A–E;
- API serialization;
- first UI result;
- peak RAM/CPU;
- snapshot size.

## Hardware policy

Product requirement: ordinary x64 laptop capable of Docker.

**Exact minimum CPU/RAM/disk is NOT FROZEN before measurement.**

PRECHECK writes tested configuration to README:
- OS/build;
- CPU/logical cores;
- RAM;
- free disk;
- Docker version;
- WSL if applicable;
- GPU optional.

No GPU may become mandatory unless clearly documented and CPU/remote fallback exists.

Benchmark snapshot must remain bounded; jury reproduction must not require tens of GB.

> СННИТ РАДАР (WSR)
