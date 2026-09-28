# 04 — LLM EXTRACTION PROFILE v1

**Project:** СННИТ РАДАР  
**Decision ID:** `LLM_EXTRACTION_v1`  
**Addendum:** `SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.2`  
**Status:** `APPROVED / FROZEN FOR DEV PASS #2`

## 1. Runtime role

LLM:

```text
OPTIONAL FOR APP BOOT
REQUIRED FOR FULL ABCDE_v1 LIVE ANALYSIS
```

Отсутствие LLM credential не должно мешать запуску приложения, health endpoints, PostgreSQL, CACHE/SNAPSHOT replay и UI.

Если LLM не настроен:

```text
LLM_STATUS=NOT_CONFIGURED
```

Полный LIVE `C — Content Novelty` не должен фабриковаться.

## 2. Approved provider / model

```text
LLM_PROFILE_ID=openai_gpt56_terra_extraction_v1
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-terra
LLM_API=responses
LLM_OUTPUT_MODE=json_schema_strict
```

Использовать OpenAI Responses API.

DEV не выбирает другую модель самостоятельно.

Если для конкретного API account доступен immutable/datelocked snapshot выбранной модели, DEV фиксирует его в runtime metadata. Если такого snapshot нет, сохраняются model ID + request/output metadata + validated extraction.

## 3. Разрешённая функция LLM

LLM используется только для evidence-grounded structured extraction.

Выход — техническая сигнатура:

```text
candidate_name
object_class
function
mechanism
architecture_or_process
key_technical_property
evidence references / spans
unknown_fields
```

## 4. Что LLM НЕ делает

LLM не имеет права самостоятельно:

```text
rank candidates
assign final C score
assign final A/B/D/E
change percentile population
change weights
change data sufficiency result
change heuristic filters
decide TOP-15 eligibility
invent missing technical facets
perform arbitrary web research as evidence
```

## 5. Missing evidence rule

Если facet нельзя подтвердить входным evidence:

```text
null / UNKNOWN
```

Запрещено достраивать факт «по знаниям модели» или выдавать inference без evidence reference как наблюдённый факт.

## 6. Structured output validation

LLM output должен проходить strict JSON Schema validation.

Versioned identifiers:

```text
prompt_bundle_version=technical_signature_extraction_v1
schema_version=technical_signature_v1
llm_profile_id=openai_gpt56_terra_extraction_v1
```

Невалидный ответ не принимается как корректная extraction и не превращается автоматически в score.

## 7. Reproducibility

Для каждого accepted extraction сохранять минимум:

```text
llm_provider
llm_model
model_snapshot/revision if available
llm_profile_id
prompt_bundle_version
schema_version
request_timestamp
provider_request_or_response_id if available
source_document_id
evidence references
validated structured output
validation status
```

Для неизменённого SNAPSHOT/CACHE replay повторный LLM вызов не требуется.

## 8. Secret policy

Реальный OpenAI key:

```text
OPENAI_API_KEY
```

хранится только локально в `.env`, OS environment или другом local secret store.

Никогда не хранить реальное значение в Git, README или `.env.example`.

## 9. Credential timing

DEV pass #2 может реализовать LLMAdapter и offline tests без реального key.

Для финального bounded LIVE smoke пользователь вручную добавляет API key в local `.env`.

Если key отсутствует, DEV продолжает независимые P0 задачи и отмечает:

```text
REQUIRED_CONFIGURATION
```

а не блокирует весь FastTrack.

## 10. Embedding separation

LLM profile не заменяет frozen embedding profile `e5_small_v1`.

```text
evidence
→ LLM structured extraction
→ validated technical signature
→ frozen embedding preprocessing
→ deterministic similarity
→ C_raw / percentile C
```
