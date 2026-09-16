param(
    [string]$MachineBHost = '192.168.2.66',
    [string]$MachineBUser = 'lengo',
    [string]$SshKeyPath = "$env:USERPROFILE\.ssh\nexus_b",
    [string]$KnownHostsPath = "$env:USERPROFILE\.ssh\known_hosts",
    [string]$Destination = 'C:\LTTPlatform\runtime\machine-b-ovh',
    [string]$ScriptRoot = 'C:\LTTPlatform\tools\vps',
    [int]$EveryMinutes = 10
)
# Registers the Machine B runtime mirror as a Scheduled Task.
# Why: create selection needs a Machine B generation younger than
# apps/vps/profiles.py RUNTIME_MAX_AGE_SECONDS (2 collector runs + one sync).
# Before 16/09 the mirror was only refreshed by hand, so sales closed.
# The sync script is copied OUTSIDE C:\LTTPlatform\app because app\ is
# replaced on every update. EveryMinutes must match RUNTIME_SYNC_SECONDS.
$ErrorActionPreference = 'Stop'
$TaskName = 'LTT_VPS_MachineB_Runtime_Sync'

foreach ($file in @($SshKeyPath, $KnownHostsPath)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Required transport file is missing: $file"
    }
}
New-Item -ItemType Directory -Force -Path $ScriptRoot | Out-Null
$source = Join-Path $PSScriptRoot 'Sync-MachineBRuntime.ps1'
$target = Join-Path $ScriptRoot 'Sync-MachineBRuntime.ps1'
Copy-Item -LiteralPath $source -Destination $target -Force
$log = Join-Path $ScriptRoot 'machine-b-sync.log'

$arguments = ('-NoProfile -ExecutionPolicy Bypass -Command "& ''{0}'' ' +
    '-MachineBHost {1} -MachineBUser {2} -SshKeyPath ''{3}'' ' +
    '-KnownHostsPath ''{4}'' -Destination ''{5}'' *>> ''{6}''"') -f `
    $target, $MachineBHost, $MachineBUser, $SshKeyPath, $KnownHostsPath,
    $Destination, $log

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes)
# S4U: runs without an interactive logon and without storing a password; the
# SSH key is a local file of this user, so no network credential is needed.
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Output "REGISTERED $TaskName every $EveryMinutes min -> $Destination"
