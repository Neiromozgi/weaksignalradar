@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "CMD=%~1"
if "%CMD%"=="" set "CMD=help"

if /i "%CMD%"=="help" goto do_help
if /i "%CMD%"=="status" goto do_status
if /i "%CMD%"=="sources" goto do_sources
if /i "%CMD%"=="llm-status" goto do_llm
if /i "%CMD%"=="snapshots" goto do_snapshots
if /i "%CMD%"=="logs" goto do_logs
if /i "%CMD%"=="diagnostics" goto do_diagnostics

echo Unknown command: %CMD%
echo Run manage.cmd help
exit /b 1

:ensure_env
if not exist ".env" (
  echo ERROR: .env not found. Copy .env.example to .env
  exit /b 1
)
call "_wsr_env.cmd"
if errorlevel 1 exit /b 1
set "BASE=http://127.0.0.1:!BACKEND_PORT!"
exit /b 0

:ensure_curl
where curl >nul 2>&1
if errorlevel 1 (
  echo ERROR: curl.exe not found. Windows 10+ includes curl; install or enable curl on PATH.
  exit /b 1
)
exit /b 0

:http_get
REM Usage: call :http_get PATH OUTFILE TIMEOUT_SEC
set "HTTP_PATH=%~1"
set "HTTP_OUT=%~2"
set "HTTP_TO=%~3"
if "%HTTP_TO%"=="" set "HTTP_TO=15"
curl -sf --max-time !HTTP_TO! "!BASE!!HTTP_PATH!" -o "!HTTP_OUT!"
set "HTTP_RC=!errorlevel!"
exit /b !HTTP_RC!

:do_help
echo FastTrack manage.cmd (Windows CMD, no PowerShell script policy required)
echo.
echo Usage:
echo   manage.cmd status
echo   manage.cmd sources
echo   manage.cmd llm-status
echo   manage.cmd snapshots
echo   manage.cmd logs [N]
echo   manage.cmd diagnostics
echo   manage.cmd help
echo.
echo Optional developer tools: manage.ps1, run.ps1
exit /b 0

:do_status
call :ensure_env
if errorlevel 1 exit /b 1
call :ensure_curl
if errorlevel 1 exit /b 1
echo === Docker Compose ===
docker compose ps
echo.
echo === Backend health ===
curl -sf -o nul --max-time 10 "!BASE!/health/live"
if errorlevel 1 (echo /health/live -^> UNAVAILABLE) else (echo /health/live -^> 200)
curl -sf -o nul --max-time 10 "!BASE!/health/ready"
if errorlevel 1 (echo /health/ready -^> UNAVAILABLE) else (echo /health/ready -^> 200)
echo.
echo === PostgreSQL (container) ===
docker compose exec -T db pg_isready -U "!POSTGRES_USER!" -d "!POSTGRES_DB!" 2>nul
if errorlevel 1 (
  echo pg_isready: not ready or exec failed (check POSTGRES_* in .env)
)
exit /b 0

:do_sources
call :ensure_env
if errorlevel 1 exit /b 1
docker compose exec -T backend python /app/scripts/manage_cli_http.py sources
exit /b !errorlevel!

:do_llm
call :ensure_env
if errorlevel 1 exit /b 1
docker compose exec -T backend python /app/scripts/manage_cli_http.py llm-status
exit /b !errorlevel!

:do_snapshots
call :ensure_env
if errorlevel 1 exit /b 1
docker compose exec -T backend python /app/scripts/manage_cli_http.py snapshots
exit /b !errorlevel!

:do_logs
call :ensure_env
if errorlevel 1 exit /b 1
set "LINES=%~2"
if "%LINES%"=="" set "LINES=30"
docker compose exec -T backend sh -c "tail -n %LINES% /app/logs/snnit-radar.jsonl 2>/dev/null || true"
exit /b 0

:do_diagnostics
call :ensure_env
if errorlevel 1 exit /b 1
docker compose exec -T backend python /app/scripts/manage_cli_http.py diagnostics
set "DRC=!errorlevel!"
if !DRC! neq 0 (
  echo.
  echo If the backend just started, the first diagnostics call may take longer while the embedding runtime loads.
  echo Wait briefly and run: manage.cmd diagnostics
)
exit /b !DRC!
