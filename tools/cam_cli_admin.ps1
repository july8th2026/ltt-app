param(
    [Parameter(Mandatory=$true)]
    [string]$Exe,
    [switch]$Elevated
)

# ASCII only. The ZIP method intentionally requires Administrator.
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    $script = $MyInvocation.MyCommand.Path
    $arg = '-NoProfile -ExecutionPolicy Bypass -File "' + $script +
           '" -Exe "' + $Exe + '" -Elevated'
    $p = Start-Process powershell.exe -Verb RunAs -ArgumentList $arg -Wait -PassThru
    exit $p.ExitCode
}

Write-Host 'Administrator: OK'
Write-Host ('Windows user: ' + $env:USERNAME)
Write-Host 'Configuration is still written for THIS Windows user (HKCU).'
Write-Host 'Do not use Run as different user, or it will configure the wrong profile.'

$launcher = Join-Path $PSScriptRoot 'cam_cli_launcher.ps1'
& $launcher -Exe $Exe
exit $LASTEXITCODE
