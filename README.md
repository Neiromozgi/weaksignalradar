# weaksignalradar

Status: **Stage A only** (WSR-RC2-A-ACTIVE-20260922). Stage B, Stage C and any publication are **NOT authorized**. This repository was created fresh under task A-01; it is not a fork, clone, or copy of the historical MVP 1.6 research repository.

## What this repository is right now

- Stage A foundation through A-03: package layout, OpenAlex discovery adapter with SEC-001 redaction, snapshot store.
- A-04 adds PostgreSQL storage (search_runs / source_documents / source_spans / task_log), reversible Alembic migration, minimal FastAPI health endpoints, and local Docker Compose (db + backend on loopback only).

## Not done yet / known limitations

- No LLM extraction, no verification (V0–V3), no classification/buckets, no ranking, no TOP-15, no EXPLAIN, no public web deployment — all explicitly **not authorized** for Stage A per `contracts/stage_a_contract.json` (`not_authorized` list).
- SourceSpan table is storage-preparation only; no VERIFIED semantics.
- Local Compose stand is loopback-bound and must not be published.
- DEV does not self-approve; status remains `READY_FOR_TEST` until an independent TEST report exists.

## Rules

See `AGENTS.md` and `PROJECT_INSTRUCTIONS_AND_STRUCTURE.md` in this repository, and the Stage-A source package (`00_START_HERE/ACTIVE_STAGE_A.md`, `07_STAGED_TASKS/STAGE_A_TICKETS_ACTIVE.md`) for the authoritative, versioned instructions this repository must follow. On any conflict, the source Stage-A package and PO decisions take precedence over this README.
