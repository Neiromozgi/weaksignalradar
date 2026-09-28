# 00 — READ FIRST

## Что строим

**СННИТ РАДАР** — модульный web-сервис:

`запрос → документы источников → реестр найденных документов → технологические кандидаты → A/B/C/D/E → достаточность данных → weak-signal filters → Score → ranking → TOP-15 и остальные реестры → карточка технологии`.

Цель — искать **сигнал новой/зарождающейся научно-исследовательской технологии**, а не просто растущую тему, новый рынок или новую формулировку старой технологии.

## Authority / precedence

Если старый документ или код противоречат этому пакету, действует:

1. `01_DECISION_REGISTER.md`
2. executable contracts этого пакета
3. accepted Stage A baseline
4. старые review/handoff только как provenance

Cursor не имеет права сам:
- менять веса;
- менять смысл A–E;
- смешивать `REJECTED` и `INSUFFICIENT`;
- делать optional key обязательным для boot;
- заменять missing на 0;
- превращать LLM в финального судью новизны.

## Stage A

Сохранять принятый Stage A: PostgreSQL, Alembic, FastAPI, Docker, OpenAlex adapter, provenance/coverage, fail-closed semantics, tests. Не переписывать без подтверждённой причины.

## Cursor flow

`PRECHECK → DEV → TEST`

PRECHECK проверяет и фиксирует окружение/версии. DEV реализует frozen contract. TEST проверяет, но не меняет формулы.

> СННИТ РАДАР (WSR)
