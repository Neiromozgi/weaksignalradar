@echo off
REM Load .env into environment (CMD only). Caller must use EnableDelayedExpansion.
if not exist ".env" (
  echo ERROR: .env not found. Copy .env.example to .env and set PostgreSQL values.
  exit /b 1
)
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
  if not "%%a"=="" (
    set "%%a=%%b"
  )
)
if not defined BACKEND_PORT set "BACKEND_PORT=8000"
if "%POSTGRES_USER%"=="" (
  echo ERROR: POSTGRES_USER is empty in .env
  exit /b 1
)
if "%POSTGRES_PASSWORD%"=="" (
  echo ERROR: POSTGRES_PASSWORD is empty in .env
  exit /b 1
)
if "%POSTGRES_DB%"=="" (
  echo ERROR: POSTGRES_DB is empty in .env
  exit /b 1
)
exit /b 0
