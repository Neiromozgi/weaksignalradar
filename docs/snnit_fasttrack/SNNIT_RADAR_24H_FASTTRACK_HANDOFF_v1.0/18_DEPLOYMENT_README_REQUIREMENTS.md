# 18 — Deployment & README Requirements

## Runtime

Base:
`Docker / local-first`

Access:
`localhost:8000`

Optional:
public HTTPS tunnel for presentation.

PostgreSQL остаётся во внутренней Docker network; не требовать host publish 5432.

## One-command start

После clone:

```powershell
.\run.ps1
```

Script:
1. check Docker;
2. create `.env` from `.env.example` if absent;
3. create folders/volumes;
4. build/start compose;
5. wait PostgreSQL;
6. Alembic migrate;
7. wait FastAPI health;
8. print URLs/status.

## Secrets

- `.env.example`: names only.
- `.env`: secrets, gitignored.
- app boots without optional keys.
- competition keys passed out-of-band and revoked later.

## Product README — mandatory sections

1. Implemented / Partial / Target.
2. Tested system requirements from PRECHECK.
3. Quick start.
4. Docker / run.ps1.
5. `.env`.
6. DB/migrations.
7. LIVE/CACHE/SNAPSHOT.
8. Source adapters and limits.
9. Enable/disable/add source.
10. Switch LLM.
11. Document/Candidate registries.
12. A–E / percentiles / filters / score profiles.
13. FWCI diagnostic.
14. Bootstrap on-demand.
15. API.
16. UI.
17. Tests/replay.
18. Known limitations.
19. Troubleshooting.
20. Security.

> СННИТ РАДАР (WSR)
