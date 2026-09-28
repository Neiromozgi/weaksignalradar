# 02 — DEV / TEST EXECUTION POLICY v1

**Project:** СННИТ РАДАР  
**Document ID:** `02_DEV_TEST_EXECUTION_POLICY_v1`  
**Addendum version:** `SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.1`  
**Status:** `FROZEN FOR FASTTRACK EXECUTION`  
**Purpose:** зафиксировать границы автономной работы DEV и TEST, правила Git, secrets, sources, README и handoff между ролями.

---

## 1. Governance / область действия

Этот документ является дополнением к:

`SNNIT_RADAR_24H_FASTTRACK_HANDOFF_v1.0`

и к:

`01_EMBEDDING_PREPROCESSING_PROFILE_v1.md`.

Он не изменяет и не переписывает frozen handoff v1.0 и его SHA256 manifest.

Документ регулирует **только порядок исполнения FastTrack DEV / TEST**:
- что агент может делать автономно;
- что требует решения Coordinator / Product Owner;
- когда DEV обязан остановиться;
- когда TEST может начинать работу;
- когда допустим commit / push / merge.

Методология A–E, scoring, filters, source portfolio и product scope этим документом не изменяются.

---

## 2. DEV role

DEV реализует только утверждённый FastTrack scope.

DEV может автономно:

- читать frozen handoff и addendum;
- создавать и изменять код в пределах FastTrack scope;
- создавать и изменять тесты;
- обновлять README и operator documentation по фактически реализованному состоянию;
- запускать `pytest`;
- запускать `ruff`;
- запускать Docker / Docker Compose;
- выполнять Alembic migrations/checks;
- запускать FastAPI/backend;
- проверять `/health/live` и `/health/ready`;
- выполнять API checks;
- использовать CACHE / SNAPSHOT;
- выполнять bounded LIVE smoke только в разрешённых source caps;
- создавать локальные runtime artifacts, если они не должны попадать в Git;
- проверять fail-soft поведение источников;
- обновлять `.env.example` только именами переменных без секретных значений.

DEV не имеет права самостоятельно:

- менять методологию;
- менять веса A–E;
- менять percentile contract;
- менять data sufficiency gate;
- менять weak-signal filters;
- менять source portfolio;
- заменять утверждённый source другим источником;
- выбирать новый LLM provider/model без утверждения;
- менять frozen embedding profile;
- делать `git commit`;
- делать `git push`;
- делать `git merge`;
- создавать Pull Request;
- запускать TEST или передавать работу TEST автоматически;
- менять `main`;
- менять baseline Stage A retroactively.

Если DEV обнаруживает неоднозначность, конфликт требований или необходимость нового product/methodology decision:

```text
STOP FOR DECISION
→ OPEN QUESTION
→ Coordinator / Product Owner
```

DEV не должен самостоятельно «разумно решить» governance-вопрос.

---

## 3. DEV completion gate

DEV завершает работу только после формирования `DEV_REPORT`.

Минимальный `DEV_REPORT`:

```text
DEV_STATUS
implemented scope
changed files
new files
tests executed
tests passed/failed/skipped
ruff result
Docker/Compose result
API result
source status
LIVE/CACHE/SNAPSHOT status
README status
known limitations
open questions
credentials required
manual actions required
git status
READY_FOR_COORDINATOR_REVIEW
```

Допустимые финальные DEV-состояния:

```text
READY_FOR_COORDINATOR_REVIEW
BLOCKED
STOP_FOR_DECISION
```

DEV не начинает TEST автоматически.

---

## 4. Coordinator gate between DEV and TEST

После DEV:

```text
DEV
→ Coordinator review
→ human decision
→ TEST
```

Только Coordinator / Product Owner решает, можно ли передавать результат TEST.

Перед TEST проверяются минимум:

- scope соответствует handoff;
- нет несанкционированной смены methodology;
- нет несанкционированной смены sources;
- нет secrets в Git;
- README обновлён;
- DEV_REPORT полный;
- известные ограничения явно зафиксированы;
- `git diff` понятен;
- рабочее дерево соответствует ожидаемому состоянию.

---

## 5. TEST role

TEST независим от DEV.

TEST может автономно:

- читать handoff / addendum;
- читать DEV_REPORT;
- запускать unit tests;
- запускать integration tests;
- запускать regression tests;
- запускать Docker / Compose;
- проверять migrations;
- проверять FastAPI/API;
- проверять UI/backend integration;
- проверять LIVE/CACHE/SNAPSHOT;
- выполнять bounded source smoke;
- проверять source caps;
- проверять fail-soft;
- проверять secrets / `.env` hygiene;
- проверять README reproducibility;
- проверять acceptance criteria;
- сравнивать реализацию с frozen contract.

TEST не имеет права:

- исправлять DEV-код;
- менять methodology;
- менять architecture decisions;
- менять source portfolio;
- менять score/profile;
- делать `git commit`;
- делать `git push`;
- делать `git merge`;
- создавать Pull Request;
- скрывать или исправлять defect вместо его регистрации.

Если TEST находит дефект:

```text
DEFECT
→ report
→ Coordinator
→ DEV rework decision
```

---

## 6. TEST completion gate

TEST завершает работу одним из состояний:

```text
PASS
FAIL
BLOCKED
```

TEST_REPORT должен содержать минимум:

```text
TEST_STATUS
scope tested
commands executed
unit result
integration result
regression result
Docker/Compose result
API result
UI result
LIVE/CACHE/SNAPSHOT result
source result
secrets result
README reproducibility result
acceptance criteria result
defects
warnings
limitations
git status
```

TEST не выполняет commit/push.

---

## 7. Git policy

FastTrack execution flow:

```text
snnit-fasttrack
→ DEV local changes
→ Coordinator review
→ TEST
→ Coordinator decision
→ manual commit
→ manual push
```

Запрещено для DEV и TEST:

```text
git commit
git push
git merge
git rebase
git reset --hard
git clean -fd
force push
```

Без отдельного разрешения Coordinator также не создавать новые branches / PR.

`main` не изменяется в рамках автономной DEV / TEST работы.

---

## 8. Cursor execution mode

Локальный Cursor используется с:

```text
Run Mode = Auto-Review
```

Цель:

- агент может выполнять обычные безопасные команды без постоянного ручного `Run?`;
- встроенные safety checks Cursor сохраняются;
- отсутствие ручного подтверждения команды не означает разрешение на governance/Git действия.

Auto-Review не отменяет ограничения этого документа.

---

## 9. Secrets / API keys

Реальные secrets хранятся только локально.

Разрешено:

```text
.env
OS environment variables
local secret store
```

Запрещено:

```text
commit secrets
push secrets
hardcode secrets
write real keys into README
write real keys into .env.example
```

`.env` должен оставаться в `.gitignore`.

`.env.example` содержит только имена переменных и безопасные placeholders без настоящих ключей.

Приложение должно запускаться без optional LLM/source credentials, если контракт определяет модуль как optional/fail-soft.

Отсутствующий optional credential:

```text
DISABLED / REQUIRED_CREDENTIAL / PARTIAL
```

не должен превращаться в crash всего приложения.

---

## 10. LLM policy

DEV не выбирает LLM provider/model самостоятельно.

Если provider/model не утверждён:

```text
LLM_STATUS = NOT_CONFIGURED
OPEN QUESTION → Coordinator
```

Архитектура должна оставаться provider-swappable через config/adapter.

LLM разрешён только в той роли, которая определена frozen contract.

LLM не принимает самостоятельно ranking/eligibility truth decisions, если contract этого не разрешает.

---

## 11. Source policy

Разрешённый FastTrack source portfolio определяется frozen handoff.

DEV не заменяет источник другим API самостоятельно.

Если утверждённый source:

- требует credential;
- требует регистрации;
- требует принятия ToS;
- недоступен;
- изменил endpoint;
- превышает cap;
- rate-limited;

DEV фиксирует состояние и сообщает Coordinator.

Примеры:

```text
REQUIRED_CREDENTIAL
NOT_RUN
PARTIAL
ERROR
RATE_LIMITED
```

Нельзя заменять:

```text
OpenAlex
CORDIS/EURIO
EPO Linked Open Data
```

на другой источник без отдельного решения.

Timeout / rate limit / cap exhaustion не равны `NOT_FOUND`.

---

## 12. Source registration / manual account actions

DEV и TEST не:

- создают пользовательские аккаунты;
- принимают Terms of Service;
- оформляют API subscriptions;
- создают billing accounts;
- вводят платёжные данные;
- подтверждают email/2FA от имени пользователя.

Если источник требует ручной регистрации:

```text
MANUAL_ACTION_REQUIRED
```

и в отчёте указывается:

```text
source
required account
required credential
required manual step
blocking/non-blocking status
```

Дальнейшее решение принимает пользователь / Coordinator.

---

## 13. README = P0 deliverable

README является обязательным P0 артефактом FastTrack.

DEV обновляет README по фактически реализованному состоянию.

README должен отражать минимум:

- что реализовано;
- что `PARTIAL`;
- что `DESIGNED`;
- что `ROADMAP`;
- требования к системе;
- quick start;
- Docker;
- `.env`;
- migrations;
- sources;
- source limits;
- LIVE / CACHE / SNAPSHOT;
- Candidate Registry;
- A–E;
- percentiles;
- gates / filters;
- score profiles;
- API;
- UI;
- tests;
- replay / reproducibility;
- limitations;
- troubleshooting.

Нельзя описывать не реализованную функцию как реализованную.

---

## 14. Documentation synchronization

При изменении runtime behavior DEV обязан одновременно обновить соответствующую документацию.

Особенно:

```text
README
.env.example
source configuration examples
API contract implementation notes
operations/run instructions
implemented/partial status
```

Документация должна соответствовать коду на момент `READY_FOR_COORDINATOR_REVIEW`.

---

## 15. Handoff integrity

Frozen handoff:

```text
SNNIT_RADAR_24H_FASTTRACK_HANDOFF_v1.0
```

не редактируется.

Addendum:

```text
SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.1
```

добавляет решения, принятые после freeze handoff.

Если требуется новое governance/rule изменение:

- не переписывать историю;
- создать новый versioned addendum/decision;
- зафиксировать Coordinator / Product Owner approval.

---

## 16. Final execution rule

Автономность агента означает:

```text
самостоятельно выполнять разрешённую техническую работу
```

но не означает:

```text
самостоятельно принимать product/methodology/governance решения
самостоятельно передавать работу следующей роли
самостоятельно фиксировать результат в Git
```

Canonical flow:

```text
DEV autonomous execution
→ READY_FOR_COORDINATOR_REVIEW
→ Coordinator / Product Owner review
→ explicit TEST authorization
→ TEST autonomous execution
→ TEST_REPORT
→ Coordinator / Product Owner decision
→ manual Git commit/push
```
