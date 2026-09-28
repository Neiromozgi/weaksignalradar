# 10 — EXPERT / JURY LOCAL RUN GUIDE v1

**Status:** APPROVED CONTENT REQUIREMENT

Проект должен запускаться вне среды разработчика и не зависеть от Cursor, авторского Python environment, старой PostgreSQL, абсолютных путей `C:\Projects\...` или авторского `.env`.

Основной runtime — Docker Compose.

## Требования

Windows: Git, Docker Desktop, современный браузер. Интернет нужен для первого build/model download и LIVE sources, если LIVE проверяется.

CACHE/SNAPSHOT не должны требовать персональных API secrets.

## Получение проекта

```powershell
git clone <repository-url>
cd weaksignalradar
git checkout <release-branch-or-tag>
```

## Environment

```powershell
Copy-Item .env.example .env
```

`.env` не коммитить.

Для LIVE эксперт добавляет собственные разрешённые credentials согласно README.

## Запуск

```powershell
.\run.ps1
```

Открыть: `http://127.0.0.1:8000/`

## Быстрая проверка

```powershell
.\manage.ps1 status
.\manage.ps1 diagnostics
```

## Рекомендуемый сценарий жюри

Сначала воспроизводимый CACHE/SNAPSHOT: открыть UI → запустить анализ → увидеть честный TOP-15/меньше 15/0 → открыть Technology Card → Documents/Candidates/Methodology.

LIVE — при наличии сети/credentials: оставить LIVE → ввести направление → запустить → проверить новый snapshot.

## Если что-то не работает

```powershell
.\manage.ps1 status
.\manage.ps1 diagnostics
.\manage.ps1 logs
docker compose ps
docker compose logs backend
```

## Остановка

```powershell
docker compose down
```

`down -v` должен сопровождаться предупреждением, что он удаляет persistent volumes.

## Clean-machine acceptance

Перед release: fresh clone → новый `.env` → Docker build → `run.ps1` → CACHE/SNAPSHOT → UI → diagnostics. LIVE проверить отдельно.

## Первый запуск E5

Если weights не встроены в image, первый запуск может потребовать загрузку модели. README должен честно указать необходимость сети и поведение при недоступной модели. Полностью offline запуск — отдельное release requirement.
