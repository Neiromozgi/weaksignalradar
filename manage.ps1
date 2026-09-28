# FastTrack operator CLI (release ops). Secrets are never printed.
param(
    [Parameter(Position = 0)]
    [ValidateSet("status", "sources", "llm-status", "snapshots", "logs", "diagnostics", "help")]
    [string]$Command = "help",
    [int]$Tail = 30
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Get-BackendBaseUrl {
    $port = $env:BACKEND_PORT
    if (-not $port) { $port = "8000" }
    return "http://127.0.0.1:$port"
}

function Show-Help {
    @"
FastTrack manage.ps1

Usage:
  .\manage.ps1 status
  .\manage.ps1 sources
  .\manage.ps1 llm-status
  .\manage.ps1 snapshots
  .\manage.ps1 logs [-Tail N]
  .\manage.ps1 diagnostics
  .\manage.ps1 help
"@
}

function Invoke-BackendGet {
    param(
        [string]$Path,
        [int]$TimeoutSec = 15,
        [switch]$ColdStartHint
    )
    $base = Get-BackendBaseUrl
    try {
        return Invoke-RestMethod -Uri "$base$Path" -Method Get -TimeoutSec $TimeoutSec
    } catch {
        $raw = $_.Exception.Message
        $isTimeout = ($raw -match '(?i)timed out|timeout|time-out')
        if ($ColdStartHint -and $isTimeout) {
            Write-Host "Diagnostics request timed out after ${TimeoutSec} seconds."
            Write-Host "On a cold backend start, the first call may take longer while the embedding runtime loads."
            Write-Host "Wait briefly and run: .\manage.ps1 diagnostics"
        } else {
            Write-Host "Backend request failed: $raw"
        }
        return $null
    }
}

function Show-Logs {
    param([int]$Lines)
    $localLog = Join-Path $PSScriptRoot "logs\snnit-radar.jsonl"
    if (Test-Path $localLog) {
        Get-Content $localLog -Tail $Lines
        return
    }
    docker compose exec -T backend sh -c "tail -n $Lines /app/logs/snnit-radar.jsonl 2>/dev/null || true"
}

switch ($Command) {
    "help" { Show-Help; exit 0 }
    "status" {
        Write-Host "=== Docker Compose ==="
        docker compose ps
        Write-Host ""
        Write-Host "=== Backend health ==="
        $base = Get-BackendBaseUrl
        foreach ($path in @("/health/live", "/health/ready")) {
            try {
                $r = Invoke-WebRequest -Uri "$base$path" -UseBasicParsing -TimeoutSec 10
                Write-Host "$path -> $($r.StatusCode)"
            } catch {
                Write-Host "$path -> UNAVAILABLE"
            }
        }
        Write-Host ""
        Write-Host "=== PostgreSQL (container) ==="
        docker compose exec -T db pg_isready -U $env:POSTGRES_USER -d $env:POSTGRES_DB 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "pg_isready: not ready or exec failed (check POSTGRES_* in .env)"
        }
    }
    "sources" {
        $data = Invoke-BackendGet "/api/v1/config/sources"
        if ($null -eq $data) { exit 1 }
        $data.sources | ForEach-Object {
            $detail = if ($_.detail) { $_.detail } else { "" }
            Write-Host ("{0}: status={1} {2}" -f $_.source_id, $_.status, $detail)
        }
    }
    "llm-status" {
        $data = Invoke-BackendGet "/api/v1/config/llm"
        if ($null -eq $data) { exit 1 }
        Write-Host "profile_id=$($data.profile_id)"
        Write-Host "provider=$($data.provider)"
        Write-Host "model=$($data.model)"
        Write-Host "runtime_status=$($data.status)"
        Write-Host "openai_api_key=$($data.openai_api_key)"
    }
    "snapshots" {
        $data = Invoke-BackendGet "/api/v1/snapshots"
        if ($null -eq $data) { exit 1 }
        $data.snapshots | ForEach-Object {
            Write-Host ("snapshot_id={0} mode={1} immutable={2}" -f `
                    $_.snapshot_id, $_.mode, $_.immutable)
        }
    }
    "logs" {
        Show-Logs -Lines $Tail
    }
    "diagnostics" {
        $d = Invoke-BackendGet -Path "/api/v1/diagnostics" -TimeoutSec 60 -ColdStartHint
        if ($null -eq $d) { exit 1 }
        Write-Host "SNNIT RADAR (WSR) diagnostics"
        Write-Host "Service: $($d.service)"
        Write-Host "Database: $($d.database)"
        Write-Host "Embedding: $($d.embedding)"
        Write-Host "LLM: $($d.llm) (key $($d.openai_api_key))"
        Write-Host "OpenAlex: $($d.sources.openalex)"
        Write-Host "CORDIS: $($d.sources.cordis)"
        Write-Host "EPO: $($d.sources.epo_lod)"
        Write-Host "Analyses recorded: $($d.analyses_recorded)"
        Write-Host "Last run: $($d.last_run_id) status=$($d.last_run_status)"
        Write-Host "Last snapshot: $($d.last_snapshot_id)"
    }
}
