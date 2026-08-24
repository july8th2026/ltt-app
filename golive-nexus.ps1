# LTT Nexus go-live: enable Nexus + billing, then deploy (copy app + migrate + restart).
# RUN THIS IN AN ELEVATED PowerShell (Run as Administrator).
# It is idempotent and safe to re-run. Data in C:\LTTPlatform\data is untouched.

$ErrorActionPreference = 'Stop'
$repo      = 'D:\LTTSTUDIOSAPP'
$envFile   = 'C:\LTTPlatform\secrets\app.env'
$relayNote = 'C:\LTTPlatform\secrets\nexus_relay_config.txt'

function Write-Head($m) { Write-Host ''; Write-Host "=== $m ===" -ForegroundColor Cyan }

# --- 0. must be elevated ---
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) {
  Write-Host 'ERROR: not elevated. Right-click PowerShell -> Run as Administrator, then re-run this script.' -ForegroundColor Red
  exit 1
}

# --- 1. append Nexus env to app.env (idempotent, NO BOM) ---
Write-Head '1/3  Configure app.env (enable Nexus + billing 50 credit/device/month)'
$text = [IO.File]::ReadAllText($envFile)
$keys = @{}
foreach ($line in ($text -split "`n")) {
  if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') { $keys[$matches[1]] = $true }
}
$eol = if ($text -match "`r`n") { "`r`n" } else { "`n" }
$add = @()
if (-not $keys.ContainsKey('LTT_NEXUS'))               { $add += 'LTT_NEXUS=1' }
if (-not $keys.ContainsKey('LTT_NEXUS_GIA_MAY_THANG')) { $add += 'LTT_NEXUS_GIA_MAY_THANG=50' }
$secret = $null
if (-not $keys.ContainsKey('LTT_NEXUS_RELAY_SECRET')) {
  $b = New-Object byte[] 36
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
  $secret = ([Convert]::ToBase64String($b)) -replace '[+/=]', ''
  $add += "LTT_NEXUS_RELAY_SECRET=$secret"
}
if ($add.Count -gt 0) {
  if ($text.Length -gt 0 -and -not $text.EndsWith("`n")) { $text += $eol }
  $text += $eol + '# --- LTT Nexus go-live (Q101/Q98) ---' + $eol + ($add -join $eol) + $eol
  [IO.File]::WriteAllText($envFile, $text, (New-Object Text.UTF8Encoding($false)))
  $names = ($add | ForEach-Object { ($_ -split '=')[0] }) -join ', '
  Write-Host "  added: $names" -ForegroundColor Green
} else {
  Write-Host '  app.env already has all Nexus keys - unchanged.' -ForegroundColor Yellow
}

# relay config note (contains the shared secret) for the Vultr hbbs side
if ($secret) {
  $note = @"
LTT Nexus - RELAY (hbbs fork) config on Vultr 45.76.185.75
==========================================================
Set these env vars for the hbbs process (fork LThbbs):

  LTT_NEXUS_RELAY_CHECK_URL=https://app.lttstudios.com/nexus/relay-check
  LTT_NEXUS_RELAY_SECRET=$secret

This secret MUST match LTT_NEXUS_RELAY_SECRET in C:\LTTPlatform\secrets\app.env.
hbbs sends it as header X-LTT-Relay-Secret to /relay-check; the platform is
fail-closed: missing secret -> /relay-check returns 404.

This file contains a SECRET - do not commit or copy off-machine.
"@
  [IO.File]::WriteAllText($relayNote, $note, (New-Object Text.UTF8Encoding($false)))
  Write-Host "  wrote relay config (with the shared secret): $relayNote" -ForegroundColor Green
}

# --- 2. confirm before touching the running service ---
Write-Head '2/3  Deploy new code (this replaces C:\LTTPlatform\app, runs DB migration, restarts services)'
Write-Host '  Data/ is preserved. Old app becomes app.previous (rollback available).'
$ans = Read-Host '  Proceed with deploy now? (yes/no)'
if ($ans -ne 'yes') { Write-Host 'Stopped before deploy. app.env is already configured; re-run to deploy.' -ForegroundColor Yellow; exit 0 }

# --- 3. run the sanctioned update ---
Write-Head '3/3  Running setup\2-cai-dat.ps1'
Set-Location $repo
& powershell -NoProfile -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1
Write-Host ''
Write-Host 'DONE. Verify:' -ForegroundColor Green
Write-Host '  - https://app.lttstudios.com/health/ready   (expect 200)'
Write-Host '  - https://app.lttstudios.com/tai-xuong       (Windows + Android downloadable)'
Write-Host '  - https://app.lttstudios.com/nexus/version.json'
Write-Host ''
Write-Host 'Relay-side billing teeth: configure the Vultr hbbs using' -ForegroundColor Cyan
Write-Host "  $relayNote"
