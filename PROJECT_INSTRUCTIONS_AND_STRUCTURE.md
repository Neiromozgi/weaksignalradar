> **АКТИВАЦИЯ PO 22.09.2026:** этот файл является действующим шаблоном только для НОВОГО репозитория и ТОЛЬКО этапа A после проверки активного Release Manifest. Упоминания PROPOSED ниже — исторический статус RC2 до решения PO; не дают разрешения B/C/публикации. Приоритет: `00_START_HERE/ACTIVE_STAGE_A.md`.

# PROJECT_INSTRUCTIONS_AND_STRUCTURE — NEW WeakSignalRadar scope

Status PROPOSED. New independent repository; previous 1.6 Experiment 01–02 restrictions apply ONLY to historical research repository and shall not be transplanted. Single source of truth: RELEASE_MANIFEST.json + docs/approved_spec + PO authorizations. Keep origin import manifest to track only permitted 1.6 code.

No automatic interaction among Chats 1/2/3/4 or Cursor. PO relays signed/approved artifacts. Chat 1 architecture & interface owner; Chat 2 method / prompt content owner; Chat 3 independent QA; Chat 4 map H1–H6 used elements (no new research); Cursor DEV/TEST/PRECHECK sequential contexts. Each branch has explicit gate and rollback plan.

Start dev session: verify stage authorization + manifest hashes, check clean working tree, read stage ticket, inspect tests, run only permitted changes, report exact commands and outputs. End: commit + test log + new risks + handoff TEST, never self-approve. Stage C publication needs additional PO consent.
