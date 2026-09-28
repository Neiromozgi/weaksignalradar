# 25 — Target Repository Structure

Не переименовывать существующий repo root. Адаптировать к текущему коду, не делать destructive rewrite.

```text
<existing-repo>/
  README.md
  .env.example
  .gitignore
  docker-compose.yml
  run.ps1
  manage.ps1

  app/
    api/
    orchestration/
    sources/
      base.py
      openalex/
      cordis/
      epo_lod/
    llm/
      base.py
      providers/
      prompts/
    documents/
    candidates/
    features/
      a_growth.py
      b_acceleration.py
      c_novelty.py
      d_confirmation.py
      e_weakness.py
    ranking/
    registries/
    snapshots/
    db/
    models/
    config/

  frontend/
    api.js
    ...

  migrations/
  tests/
    unit/
    integration/
    contract/
    fixtures/
    snapshots/

  snapshots/
    README.md
    benchmark/

  docs/
    fasttrack/
    methodology/
    api/
    deployment/

  scripts/
```

Separation:
- source adapters = acquisition/normalization;
- LLM adapters = structured extraction;
- feature modules = calculation;
- ranking does not call providers;
- UI does not calculate metrics.

> СННИТ РАДАР (WSR)
