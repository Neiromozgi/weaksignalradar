# FastTrack local start (Docker Compose). Requires .env with DATABASE_URL / Postgres vars.
param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) {
    Write-Host "Copy .env.example to .env and set DATABASE_URL / Postgres credentials."
    exit 1
}

$composeArgs = @("compose", "up")
if ($Build) { $composeArgs += "--build" }
$composeArgs += "-d"

docker @composeArgs
Write-Host "Backend: http://127.0.0.1:${env:BACKEND_PORT}/ (default 8000)"
Write-Host "Health:  http://127.0.0.1:${env:BACKEND_PORT}/health/live"
