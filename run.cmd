@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker CLI not found. Install Docker Desktop and ensure docker is on PATH.
  exit /b 1
)
docker compose version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker Compose plugin not available. Use a current Docker Desktop install.
  exit /b 1
)

if not exist ".env" (
  if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    echo Created .env from .env.example
  ) else (
    echo ERROR: Missing .env and .env.example
    exit /b 1
  )
)

call "_wsr_env.cmd"
if errorlevel 1 exit /b 1

set "DO_BUILD=0"
if /i "%~1"=="-Build" set "DO_BUILD=1"

if "!DO_BUILD!"=="1" (
  echo Starting Docker Compose with build...
  docker compose up --build -d
) else (
  echo Starting Docker Compose...
  docker compose up -d
)
if errorlevel 1 (
  echo ERROR: docker compose up failed.
  exit /b 1
)

set "BASE=http://127.0.0.1:!BACKEND_PORT!"
set /a ATTEMPTS=0
set /a MAX_ATTEMPTS=90
echo Waiting for backend readiness (up to !MAX_ATTEMPTS! attempts, 2s each)...

:wait_loop
set /a ATTEMPTS+=1
curl -sf -o nul --max-time 3 "!BASE!/health/ready" 2>nul
if not errorlevel 1 goto ready_ok
if !ATTEMPTS! geq !MAX_ATTEMPTS! goto ready_fail
ping 127.0.0.1 -n 3 >nul
goto wait_loop

:ready_fail
echo WARNING: Backend /health/ready not OK yet. Services may still be starting.
curl -sf -o nul --max-time 3 "!BASE!/health/live" 2>nul
if errorlevel 1 (
  echo ERROR: Backend /health/live is also unavailable.
  exit /b 1
)
goto print_urls

:ready_ok
echo Backend is ready.

:print_urls
echo.
echo UI:     !BASE!/
echo Health: !BASE!/health/live
echo Ready:  !BASE!/health/ready
echo.
echo Operator CLI: manage.cmd status ^| diagnostics ^| logs ^| help
exit /b 0
