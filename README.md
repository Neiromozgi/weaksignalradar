# weaksignalradar

Status: **Stage A only** (WSR-RC2-A-ACTIVE-20260922). Stage B, Stage C and any publication are **NOT authorized**. This repository was created fresh under task A-01; it is not a fork, clone, or copy of the historical MVP 1.6 research repository.

## What this repository is right now

- A clean git root containing only the currently active Stage-A normative documents:
  - `AGENTS.md` — active agent rules for this new repository (Stage A override applies).
  - `PROJECT_INSTRUCTIONS_AND_STRUCTURE.md` — active project instructions for this new repository.
  - `RELEASE_MANIFEST.json` — normative lock of Stage-A inputs (release `WSR-RC2-A-ACTIVE-20260922`).
  - `contracts/stage_a_contract.json` — the single mandatory Stage-A interface contract.
  - `IMPORT_MANIFEST.json` — empty by design; any future reuse of MVP 1.6 code must be added file-by-file with source commit/hash/license/diff, never as a bulk import.
- No application code, dependencies, tests, migrations, or Docker setup yet. Those are scoped to later Stage-A tickets (A-02, A-03, A-04) and are **not part of A-01**.

## Not done yet / known limitations

- No `pyproject.toml`, no pinned dependency lock, no `pytest` suite, no `ruff` configuration (A-02).
- No live source adapter, no SEC-001 fix/tests, no snapshot storage (A-03).
- No PostgreSQL migrations, no backend scaffold, no `/health/live` or `/health/ready` endpoints, no Docker Compose (A-04).
- No LLM extraction, no verification (V0–V3), no classification/buckets, no ranking, no TOP-15, no EXPLAIN, no public web deployment — all explicitly **not authorized** for Stage A per `contracts/stage_a_contract.json` (`not_authorized` list).
- This initial commit has not been reviewed by TEST. DEV does not self-approve; status remains `READY_FOR_TEST` until an independent TEST report exists.

## Rules

See `AGENTS.md` and `PROJECT_INSTRUCTIONS_AND_STRUCTURE.md` in this repository, and the Stage-A source package (`00_START_HERE/ACTIVE_STAGE_A.md`, `07_STAGED_TASKS/STAGE_A_TICKETS_ACTIVE.md`) for the authoritative, versioned instructions this repository must follow. On any conflict, the source Stage-A package and PO decisions take precedence over this README.
