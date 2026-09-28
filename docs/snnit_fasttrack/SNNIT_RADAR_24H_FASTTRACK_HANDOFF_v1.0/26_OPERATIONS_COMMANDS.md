# 26 — Operations Commands to Implement

Exact internal implementation may adapt to existing repo, but user-facing operations should be equivalent.

## Start

```powershell
.\run.ps1
```

## Source management

```powershell
.\manage.ps1 source list
.\manage.ps1 source status
.\manage.ps1 source enable openalex
.\manage.ps1 source enable cordis
.\manage.ps1 source enable epo_lod
.\manage.ps1 source disable cordis
.\manage.ps1 source test openalex
```

Register installed adapter:

```powershell
.\manage.ps1 source register --id <id> --adapter <python-path> --config <config-file>
.\manage.ps1 source test <id>
.\manage.ps1 source enable <id>
```

No core algorithm edits required for enable/disable.

## LLM management

```powershell
.\manage.ps1 llm list
.\manage.ps1 llm status
.\manage.ps1 llm set --provider <provider> --model <model>
.\manage.ps1 llm test
```

API key is read from `.env`, never passed in command history.

## Snapshots/cache

```powershell
.\manage.ps1 snapshot list
.\manage.ps1 snapshot verify <snapshot_id>
.\manage.ps1 cache status
```

## Safety

Config mutations:
- logged;
- config version incremented;
- secrets never printed;
- restart only when technically needed.

> СННИТ РАДАР (WSR)
