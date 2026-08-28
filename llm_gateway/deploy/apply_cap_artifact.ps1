param(
    [Parameter(Mandatory = $true)][string]$PatchPath,
    [string]$EnvPath = 'C:\ProgramData\LTTLlm\gateway.env',
    [switch]$Rollback
)

$ErrorActionPreference = 'Stop'
$backupPath = "$EnvPath.q115.previous"

if ($Rollback) {
    if (-not (Test-Path -LiteralPath $backupPath)) {
        throw "Rollback backup not found: $backupPath"
    }
    Copy-Item -LiteralPath $backupPath -Destination $EnvPath -Force
    Restart-Service -Name LTTLlmGateway -Force
    Write-Output 'ROLLBACK=PASS'
    exit 0
}

if (-not (Test-Path -LiteralPath $EnvPath)) {
    throw "Gateway environment not found: $EnvPath"
}
if (-not (Test-Path -LiteralPath $PatchPath)) {
    throw "Patch artifact not found: $PatchPath"
}

$updates = @{}
foreach ($line in [IO.File]::ReadAllLines($PatchPath)) {
    if ($line -match '^([A-Z0-9_]+)=(.*)$') {
        $updates[$Matches[1]] = $Matches[2]
    }
}
if ($updates.Count -eq 0) {
    throw 'Patch artifact has no KEY=VALUE entries'
}

$seen = @{}
$newLines = @(
    foreach ($line in [IO.File]::ReadAllLines($EnvPath)) {
        if ($line -match '^([A-Z0-9_]+)=') {
            $key = $Matches[1]
            if ($updates.ContainsKey($key)) {
                $seen[$key] = $true
                "$key=$($updates[$key])"
                continue
            }
        }
        $line
    }
)
foreach ($key in $updates.Keys) {
    if (-not $seen.ContainsKey($key)) {
        $newLines += "$key=$($updates[$key])"
    }
}

Copy-Item -LiteralPath $EnvPath -Destination $backupPath -Force
$tmpPath = "$EnvPath.q115.tmp"
[IO.File]::WriteAllText(
    $tmpPath,
    ($newLines -join "`n") + "`n",
    (New-Object Text.UTF8Encoding($false))
)
Move-Item -LiteralPath $tmpPath -Destination $EnvPath -Force
Restart-Service -Name LTTLlmGateway -Force
Start-Sleep -Seconds 3

$svc = Get-Service -Name LTTLlmGateway
if ($svc.Status -ne 'Running') {
    throw "LTTLlmGateway is not running after restart: $($svc.Status)"
}
Write-Output "SERVICE=$($svc.Status)"
Write-Output "ENV_SHA256=$((Get-FileHash -Algorithm SHA256 -LiteralPath $EnvPath).Hash)"
Write-Output "BACKUP_SHA256=$((Get-FileHash -Algorithm SHA256 -LiteralPath $backupPath).Hash)"
Write-Output 'TOKEN=preserved-not-printed'
