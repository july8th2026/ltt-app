<#
.SYNOPSIS
    One-time prerequisites for Windows Server 2016 (P9).

.DESCRIPTION
    Server 2016 differs from 2019+ in one important way: the OpenSSH
    Feature-on-Demand does not exist, so `Add-WindowsCapability -Name
    OpenSSH.Server` fails with "capability not found". This script
    installs OpenSSH from the official Microsoft Win32-OpenSSH GitHub
    release instead, then prepares everything else the deployment needs.

    Safe to re-run: every step checks before acting.

    Run this ONCE, in an Administrator PowerShell, over RDP.

.PARAMETER PublicKey
    The SSH public key allowed to administer this server.
#>
[CmdletBinding()]
param(
    [string]$PublicKey = '',
    [string]$PythonVersion = '3.12.10'
)

$ErrorActionPreference = 'Stop'

function Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK] $m"   -ForegroundColor Green }
function Warn($m) { Write-Host "  [!] $m"    -ForegroundColor Yellow }

# Server 2016's PowerShell defaults to TLS 1.0 for web requests, which
# GitHub and python.org both refuse. Without this every download fails
# with an unhelpful "connection closed" error.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Step 'Checking Windows version'
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "  $($os.Caption)  build $($os.BuildNumber)"
Write-Host "  PowerShell $($PSVersionTable.PSVersion)"
if ($PSVersionTable.PSVersion.Major -lt 5) {
    throw "PowerShell 5.0+ required. Install WMF 5.1 first."
}
Ok 'Version supported'

# ---------------------------------------------------------------- Python
Step 'Python'
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    $v = (& python --version 2>&1) -replace 'Python\s*',''
    Write-Host "  Found Python $v at $($py.Source)"
    Ok 'Python already installed'
} else {
    # 3.12 rather than 3.13: 3.12 is the last line explicitly tested
    # against Server 2016's Windows 10 1607 kernel.
    $url = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
    $exe = "$env:TEMP\python-installer.exe"
    Write-Host "  Downloading Python $PythonVersion ..."
    Invoke-WebRequest -Uri $url -OutFile $exe -UseBasicParsing
    Write-Host '  Installing (silent, all users, added to PATH) ...'
    Start-Process -FilePath $exe -Wait -ArgumentList @(
        '/quiet','InstallAllUsers=1','PrependPath=1','Include_test=0'
    )
    Remove-Item $exe -Force -ErrorAction SilentlyContinue
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine')
    Ok "Python $PythonVersion installed"
}

# --------------------------------------------------------------- OpenSSH
Step 'OpenSSH Server'
if (Get-Service sshd -ErrorAction SilentlyContinue) {
    Ok 'sshd already installed'
} else {
    Write-Host '  Add-WindowsCapability is unavailable on Server 2016 -'
    Write-Host '  installing from the Microsoft Win32-OpenSSH release.'

    # Resolve the latest release asset instead of pinning a version that
    # will rot.
    $api  = 'https://api.github.com/repos/PowerShell/Win32-OpenSSH/releases/latest'
    $rel  = Invoke-RestMethod -Uri $api -UseBasicParsing -Headers @{ 'User-Agent' = 'ltt-deploy' }
    $asset = $rel.assets | Where-Object { $_.name -eq 'OpenSSH-Win64.zip' } | Select-Object -First 1
    if (-not $asset) { throw 'Could not find OpenSSH-Win64.zip in the latest release.' }

    $zip = "$env:TEMP\OpenSSH-Win64.zip"
    Write-Host "  Downloading $($rel.tag_name) ..."
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing

    $dest = 'C:\Program Files\OpenSSH'
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    # Expand-Archive exists on PS 5.0+; Server 2016 ships 5.1.
    Expand-Archive -Path $zip -DestinationPath 'C:\Program Files' -Force
    if (-not (Test-Path $dest)) {
        # Some releases nest the files one level deeper.
        $inner = Get-ChildItem 'C:\Program Files' -Directory -Filter 'OpenSSH*' | Select-Object -First 1
        if ($inner -and $inner.FullName -ne $dest) { Rename-Item $inner.FullName $dest }
    }
    Remove-Item $zip -Force -ErrorAction SilentlyContinue

    & powershell.exe -ExecutionPolicy Bypass -File "$dest\install-sshd.ps1" | Out-Null
    Ok 'sshd installed'
}

Set-Service -Name sshd     -StartupType Automatic
Set-Service -Name ssh-agent -StartupType Automatic -ErrorAction SilentlyContinue
Start-Service sshd
Ok 'sshd running and set to auto-start'

Step 'Firewall rule for SSH'
if (-not (Get-NetFirewallRule -Name sshd -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (TCP 22)' `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
    Ok 'Port 22 opened'
} else { Ok 'Rule already present' }

Step 'Default shell for SSH sessions'
# Without this an SSH session lands in cmd.exe and every PowerShell
# command sent by the deployment tooling fails.
if (-not (Test-Path 'HKLM:\SOFTWARE\OpenSSH')) {
    New-Item -Path 'HKLM:\SOFTWARE\OpenSSH' -Force | Out-Null
}
New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell `
    -Value 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' `
    -PropertyType String -Force | Out-Null
Ok 'PowerShell set as default SSH shell'

# ------------------------------------------------------------ public key
Step 'Authorised key'
if (-not $PublicKey) {
    Warn 'No -PublicKey given; skipping. Re-run with -PublicKey "ssh-ed25519 AAAA..."'
} else {
    # Accounts in the Administrators group use this file, NOT
    # C:\Users\<name>\.ssh\authorized_keys.
    $f = 'C:\ProgramData\ssh\administrators_authorized_keys'
    New-Item -ItemType Directory -Path 'C:\ProgramData\ssh' -Force | Out-Null
    if ((Test-Path $f) -and (Select-String -Path $f -SimpleMatch $PublicKey -Quiet)) {
        Ok 'Key already authorised'
    } else {
        Add-Content -Path $f -Value $PublicKey
        Ok 'Key added'
    }
    # OpenSSH silently ignores this file if non-admins can write to it.
    icacls $f /inheritance:r /grant 'Administrators:F' /grant 'SYSTEM:F' | Out-Null
    Ok 'Permissions tightened'
    Restart-Service sshd
}

Step 'Summary'
Get-Service sshd | Select-Object Name, Status, StartType | Format-Table -AutoSize
Write-Host "  Python : $(& python --version 2>&1)"
Write-Host "  User   : $(whoami)"
Write-Host ''
Write-Host '  Public IPv4 addresses of this server:' -ForegroundColor Cyan
Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object IPAddress, InterfaceAlias | Format-Table -AutoSize
Write-Host '  Send the IP + username to continue the deployment.' -ForegroundColor Cyan
