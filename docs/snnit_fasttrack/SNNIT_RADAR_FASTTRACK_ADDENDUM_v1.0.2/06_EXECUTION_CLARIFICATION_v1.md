# 06 — EXECUTION CLARIFICATION v1

**Project:** СННИТ РАДАР  
**Decision ID:** `DEV_TEST_EXECUTION_CLARIFICATION_v1`  
**Addendum:** `SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.2`  
**Status:** `APPROVED / FROZEN FOR DEV PASS #2`

## 1. Причина

Фраза:

```text
не запускать TEST автоматически
```

относится только к независимой роли / фазе TEST.

Она НЕ запрещает DEV запускать технические automated tests своей реализации.

## 2. Разрешено и обязательно внутри DEV

DEV обязан автономно запускать, когда это необходимо:

```text
pytest
unit tests
integration tests
regression tests
ruff
Docker / Docker Compose checks
Alembic checks
health checks
API checks
bounded source smoke tests
другие technical checks из handoff
```

Для обычных технических проверок не требуется отдельное разрешение Coordinator.

## 3. Что запрещено без Coordinator authorization

DEV не имеет права самостоятельно:

```text
запускать отдельного TEST Agent
начинать independent TEST phase
передавать работу TEST
объявлять TEST PASS
```

Разграничение:

```text
automated test suite inside DEV
= ALLOWED AND REQUIRED

independent TEST role / TEST agent / TEST phase
= FORBIDDEN until explicit Coordinator authorization
```

## 4. Git restrictions unchanged

DEV и TEST по-прежнему не выполняют без отдельного разрешения:

```text
git commit
git push
git merge
git rebase
Pull Request
```

## 5. DEV final gate

После завершения DEV pass:

```text
READY_FOR_COORDINATOR_REVIEW
```

DEV останавливается.

Только после Coordinator review может быть дано отдельное разрешение на независимый TEST.
