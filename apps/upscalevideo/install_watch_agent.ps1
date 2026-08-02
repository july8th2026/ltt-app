param(
  [ValidateSet("install", "uninstall")][string]$Action,
  [string]$WatchFolder,
  [string]$StateDir = "$env:ProgramData\LTT Studios\Upscale Watch Agent",
  [string]$BaseUrl = "https://app.lttstudios.com"
)

$ErrorActionPreference = "Stop"
$taskName = "LTT Upscale Watch Agent"

if ($Action -eq "uninstall") {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
  [Environment]::SetEnvironmentVariable("LTT_UPSCALE_WATCH_TOKEN", $null, "User")
  Write-Host "Watch Agent task removed. Source and state files were not deleted."
  exit 0
}

if (-not (Test-Path -LiteralPath $WatchFolder -PathType Container)) {
  throw "WatchFolder must be an existing directory."
}
if (-not $env:LTT_UPSCALE_WATCH_TOKEN) {
  throw "Set LTT_UPSCALE_WATCH_TOKEN in the service account environment first."
}
[Environment]::SetEnvironmentVariable("LTT_UPSCALE_WATCH_TOKEN", $env:LTT_UPSCALE_WATCH_TOKEN, "User")

$python = (Get-Command pythonw.exe).Source
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$args = "-m apps.upscalevideo.watch_agent --folder `"$WatchFolder`" --state-dir `"$StateDir`" --base-url `"$BaseUrl`""
$action = New-ScheduledTaskAction -Execute $python -Argument $args -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "Watch Agent task installed. Token value was not printed."
