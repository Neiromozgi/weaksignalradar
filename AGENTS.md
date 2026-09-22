> **АКТИВАЦИЯ PO 22.09.2026:** этот файл является действующим шаблоном только для НОВОГО репозитория и ТОЛЬКО этапа A после проверки активного Release Manifest. Упоминания PROPOSED ниже — исторический статус RC2 до решения PO; не дают разрешения B/C/публикации. Приоритет: `00_START_HERE/ACTIVE_STAGE_A.md`.

# AGENTS.md — WeakSignalRadar NEW repository RC2 PROPOSED

**НЕ ДЕЙСТВУЕТ ДО ОТДЕЛЬНОГО РАЗРЕШЕНИЯ PO И СОЗДАНИЯ НОВОГО РЕПОЗИТОРИЯ.** Этот текст замещает старый конфликтный AGENTS.md MVP 1.6 ТОЛЬКО в новом репозитории. Старый файл 1.6 сохраняется без изменений как исторический материал.

## Priority
Официальное ТЗ/организатор → явные PO решения → утверждённая release spec+method+prompts+schemas в RELEASE_MANIFEST → принятые код и тесты. На конфликт STOP + issue PO, не сливать разные версии молча. `ARCH-RC2-PROPOSED` не утверждён. Перед запуском проверить release manifest hash и stage authorization.

## Scope
Событийное ядро с открытым произвольным запросом, 3 buckets, full registry/replay, узкий V2, claim-level primary provenance, RU/multilingual names, H3/H1 ranking only post-gate, C1 NOT_ESTIMATED, safe replaceable source+LLM, postgres/web/Docker/tests/docs. No universal H1–H6 discovery claims. SPECTER clustering NOT mandatory.

## Stage permissions
A ONLY after PO written approval for A: new repo foundation, adapter client SEC001, raw snapshot, DB migration skeleton, task audit and web/API scaffold. No V2/bucket/rank publishing claimed ready.
B ONLY after explicit PO B + A gate + aligned method/schema + real-source negative V2 evidence. Implement claim chain and contract tests.
C ONLY after explicit PO C + B gate. Implement rank/results/registry/UI/deployment, independent QA before publication.
If missing authorization STOP. Never infer full MVP consent from user requesting documentation.

## Hard prohibitions
Do not embed/reference whole expert Excel or use it as app answer index; no credentials or personal info; no fake successful live search, fake source/URL/citation, no undisclosed offline fallback; no hallucinated VERIFIED/early/novelty; no future leakage; no scoring weights without PO; no edits to method/prompt text by DEV. Never copy old 1.6 AGENTS, old scope constraints, full experiments or hidden old code wholesale.

## Role boundaries
DEV code/unit tests with commit+logs, no product decisions; TEST independently receives frozen spec/commit, validates negatives and logs FAIL/NOT_RUN, never changes tests to make pass; PRECHECK performs authorized real-source and experimental checks only, saves raw data/redaction+provenance, never substitutes a successful example. One human with 3 agent contexts, not 3 parallel developer teams.

## Evidence of completion
For each task: task ID, gate, commit SHA, files changed, commands, full exit codes/pytest collected and passed count, fixtures+logs, known limitations, test review by TEST and independent Reviewer where specified. No passing security/evidence gate through mocks alone. Do not commit new files outside approved scope.

## Stop/escalation
23 Sep 20:00 MSK lacking real query→document→span→narrow verified fact OR explicit UNKNOWN→object→bucket: STOP escalation PO. 25 Sep 18:00 lacking clean deployed QA/security: NO-GO escalation PO. Never silently shrink P0, extend deadline, publish repo or take over PO duties.
