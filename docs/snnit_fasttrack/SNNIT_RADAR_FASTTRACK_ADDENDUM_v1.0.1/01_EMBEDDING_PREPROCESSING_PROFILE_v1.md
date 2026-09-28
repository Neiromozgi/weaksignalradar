# 01 — EMBEDDING PREPROCESSING PROFILE v1

**Project:** СННИТ РАДАР  
**Document ID:** `01_EMBEDDING_PREPROCESSING_PROFILE_v1`  
**Addendum version:** `SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.1`  
**Status:** `FROZEN FOR FASTTRACK DEV`  
**Purpose:** зафиксировать воспроизводимый runtime-профиль embedding для FastTrack-реализации.

---

## 1. Governance / приоритет

Этот документ является дополнением к:

`SNNIT_RADAR_24H_FASTTRACK_HANDOFF_v1.0`

Он **не изменяет** и не переписывает исходный handoff v1.0 и его SHA256 manifest.

Если в handoff v1.0 не определены конкретные runtime-параметры embedding preprocessing, для FastTrack DEV применяется этот документ.

Область действия ограничена embedding preprocessing и воспроизводимостью семантических сравнений. Документ **не меняет** методологию A–E, веса, percentile contract, data sufficiency gate, weak-signal filters или ranking.

---

## 2. Frozen embedding model

```text
EMBEDDING_PROFILE_ID=e5_small_v1
EMBEDDING_MODEL_ID=intfloat/multilingual-e5-small
EMBEDDING_MODEL_REVISION=614241f622f53c4eeff9890bdc4f31cfecc418b3
EMBEDDING_VECTOR_DIMENSION=384
EMBEDDING_MAX_TOKENS=512
EMBEDDING_POOLING=mean
EMBEDDING_NORMALIZATION=L2
EMBEDDING_METRIC=cosine
```

`MODEL_REVISION` — полный immutable commit SHA модели, проверенный PRECHECK через Hugging Face API и `git ls-remote`.

Использование `main`, `latest`, сокращённого SHA или иной незапиненной версии модели в конкурсной сборке запрещено.

---

## 3. Общий preprocessing contract

Перед вычислением embedding:

1. использовать tokenizer/config выбранной revision;
2. не менять tokenizer settings скрыто между запусками;
3. максимальная длина входа — `512` токенов;
4. входы длиннее лимита — `truncate` по стандартному поведению tokenizer данной revision;
5. pooling — `mean pooling`;
6. итоговый embedding — `L2 normalize`;
7. similarity — `cosine similarity`;
8. пустое или неподтверждённое значение не заменять выдуманным текстом;
9. preprocessing profile должен записываться в provenance каждого run/snapshot.

---

## 4. Prefix policy

### 4.1. Retrieval: пользовательский/доменный запрос → исходный документ

Для поискового запроса:

```text
query: <normalized query text>
```

Для документа / evidence text:

```text
passage: <document text>
```

Рекомендуемый document input в рамках доступных данных:

```text
passage: <title> <abstract/evidence text>
```

Не добавлять несуществующий abstract/full text.

### 4.2. Symmetric semantic similarity

Для сравнений, где обе стороны являются равноправными смысловыми сущностями, использовать одинаковый prefix:

```text
query: <entity A>
query: <entity B>
```

Это относится к:

- alias / synonym comparison;
- semantic-equivalence checks;
- сравнению technology signatures;
- вычислениям, связанным с `C — Content Novelty`, если обе стороны представлены как сопоставимые technology/facet representations.

Нельзя использовать различающиеся `query:` / `passage:` только потому, что одна технология историческая, а другая текущая.

---

## 5. Technology signature for C — Content Novelty

Семантическая новизна сравнивает **техническую сущность**, а не рынок, бренд или маркетинговое описание.

Используемые facets:

```text
object_class
function
mechanism
architecture_or_process
key_technical_property
```

Для каждого facet:

1. использовать только evidence-grounded значение;
2. не подставлять значения из соседних полей;
3. `UNKNOWN` / отсутствующий facet не превращать в ноль и не генерировать LLM-догадкой;
4. одинаковое preprocessing rule применяется ко всем кандидатам и историческим предшественникам;
5. market/application wording не использовать как самостоятельное доказательство технической новизны.

Если handoff задаёт отдельные веса facets, DEV обязан использовать их без изменения.

---

## 6. Canonical text construction

Для symmetric comparison отдельного facet:

```text
query: <facet_value>
```

Если реализуется объединённая technical signature для вспомогательной диагностики, порядок полей должен быть фиксированным:

```text
object_class: <value>
function: <value>
mechanism: <value>
architecture_or_process: <value>
key_technical_property: <value>
```

и затем:

```text
query: <canonical technical signature>
```

Порядок полей нельзя менять между run.

Объединённая signature не должна подменять facet-level contract, если формула `C` в handoff требует сравнения по facets.

---

## 7. Missing / insufficient evidence

Если значение, необходимое для embedding comparison, отсутствует или не подтверждено evidence:

```text
UNKNOWN / INSUFFICIENT
```

Не допускается:

- генерировать отсутствующий технический признак;
- использовать название рынка как замену mechanism/property;
- присваивать similarity = 0;
- присваивать similarity = 1;
- индивидуально менять preprocessing или модель для конкретного кандидата.

---

## 8. Reproducibility fields

Каждый run, использующий embeddings, должен позволять восстановить минимум:

```text
embedding_profile_id
embedding_model_id
embedding_model_revision
vector_dimension
max_tokens
pooling
normalization
similarity_metric
prefix_policy_version
preprocessing_version
snapshot_id
candidate_universe_version
feature_contract_version
```

Для FastTrack:

```text
prefix_policy_version=e5_prefix_v1
preprocessing_version=e5_small_preprocess_v1
```

---

## 9. Model replaceability

Embedding-модель является заменяемым модулем архитектуры.

Будущая версия может использовать другую модель без переписывания всего pipeline, при условии создания нового versioned profile.

Новая модель НЕ должна незаметно заменять текущую внутри того же profile ID.

Пример:

```text
e5_small_v1      -> current FastTrack profile
bge_m3_v2        -> possible future profile
```

Результаты, полученные разными embedding profiles, нельзя считать полностью сопоставимыми без отдельной проверки.

---

## 10. DEV implementation rule

DEV должен:

- реализовать этот профиль как конфигурационный/versioned contract;
- не hardcode модель хаотично в разных модулях;
- сохранить возможность заменить профиль через config/adapter;
- использовать один и тот же frozen profile во всех местах FastTrack, где требуется данный embedding contract;
- добавить тесты на model ID/revision, prefixes, max length policy, normalization и deterministic preprocessing;
- не менять значения этого документа без нового Coordinator / Product Owner decision.

---

## 11. PRECHECK warning disposition

```text
W-MODEL-PREPROCESS = RESOLVED BY ADDENDUM v1.0.1
```

После добавления этого документа в authoritative project context предупреждение может считаться закрытым при условии, что DEV реализует контракт без отклонений.

---

## 12. Human-readable summary

Для конкурсной версии СННИТ РАДАР используется одна конкретная версия `intfloat/multilingual-e5-small`.

Модель можно заменить в будущих версиях продукта, но в текущей сборке её ID, revision и preprocessing заморожены, чтобы одинаковые входные данные обрабатывались одинаковым способом и результат можно было воспроизвести.
