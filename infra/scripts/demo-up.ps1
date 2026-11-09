<#
.SYNOPSIS
  Start the full DinkDesk stack on the demo host (Jose's PC), ingest the knowledge base and
  open Cloudflare quick tunnels for the backend and the frontend.

.DESCRIPTION
  Run from anywhere:   powershell -ExecutionPolicy Bypass -File infra\scripts\demo-up.ps1
  Stop the tunnels:    powershell -ExecutionPolicy Bypass -File infra\scripts\demo-down.ps1

  1. Opens the tunnels first (quick-tunnel URLs change every run and the frontend build and the
     backend's CORS list both need them).
  2. Builds and starts every container, including the frontend profile, and waits until healthy.
  3. Runs the KB ingestion once inside the backend container (incremental: unchanged docs are skipped).
  4. Prints the URLs to send Arjan and Andre and saves them to infra\.demo\urls.txt.

  Only the backend and frontend are exposed. n8n, Postgres, Chroma, Mailpit and the mock
  directory stay on localhost (docs/architecture.md section 7).

.PARAMETER NoTunnel     Local only: no cloudflared, frontend talks to http://localhost:8000.
.PARAMETER NoFrontend   Skip the frontend container and its tunnel (Arjan runs `npm run dev` himself).
.PARAMETER SkipIngest   Do not run the KB ingestion.
.PARAMETER FullIngest   Re-embed every KB document (after changing the embedding model).
#>
[CmdletBinding()]
param(
    [switch]$NoTunnel,
    [switch]$NoFrontend,
    [switch]$SkipIngest,
    [switch]$FullIngest
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Compose = Join-Path $RepoRoot 'infra\docker-compose.yml'
$EnvFile = Join-Path $RepoRoot '.env'
$StateDir = Join-Path $RepoRoot 'infra\.demo'

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

# --- 0. Prerequisites --------------------------------------------------------
Step 'Checking prerequisites'
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail 'docker not found. Install Docker Desktop first: infra\docker-desktop-setup.md'
}
docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) { Fail 'Docker Desktop is not running. Start it from the Start menu and wait for "Engine running".' }

if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $RepoRoot '.env.example') $EnvFile
    Write-Host 'Created .env from .env.example. Put your GEMINI_API_KEY in it, then run this script again.' -ForegroundColor Yellow
    exit 1
}

if (-not $NoTunnel -and -not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Fail 'cloudflared not found. Install it with:  winget install --id Cloudflare.cloudflared  (then open a new terminal), or run with -NoTunnel.'
}

New-Item -ItemType Directory -Force $StateDir | Out-Null
Set-Content -Path (Join-Path $StateDir '.gitignore') -Value '*' -Encoding ascii

# Stop tunnels left over from a previous run.
& (Join-Path $PSScriptRoot 'demo-down.ps1') -Quiet

# --- 1. Tunnels --------------------------------------------------------------
function Start-QuickTunnel([string]$Name, [int]$Port) {
    $log = Join-Path $StateDir "tunnel-$Name.log"
    $out = Join-Path $StateDir "tunnel-$Name.out"
    Remove-Item $log, $out -ErrorAction SilentlyContinue
    $proc = Start-Process cloudflared -PassThru -WindowStyle Hidden `
        -ArgumentList @('tunnel', '--no-autoupdate', '--url', "http://localhost:$Port") `
        -RedirectStandardError $log -RedirectStandardOutput $out
    Add-Content -Path (Join-Path $StateDir 'tunnel-pids.txt') -Value $proc.Id
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
        if ($proc.HasExited) { Fail "cloudflared for $Name exited. See $log" }
        $text = Get-Content $log -Raw -ErrorAction SilentlyContinue
        if ($text -match '(https://[a-z0-9-]+\.trycloudflare\.com)') { return $Matches[1] }
    }
    Fail "No tunnel URL for $Name after 60 s. See $log"
}

$BackendUrl = 'http://localhost:8000'
$FrontendUrl = 'http://localhost:3000'
if (-not $NoTunnel) {
    Step 'Opening Cloudflare quick tunnel for the backend (port 8000)'
    $BackendUrl = Start-QuickTunnel 'backend' 8000
    Write-Host "    $BackendUrl"
    if (-not $NoFrontend) {
        Step 'Opening Cloudflare quick tunnel for the frontend (port 3000)'
        $FrontendUrl = Start-QuickTunnel 'frontend' 3000
        Write-Host "    $FrontendUrl"
    }
}

# Compose reads these from the shell (they win over .env): the frontend is built against the
# backend's public URL, and the backend allows the tunnel origin plus local dev.
$origins = @('http://localhost:3000')
if ($FrontendUrl -ne 'http://localhost:3000') { $origins += $FrontendUrl }
$env:CORS_ORIGINS = $origins -join ','
$env:FRONTEND_API_BASE_URL = $BackendUrl

# --- 2. Stack ----------------------------------------------------------------
Step 'Building and starting containers (first run takes several minutes)'
$composeArgs = @('compose', '-f', $Compose, '--env-file', $EnvFile)
if (-not $NoFrontend) { $composeArgs += @('--profile', 'frontend') }
& docker @composeArgs up -d --build --wait --wait-timeout 300
if ($LASTEXITCODE -ne 0) {
    & docker @composeArgs ps
    Fail 'Some containers did not become healthy. Check: docker compose -f infra\docker-compose.yml logs <service>'
}

# --- 2b. Database tables + demo accounts (both safe to re-run) -----------------
Step 'Creating database tables and demo accounts'
& docker @composeArgs exec -T backend alembic upgrade head
if ($LASTEXITCODE -ne 0) { Fail 'Database migration failed. Check: docker compose -f infra\docker-compose.yml logs backend postgres' }
& docker @composeArgs exec -T backend python -m app.seed
if ($LASTEXITCODE -ne 0) { Fail 'Seeding demo accounts failed. Check the output above.' }

# --- 3. KB ingestion -----------------------------------------------------------
if (-not $SkipIngest) {
    Step 'Ingesting the knowledge base into Chroma'
    & docker @composeArgs exec -T backend python -c 'import app.rag.ingest' *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host '    Skipped: this backend build has no app.rag.ingest yet (RAG pipeline PR not merged).' -ForegroundColor Yellow
    } else {
        $ingestArgs = @('exec', '-T', 'backend', 'python', '-m', 'app.rag.ingest')
        if ($FullIngest) { $ingestArgs += '--full' }
        & docker @composeArgs @ingestArgs
        if ($LASTEXITCODE -ne 0) { Write-Host '    Ingestion failed (check GEMINI_API_KEY in .env). The stack is still up.' -ForegroundColor Yellow }
    }
}

# --- 4. Summary --------------------------------------------------------------
$lines = @(
    "DinkDesk demo stack - $(Get-Date -Format 'yyyy-MM-dd HH:mm')",
    '',
    'Send to Arjan (frontend):',
    "  App:                       $FrontendUrl",
    "  NEXT_PUBLIC_API_BASE_URL = $BackendUrl",
    '',
    'Send to Andre (backend):',
    "  API base:                  $BackendUrl",
    "  Swagger UI:                $BackendUrl/docs",
    "  Health:                    $BackendUrl/health",
    '',
    'Local only (this PC):',
    '  Mailpit inbox (codes, emails)  http://localhost:8025',
    '  n8n                            http://localhost:5678',
    '  Mock directory                 http://localhost:8090/docs',
    '  ChromaDB                       http://localhost:8001'
)
if (-not $NoTunnel) {
    $lines += @('', 'Tunnel URLs change every run. Stop the tunnels with infra\scripts\demo-down.ps1')
}
$lines | Set-Content -Path (Join-Path $StateDir 'urls.txt') -Encoding utf8
Write-Host ''
Write-Host ($lines -join "`n") -ForegroundColor Green
Write-Host "`n(Saved to infra\.demo\urls.txt. Check everything with infra\scripts\verify-stack.ps1)"
