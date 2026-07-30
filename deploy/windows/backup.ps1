<#
.SYNOPSIS
    Back up runtime data, configuration and key material (P7/P9).

.DESCRIPTION
    Scope follows docs/DATA_RETENTION_POLICY.md: databases, config,
    encrypted token stores and the audit log are included; the disposable
    video cache, session locks and rotating logs are excluded.

    The archive contains SECRET MATERIAL (encrypted token stores, and
    secrets\app.env if -IncludeSecrets is passed). Store it somewhere with
    the same protection as the server itself.
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Stamp = (Get-Date -Format 'yyyyMMdd_HHmmss'),
    [switch]$IncludeSecrets
)

$ErrorActionPreference = 'Stop'

$dataDir = Join-Path $Root 'data'
$backups = Join-Path $Root 'backups'
$staging = Join-Path $env:TEMP "ltt_backup_$Stamp"

if (-not (Test-Path $dataDir)) { throw "Data directory not found: $dataDir" }
if (-not (Test-Path $backups)) { New-Item -ItemType Directory -Path $backups -Force | Out-Null }

New-Item -ItemType Directory -Path $staging -Force | Out-Null

# Included: authoritative state. Excluded: anything regenerable.
$patterns = @('config.json', 'workers.json', '*.enc', '*.db', '*.sqlite3', 'audit_log.jsonl')
$copied = 0
foreach ($p in $patterns) {
    Get-ChildItem -Path $dataDir -Filter $p -File -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item $_.FullName -Destination $staging -Force
        $copied++
    }
}

if ($IncludeSecrets) {
    $envFile = Join-Path $Root 'secrets\app.env'
    if (Test-Path $envFile) {
        Copy-Item $envFile -Destination (Join-Path $staging 'app.env') -Force
        $copied++
        Write-Host '  [!] Secrets INCLUDED - protect this archive accordingly.' -ForegroundColor Yellow
    }
}

if ($copied -eq 0) {
    # An empty data directory is a legitimate state (fresh install, before
    # any config or token exists) - not an error. Throwing here used to
    # abort update.ps1 entirely, because update.ps1 backs up before it
    # touches anything. Warn and succeed instead.
    Remove-Item $staging -Recurse -Force
    Write-Host '  [SKIP] Khong co du lieu de sao luu (cai moi) - bo qua.' -ForegroundColor Yellow
    exit 0
}

$archive = Join-Path $backups "ltt_data_$Stamp.zip"
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $archive -Force
Remove-Item $staging -Recurse -Force

# Verify the archive is readable before reporting success - an unverified
# backup is not a backup.
$entries = [IO.Compression.ZipFile]::OpenRead($archive).Entries.Count
Write-Host "  [OK] Backup written: $archive ($entries entries, $copied files)" -ForegroundColor Green

# Retention: keep the 14 most recent archives.
Get-ChildItem -Path $backups -Filter 'ltt_data_*.zip' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 14 |
    ForEach-Object { Remove-Item $_.FullName -Force; Write-Host "  pruned $($_.Name)" }
