<#
.SYNOPSIS
  Check that every DinkDesk container answers, then run one end-to-end check:
  ask the mock directory for a one-time code and find the "SMS" in Mailpit.

  powershell -ExecutionPolicy Bypass -File infra\scripts\verify-stack.ps1
#>
[CmdletBinding()]
param([string]$DirectoryApiKey)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$failed = 0

function Check([string]$Name, [scriptblock]$Test) {
    try {
        $detail = & $Test
        Write-Host ("[ OK ] {0,-34} {1}" -f $Name, $detail) -ForegroundColor Green
    } catch {
        Write-Host ("[FAIL] {0,-34} {1}" -f $Name, $_.Exception.Message) -ForegroundColor Red
        $script:failed++
    }
}

function Get-Ok([string]$Url) {
    $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
    return "HTTP $($r.StatusCode)"
}

if (-not $DirectoryApiKey) {
    $DirectoryApiKey = 'dev-directory-key'
    $envFile = Join-Path $RepoRoot '.env'
    if (Test-Path $envFile) {
        $line = Select-String -Path $envFile -Pattern '^\s*DIRECTORY_API_KEY\s*=\s*(.+)$' | Select-Object -First 1
        if ($line) { $DirectoryApiKey = $line.Matches[0].Groups[1].Value.Trim() }
    }
}

Write-Host "`nContainers" -ForegroundColor Cyan
docker compose -f (Join-Path $RepoRoot 'infra\docker-compose.yml') --profile frontend ps --format 'table {{.Service}}\t{{.State}}\t{{.Health}}'

Write-Host "`nEndpoints" -ForegroundColor Cyan
Check 'Backend    :8000/health' { Get-Ok 'http://localhost:8000/health' }
Check 'ChromaDB   :8001/api/v2/heartbeat' { Get-Ok 'http://localhost:8001/api/v2/heartbeat' }
Check 'n8n        :5678/healthz' { Get-Ok 'http://localhost:5678/healthz' }
Check 'Mock dir.  :8090/health' { Get-Ok 'http://localhost:8090/health' }
Check 'Mailpit    :8025/readyz' { Get-Ok 'http://localhost:8025/readyz' }
Check 'Postgres   :5432 (pg_isready)' {
    docker compose -f (Join-Path $RepoRoot 'infra\docker-compose.yml') exec -T postgres pg_isready -q
    if ($LASTEXITCODE -ne 0) { throw 'pg_isready failed' }
    'accepting connections'
}
Check 'Frontend   :3000 (optional)' { Get-Ok 'http://localhost:3000' }

Write-Host "`nEnd to end: one-time code -> Mailpit" -ForegroundColor Cyan
Check 'OTP for demo.staff reaches Mailpit' {
    $h = @{ 'X-API-Key' = $DirectoryApiKey }
    Invoke-RestMethod -Method Post -Uri 'http://localhost:8090/admin/reload' -Headers $h | Out-Null
    $body = '{"employee_no": "PH-10021"}'
    $otp = Invoke-RestMethod -Method Post -Uri 'http://localhost:8090/accounts/demo.staff/otp' `
        -Headers $h -ContentType 'application/json' -Body $body
    Start-Sleep -Seconds 1
    $msgs = Invoke-RestMethod -Uri 'http://localhost:8025/api/v1/messages?limit=10'
    # Not $_.To.Address: on Windows PowerShell 5.1 that calls the array's Address() method instead of enumerating.
    $hit = $msgs.messages | Where-Object { ($_.To | ForEach-Object { $_.Address }) -contains '639170000021@sms.picklehub.example' } | Select-Object -First 1
    Invoke-RestMethod -Method Post -Uri 'http://localhost:8090/admin/reload' -Headers $h | Out-Null
    if (-not $hit) { throw 'code was requested but no SMS found in Mailpit' }
    "challenge $($otp.challenge_id.Substring(0, 6))... -> '$($hit.Subject)'"
}

Write-Host ''
if ($failed -gt 0) {
    Write-Host "$failed check(s) failed. Frontend fails are fine if you did not start it." -ForegroundColor Yellow
    exit 1
}
Write-Host 'All checks passed.' -ForegroundColor Green
