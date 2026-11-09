<#
.SYNOPSIS
  Close the Cloudflare tunnels opened by demo-up.ps1. Add -Stack to also stop the containers
  (data volumes are kept; add -Volumes to wipe them too).
#>
[CmdletBinding()]
param(
    [switch]$Stack,
    [switch]$Volumes,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PidFile = Join-Path $RepoRoot 'infra\.demo\tunnel-pids.txt'

if (Test-Path $PidFile) {
    foreach ($id in Get-Content $PidFile) {
        $p = Get-Process -Id $id -ErrorAction SilentlyContinue
        if ($p -and $p.ProcessName -like 'cloudflared*') {
            Stop-Process -Id $id -Force -Confirm:$false
            if (-not $Quiet) { Write-Host "Stopped tunnel (PID $id)" }
        }
    }
    Remove-Item $PidFile -Confirm:$false
} elseif (-not $Quiet) {
    Write-Host 'No tunnels recorded.'
}

if ($Stack) {
    $composeArgs = @('compose', '-f', (Join-Path $RepoRoot 'infra\docker-compose.yml'), '--profile', 'frontend', 'down')
    if ($Volumes) { $composeArgs += '-v' }
    & docker @composeArgs
}
