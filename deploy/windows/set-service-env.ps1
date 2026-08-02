<#
.SYNOPSIS
    Load C:\LTTPlatform\secrets\app.env into the Windows service
    environment (P9).

.DESCRIPTION
    NSSM stores service environment variables in the registry. This reads
    the protected app.env file and applies it, so secrets never appear in
    the service command line (visible to any user via Task Manager) and
    never live inside the release directory.

    Secret VALUES are never echoed - only variable names are printed.
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$ServiceName = 'LTTStudioWeb'
)

$ErrorActionPreference = 'Stop'

$envFile = Join-Path $Root 'secrets\app.env'
if (-not (Test-Path $envFile)) { throw "Secrets file not found: $envFile" }
$nssmCommand = Get-Command nssm.exe -ErrorAction SilentlyContinue
$nssmExe = if ($nssmCommand) { $nssmCommand.Source } else { Join-Path $Root 'tools\nssm.exe' }
if (-not (Test-Path $nssmExe)) { throw 'nssm.exe not found on PATH or under Root\tools.' }

$pairs   = @()
$missing = @()

foreach ($line in Get-Content $envFile) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
    $idx = $trimmed.IndexOf('=')
    if ($idx -lt 1) { continue }
    $name  = $trimmed.Substring(0, $idx).Trim()
    $value = $trimmed.Substring($idx + 1).Trim()
    if (-not $value) { $missing += $name; continue }
    $pairs += "$name=$value"
    Write-Host "  set $name" -ForegroundColor Green   # name only, never the value
}

if ($missing.Count -gt 0) {
    # Optional integrations intentionally use empty placeholders. Do not make
    # an unrelated rollout impossible; setup/4-nghiem-thu.ps1 separately
    # enforces the runtime secrets that are genuinely required.
    Write-Host "  skip empty: $($missing -join ', ')" -ForegroundColor Yellow
}

# NSSM expects the whole block as one multi-line AppEnvironmentExtra value.
& $nssmExe set $ServiceName AppEnvironmentExtra ($pairs -join "`n")
if ($LASTEXITCODE -ne 0) { throw 'nssm set AppEnvironmentExtra failed' }

Write-Host "`nApplied $($pairs.Count) variables to service $ServiceName." -ForegroundColor Cyan
Write-Host 'Restart the service for changes to take effect:' -ForegroundColor White
Write-Host "  Restart-Service $ServiceName" -ForegroundColor White
