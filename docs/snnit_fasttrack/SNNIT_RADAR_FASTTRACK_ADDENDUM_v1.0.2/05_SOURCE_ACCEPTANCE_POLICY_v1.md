# 05 — SOURCE ACCEPTANCE POLICY v1

**Project:** СННИТ РАДАР  
**Decision ID:** `SOURCE_ACCEPTANCE_v1`  
**Addendum:** `SNNIT_RADAR_FASTTRACK_ADDENDUM_v1.0.2`  
**Status:** `APPROVED / FROZEN FOR DEV PASS #2`

## 1. Source roles

```text
OpenAlex
= REQUIRED_REFERENCE_SOURCE

CORDIS / EURIO
= REQUIRED_ATTEMPT
= FAIL_SOFT
= evidence sensor for D

EPO Linked Open Data
= REQUIRED_ATTEMPT
= FAIL_SOFT
= patent evidence sensor for D
```

Источники не являются взаимозаменяемыми.

## 2. OpenAlex

OpenAlex является reference source для reference corpus, temporal series, A/B/E и reference population по frozen methodology.

### Existing Stage A credential

В Stage A уже существует рабочий OpenAlex API-key/configuration path.

DEV pass #2 должен:
- переиспользовать существующий локальный OpenAlex credential/configuration;
- не требовать повторной регистрации;
- не переносить реальный key в Git;
- сначала проверить существующий Stage A path;
- не переименовывать credential/config без необходимости.

### P0 before TEST

OpenAlex должен пройти реальный bounded LIVE smoke:

```text
real API request
stable IDs
dedup
Source Document Registry
snapshot/cache
provenance
caps
reference universe construction
```

Frozen caps:

```text
max 15 external calls/run
max 6 search/list pages
max 500 Works before candidate extraction
hard cutoff 90 sec
```

Если OpenAlex недоступен при новом LIVE refresh:

```text
REFERENCE_SOURCE_UNAVAILABLE
PARTIAL / ERROR
```

CORDIS/EPO не заменяют OpenAlex denominator/reference universe.

## 3. CORDIS / EURIO

P0 transport:

```text
CORDIS / EURIO Knowledge Graph
public Linked Open Data / SPARQL
```

P0 path не должен считаться credential-dependent по умолчанию.

DEV не переключается на другой CORDIS API только потому, что там удобнее authentication/data format.

Если пользователь позже получает credential для отдельного CORDIS API/DET, это не меняет утверждённый P0 transport автоматически.

### P0 before TEST

Нужен настоящий bounded EURIO/SPARQL adapter, не stub.

Минимальная normalization:

```text
stable project ID
title
start/end or relevant dates
participating organisation(s)
source URL / provenance
source execution status
```

Frozen caps:

```text
max 8 bounded SPARQL calls/run
max 250 projects
hard cutoff 120 sec
```

Failure semantics:

```text
successful query + 0 records → SEARCHED_OK + 0
timeout → PARTIAL / ERROR
rate/cap problem → PARTIAL / RATE_LIMITED
not executed → NOT_RUN
```

## 4. EPO Linked Open Data

P0 transport:

```text
EPO Linked Open EP Data
API / SPARQL suitable for bounded occasional use
```

Не подменять автоматически EPO OPS, Google Patents или другой patent API.

Если пользователь позже получает credential для отдельного EPO service, это не разрешает смену P0 source/transport без Coordinator decision.

### P0 before TEST

Stub недостаточен.

Нужен реальный bounded adapter с минимальной normalization:

```text
publication/application stable ID
title if available
publication date
applicant / organisation if available
source URI / provenance
source execution status
```

## 5. Fail-soft rule

CORDIS/EURIO и EPO failure не должны:
- падать всем приложением;
- превращаться в `NOT_FOUND`;
- давать ложный ноль подтверждения.

При недоступности:

```text
coverage = PARTIAL / UNKNOWN
```

`D — Independent Confirmation` использует только реально наблюдённые evidence lineages/source classes.

## 6. Acceptance gate before independent TEST

### OpenAlex

```text
LIVE real call                 PASS
caps                           PASS
dedup/stable IDs               PASS
Source Document Registry       PASS
snapshot/cache                 PASS
provenance                     PASS
reference universe             PASS
```

### CORDIS/EURIO

```text
real SPARQL attempt            PASS
minimal normalization          PASS
caps                           PASS
fail-soft                      PASS
coverage state                 PASS
```

### EPO Linked Open Data

```text
real bounded attempt           PASS
minimal normalization          PASS
caps                           PASS
fail-soft                      PASS
coverage state                 PASS
```

`SEARCHED_OK + 0 records` является валидным результатом.

## 7. Credential / registration policy

Пользователь может отдельно зарегистрировать credentials для дополнительных официальных API.

Но для утверждённого P0:
- существующий OpenAlex key уже имеется и переиспользуется;
- EURIO public SPARQL не должен блокироваться отсутствием CORDIS API key;
- EPO Linked Open Data path не должен автоматически заменяться credentialed EPO API.

Все реальные credentials:
- только local `.env` / environment;
- никогда Git;
- никогда README;
- никогда реальные значения в `.env.example`.

Если выбранный именно P0 endpoint фактически потребует credential/registration:

```text
MANUAL_ACTION_REQUIRED
```

DEV сообщает Coordinator и не подменяет endpoint самостоятельно.
