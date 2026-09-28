# PRECHECK_REPORT — СННИТ РАДАР / FastTrack v1.0

**Дата:** 2026-09-28  
**Роль:** PRECHECK  
**Итоговый статус:** **PASS WITH WARNINGS**

**Blockers open:** 0  
**Warnings open:** 8  
**DEV gate:** **OPEN** (FastTrack scope only; this PRECHECK session does not start DEV)

Код и конфигурация репозитория `weaksignalradar` **не изменялись** (в т.ч. `DATABASE_URL` не переписывался). Commit/push не выполнялись. DEV в этой сессии не начинался.

---

## 0. Recheck B-ENV-01 / B-ENV-02 (после старта Docker Desktop)

| Check | Command / method | Exit | Result |
|---|---|---|---|
| Docker daemon | `docker info` | **0** | Server 29.8.0 |
| Compose up | `docker compose up -d --build` | **0** | `db` healthy; `backend` up |
| PostgreSQL | `docker compose exec -T db pg_isready -U <user> -d <db>` | **0** | `accepting connections` |
| Alembic current | `docker compose exec -T backend python -m alembic current` | **0** | `a04_001_stage_a_storage (head)` |
| Alembic heads | `docker compose exec -T backend python -m alembic heads` | **0** | `a04_001_stage_a_storage (head)` |
| `/health/live` | `GET http://127.0.0.1:8000/health/live` | HTTP **200** | `{"status":"live"}` |
| `/health/ready` | `GET http://127.0.0.1:8000/health/ready` | HTTP **200** | `{"status":"ready"}` |
| Resolve `db` **inside** Compose network | `docker compose exec -T backend python -c "…socket.gethostbyname('db')…SELECT 1"` | **0** | `db_ip 172.18.0.3`, `db_select 1` |
| Integration **in** Compose network | `docker run --rm --network weaksignalradar_default -e DATABASE_URL=… -v <repo>:/work:ro -w /work --entrypoint sh weaksignalradar-backend:latest -c "pip install -q pytest==9.1.1 && python -m pytest -q tests/integration"` | **0** | **6 passed** |
| Control: resolve `db` **on host** | DNS `db` from Windows host | fail | `No such host is known` — ожидаемо |
| Control: host pytest + same `DATABASE_URL` (`@db:`) | `python -m pytest -q tests/integration` (host `.venv`) | **1** | 6 failed: `failed to resolve host 'db'` — **wrong environment**, не дефект Compose URL |

### Закрытие B-ENV

- **B-ENV-01 — CLOSED (PASS).** Docker Desktop + Compose stack работают; Postgres healthy; Alembic at head; health live/ready 200.
- **B-ENV-02 — CLOSED (NOT A DEFECT).** Hostname `db` в `DATABASE_URL` **корректен для Compose**: резолвится и коннектится внутри Docker network; integration в этом окружении зелёные. Переписывать на `127.0.0.1` **не требуется** для Compose runtime. Host-side pytest с Compose DNS — отдельный режим (нужен либо test-runner в network, либо отдельный host URL); это не доказанный баг `.env` для backend.

Backend entrypoint при старте: `database reachable; running alembic upgrade head` → затем Uvicorn.

---

## 1. Baseline

| Поле | Значение |
|---|---|
| Repo | `C:\Projects\WeakSignalRadar\weaksignalradar` |
| Current commit | `81fe888245b6f6d6c398d865e6000674bdc34874` |
| Commit message | `A-04: PostgreSQL storage, Alembic migration, health API, local Compose` |
| Working tree | не модифицировался PRECHECK |
| Stage A baseline (handoff `29_VERSION_MANIFEST.md`) | тот же SHA — совпадает |
| Handoff package integrity (`SHA256SUMS.json`) | **43/43 OK** (проверка предыдущего прогона) |
| Secrets in git | **PASS** — `.env` ignored; tracked only `.env.example` |

### Stage A inventory (факт)

- PostgreSQL models + Alembic `a04_001_stage_a_storage`: `search_runs`, `source_documents`, `source_spans`, `task_log`
- FastAPI: только `GET /health/live`, `GET /health/ready`
- Docker Compose: `compose.yaml` (db + backend, loopback binds)
- Discovery: **только** `OpenAlexAdapter` + SEC-001 redaction + snapshot store

---

## 2. Environment (актуально после recheck)

| Check | Result | Notes |
|---|---|---|
| OS | Windows NT 10.0.26200 | |
| CPU / RAM / disk | i5-10210U / ~16 GB / ~400 GB free C: | from prior PRECHECK |
| Python | 3.13.15 (`.venv`) | |
| Docker CLI / Compose | 29.8.0 / v5.5.1 | |
| Docker **daemon** | **PASS** | |
| PostgreSQL via Compose | **PASS** | healthy, port `127.0.0.1:5432` |
| Alembic on live DB | **PASS** | revision = head |
| FastAPI `/health/live` | **PASS** 200 | |
| FastAPI `/health/ready` | **PASS** 200 | |
| `db` DNS in Compose network | **PASS** | |
| Static UI served | **FAIL / absent** | нет frontend shell в repo (не ENV-blocker) |

### Boot без optional keys (prior; unchanged)

| Check | Result |
|---|---|
| App без `LLM_*` / `SOURCE_API_KEY` | **PASS** |
| OpenAlex без API key | **PASS** |

---

## 3. Tests / lint

| Command | Env | Exit | Result |
|---|---|---|---|
| `pytest` unit (prior) | host | **0** | 41 passed, 1 skipped |
| `ruff check src tests` (prior) | host | **0** | clean |
| `pytest tests/integration` | **Compose network** (`DATABASE_URL` host=`db`) | **0** | **6 passed** |
| `pytest tests/integration` | host + same `DATABASE_URL` | **1** | 6 failed — host cannot resolve `db` (control only) |

---

## 4. Sources

| Source | Role (FastTrack D-013) | Code status | Notes |
|---|---|---|---|
| OpenAlex | `REQUIRED_REFERENCE_SOURCE` | **PARTIAL** | adapter + mocks; live smoke **NOT_RUN** in this recheck |
| CORDIS/EURIO | `REQUIRED_ATTEMPT / FAIL_SOFT` | **MISSING** | DESIGNED gap |
| EPO LOD | `REQUIRED_ATTEMPT / FAIL_SOFT` | **MISSING** | DESIGNED gap |

Caps 15/500 / fail-soft CORDIS/EPO — **не enforced** (warnings).

---

## 5. Models

| Item | Recorded value |
|---|---|
| LLM provider/model | **DISABLED** |

### 5.1 B-MODEL-01 read-only verification (2026-09-28)

PO/Coordinator choice: `intfloat/multilingual-e5-small`.  
Веса модели **не загружались**. Код / `.env` / requirements / handoff methodology **не менялись**.

| Check | Result |
|---|---|
| HF API `…/api/models/intfloat/multilingual-e5-small` → `.sha` | `614241f622f53c4eeff9890bdc4f31cfecc418b3` (len=40) |
| `git ls-remote … refs/heads/main` | same SHA → `refs/heads/main` |
| Revision API `…/revision/<sha>` | OK — `id=intfloat/multilingual-e5-small`, `sha` matches |
| Artifact at revision (`resolve/<sha>/config.json` HEAD) | HTTP **200** |
| Private / disabled | `false` / `false` |

**Proposed reproducibility contract (report-only; not written into repo config):**

```text
EMBEDDING_MODEL_ID=intfloat/multilingual-e5-small
EMBEDDING_MODEL_REVISION=614241f622f53c4eeff9890bdc4f31cfecc418b3
EMBEDDING_METRIC=cosine
```

(`EMBEDDING_METRIC=cosine` — из frozen example `schemas/llm_config.example.yaml` + `10_FEATURES_A_E.md`: each `s` = cosine similarity.)

### 5.2 Model metadata (from HF model card + files at pinned revision; no weight download)

| Metadata | Source | Value |
|---|---|---|
| Embedding / vector dimension | model card; `config.json` `hidden_size`; `1_Pooling/config.json` `word_embedding_dimension` | **384** |
| Max input / token length | model card FAQ/Limitations; tokenizer example `max_length=512`; `config.json` `max_position_embeddings` | **512** tokens (longer texts truncated) |
| Multilingual support | model card / HF tags | Yes — trained for multilingual use; card: supports **100 languages** from xlm-roberta (low-resource may degrade) |
| Pooling (revision file) | `1_Pooling/config.json` @ pinned SHA | **mean tokens** (`pooling_mode_mean_tokens=true`) |
| Recommended input prefixes (model card FAQ) | model card | Asymmetric retrieval: `query: ` / `passage: `; symmetric similarity / features / clustering: use `query: ` prefix; card: prefixes required or performance degrades; apply even for non-English |
| Normalization in card examples | model card usage | L2-normalize embeddings before similarity (`F.normalize` / `normalize_embeddings=True`) |

### 5.3 FastTrack mapping — what else is required beyond MODEL_ID + REVISION

Для **закрытия PRECHECK pin (B-MODEL-01)** handoff/`19_PRECHECK_INSTRUCTIONS` требуют зафиксировать **ID + exact revision** (+ metric в example schema). Это выполнено выше.

Дополнительно FastTrack требует, но **не задаёт готовые литералы** в Decision Register:

| Requirement | Handoff basis | Status for B-MODEL-01 |
|---|---|---|
| `metric: cosine` | `schemas/llm_config.example.yaml`; cosine in `10_FEATURES_A_E.md` | Included in proposed contract |
| **preprocessing frozen per run** | `10_FEATURES_A_E.md`: «model/version/preprocessing frozen per run» | **Required for runtime reproducibility**, values must come from model card (not invented). Proposed freeze candidates from card/revision files (for DEV to wire, not applied now): prefixes `query:` / `passage:` per task type; `max_length=512` + truncation; mean pooling; L2 normalize before cosine |
| `provider: <local-or-api-adapter>` | `schemas/llm_config.example.yaml` placeholder | **Not chosen by this PRECHECK** — no frozen provider in handoff |
| Log `embedding_model_id` on run | `05_DATA_MODEL.md` / scoring docs | Implementation concern for DEV after GOV |

**Не придумано:** facet-specific prefix mapping для C signature fields (object/function/…) — в FastTrack нет отдельного frozen preprocessing profile beyond «freeze per run» + cosine.

### 5.4 B-MODEL-01 disposition

**B-MODEL-01 может быть CLOSED** на основании: PO-выбранный `MODEL_ID` + verified immutable full revision SHA + metric cosine из frozen contract example.

**W-MODEL-PREPROCESS disposition (update):** см. §7 — **CLOSED / RESOLVED BY ADDENDUM v1.0.1** после read-only verification `SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.1/01_EMBEDDING_PREPROCESSING_PROFILE_v1.md`.

---

## 6. Contracts vs Stage A

Прямого runtime-конфликта в коде нет (FastTrack ещё не реализован). Исторический Stage A `not_authorized` **сохраняется как запись предыдущего этапа** и не переписывается.

**B-GOV-01 — CLOSED / PO OVERRIDE AUTHORIZED** (Coordinator / Product Owner, 2026-09-28):

1. Accepted Stage A baseline остаётся immutable reference: commit `81fe888245b6f6d6c398d865e6000674bdc34874`.
2. Исторический Stage A `not_authorized` остаётся valid record предыдущего stage и **MUST NOT** быть rewritten / retroactively changed.
3. Для **нового** FastTrack implementation scope пакет `SNNIT_RADAR_24H_FASTTRACK_HANDOFF_v1.0` **explicitly supersedes** предыдущее Stage A `not_authorized` restriction.
4. Authorization только на implementation, governed by frozen FastTrack handoff; **не** authorize arbitrary methodology/architecture вне контракта.
5. Неразрешённые methodological/product ambiguities в DEV → **OPEN QUESTION** к Coordinator / PO, не самостоятельные решения DEV.

---

## 7. Blockers / warnings (актуально)

### Closed blockers (0 open)

1. ~~B-ENV-01~~ — **CLOSED PASS**
2. ~~B-ENV-02~~ — **CLOSED NOT A DEFECT**
3. ~~B-MODEL-01~~ — **CLOSED** (PO model + verified HF revision; report-only pin)
4. ~~B-GOV-01~~ — **CLOSED / PO OVERRIDE AUTHORIZED** (см. §6)

### Closed warnings

5. ~~W-MODEL-PREPROCESS~~ — **CLOSED / RESOLVED BY ADDENDUM v1.0.1**

Read-only verification: `SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.1/01_EMBEDDING_PREPROCESSING_PROFILE_v1.md` (`FROZEN FOR FASTTRACK DEV`).

Совпадает с PRECHECK pin и закрывает ранее отсутствовавший profile:

- `EMBEDDING_PROFILE_ID=e5_small_v1`
- `EMBEDDING_MODEL_ID=intfloat/multilingual-e5-small`
- `EMBEDDING_MODEL_REVISION=614241f622f53c4eeff9890bdc4f31cfecc418b3` (full SHA)
- dimension **384**, max tokens **512**, pooling **mean**, normalization **L2**, metric **cosine**
- prefix policy: retrieval `query:`/`passage:`; symmetric/C facets `query:`/`query:`
- missing evidence → UNKNOWN/INSUFFICIENT (no invent / no forced sim 0|1)
- provenance versions: `prefix_policy_version=e5_prefix_v1`, `preprocessing_version=e5_small_preprocess_v1`
- addendum §11 explicitly: `W-MODEL-PREPROCESS = RESOLVED BY ADDENDUM v1.0.1`
- handoff v1.0 не переписан; addendum дополняет только embedding preprocessing

DEV обязан реализовать контракт без отклонений; это implementation duty, не reopen PRECHECK warning.

### Open warnings (8)

1. W-SRC-01: OpenAlex live viability не подтверждена
2. W-SRC-02: source caps не enforced
3. W-SRC-03: CORDIS/EPO отсутствуют (DESIGNED gap)
4. W-UI-01: frontend shell отсутствует
5. W-API-01: FastTrack `/api/v1/*` отсутствует
6. W-OPS-01: нет `run.ps1` / `manage.ps1`
7. W-DOC-01: README всё ещё Stage A surface
8. W-TEST-01: host-side `pytest tests/integration` с Compose `DATABASE_URL` (`@db`) закономерно падает; нужен отдельный runner/URL policy (не менять Compose `.env` без решения)

---

## 8. Gate status

Все PRECHECK blockers закрыты.  
**W-MODEL-PREPROCESS закрыт addendum v1.0.1.** Остаются 8 non-blocking warnings.

**DEV gate: OPEN** для работ строго по `SNNIT_RADAR_24H_FASTTRACK_HANDOFF_v1.0` + обязательный contract `SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.1/01_EMBEDDING_PREPROCESSING_PROFILE_v1.md` / `prompts/DEV_PROMPT.md`.  
Этот отчёт **не запускает** DEV — старт по отдельной команде Coordinator/PO.

---

## 9. Recorded pins / status for manifest

```yaml
repo_commit: "81fe888245b6f6d6c398d865e6000674bdc34874"
stage_a_baseline_commit: "81fe888245b6f6d6c398d865e6000674bdc34874"
embedding_model_id: "intfloat/multilingual-e5-small"
embedding_model_revision: "614241f622f53c4eeff9890bdc4f31cfecc418b3"
embedding_metric: "cosine"
llm_provider: "DISABLED"
llm_model_id: "DISABLED"
openalex: "PARTIAL_ADAPTER_MOCK_TESTED_LIVE_NOT_RUN"
cordis: "MISSING"
epo_lod: "MISSING"
compose_db_hostname: "db"   # VALID inside Compose network
b_env_01: "CLOSED_PASS"
b_env_02: "CLOSED_NOT_A_DEFECT"
b_model_01: "CLOSED"
b_gov_01: "CLOSED_PO_OVERRIDE_AUTHORIZED"
w_model_preprocess: "CLOSED_RESOLVED_BY_ADDENDUM_v1.0.1"
embedding_profile_id: "e5_small_v1"
prefix_policy_version: "e5_prefix_v1"
preprocessing_version: "e5_small_preprocess_v1"
blockers_open: 0
warnings_open: 8
dev_gate: "OPEN"
precheck_status: "PASS_WITH_WARNINGS"
```

---

## 10. Final verdict

# **PASS WITH WARNINGS**

| Metric | Value |
|---|---|
| Final PRECHECK status | **PASS WITH WARNINGS** |
| Blockers open | **0** |
| Warnings open | **8** |
| W-MODEL-PREPROCESS | **CLOSED / RESOLVED BY ADDENDUM v1.0.1** |
| DEV gate open? | **YES** (FastTrack handoff + addendum v1.0.1 embedding profile) |

PRECHECK session **does not start DEV**. Application code/configuration/handoff unchanged; updated report only.

> СННИТ РАДАР (WSR)
