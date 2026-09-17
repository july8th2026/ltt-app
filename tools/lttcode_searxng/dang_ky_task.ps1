# Register the startup task that keeps the private SearXNG running (P06). ASCII only.
#
# OWNER runs this ONCE in an elevated PowerShell (it asks for the Windows password of
# the account that owns the WSL distro; the password is stored only by Task Scheduler):
#   pwsh -File tools\lttcode_searxng\dang_ky_task.ps1
#
# Why a task under the owner's account and not SYSTEM: Store WSL is not reachable from
# session 0 as SYSTEM (microsoft/WSL#9231); "run whether user is logged on or not"
# under the distro owner is the reported working setup.
param(
  [string]$Distro = 'Ubuntu',
  [int]$Port = 8888,
  [switch]$SkipFirewall
)
$ErrorActionPreference = 'Stop'
$taskName = 'LTT SearXNG (LTTCODE search)'
$wsl = Join-Path $env:ProgramFiles 'WSL\wsl.exe'
if (-not (Test-Path -LiteralPath $wsl)) { $wsl = (Get-Command wsl.exe).Source }

$cred = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message "Windows password for the task '$taskName' (stored by Task Scheduler only)"
$action = New-ScheduledTaskAction -Execute $wsl -Argument "-d $Distro -u root -- /usr/local/searxng/chay.sh"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 `
  -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
  -User $cred.UserName -Password $cred.GetNetworkCredential().Password -RunLevel Limited -Force | Out-Null
$cred = $null

if (-not $SkipFirewall) {
  # Defence in depth: nothing outside this machine may reach the SearXNG port.
  if (-not (Get-NetFirewallRule -DisplayName 'LTT SearXNG block inbound' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'LTT SearXNG block inbound' -Direction Inbound -Protocol TCP `
      -LocalPort $Port -RemoteAddress Any -Action Block -Profile Any | Out-Null
  }
}

Start-ScheduledTask -TaskName $taskName
Write-Host "Task '$taskName' registered and started. Check: pwsh -File tools\lttcode_searxng\kiem_tra.ps1"
