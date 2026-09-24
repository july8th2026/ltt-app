# fw_localuser.ps1 - Do HUONG 1: luat tuong lua outbound theo SID nguoi dung / theo duong dan chuong trinh.
#
# CANH BAO - MAY NAY LA MAY SAN XUAT.
#   * Moi luat deu HEP: chi mot dia chi dich /32, chi TCP, chi cong 80/443, chi chieu RA.
#   * Ten luat deu bat dau bang "p6b-spike-" de go sach chac chan.
#   * Khoi finally LUON go luat, ke ca khi co loi hay bi ngat.
#   * Go tay neu can:  Get-NetFirewallRule -DisplayName 'p6b-spike-*' | Remove-NetFirewallRule
#
# Dung: powershell -NoProfile -ExecutionPolicy Bypass -File fw_localuser.ps1 -Stage <thu-muc-dan-dung> -Ip4 <ip>

param(
    [Parameter(Mandatory = $true)][string]$Stage,
    [Parameter(Mandatory = $true)][string]$Ip4
)

$ErrorActionPreference = 'Stop'
# Duong dan DAI: -Program tu choi dang ten ngan 8.3 (THANGT~1) voi loi Win32 87.
$Stage = (Get-Item -LiteralPath $Stage).FullName
$node = Join-Path $Stage 'node.exe'
$sid = ([Security.Principal.WindowsIdentity]::GetCurrent()).User.Value
$sddl = "D:(A;;CC;;;$sid)"
# DOI CHUNG AM: mot SID KHAC hoan toan (NT AUTHORITY\LOCAL SERVICE).
# Neu luat gan SID nay VAN chan probe cua ta thi dieu kien LocalUser dang bi BO QUA
# va luat thuc te ap cho ca may - phai biet dieu do truoc khi khuyen nghi bat cu gi.
$sddlKhac = 'D:(A;;CC;;;S-1-5-19)'

function Thu-Probe {
    param([string]$Nhan, [string]$Piece, [string]$Mode)
    $env:MODE = $Mode
    $env:IP4 = $Ip4
    $env:IP6 = ''
    $out = & $node --preserve-symlinks-main (Join-Path $Stage $Piece) 2>&1 | Out-String
    $line = ($out -split "`r?`n" | Where-Object { $_ -match '^(REACHED|BLOCKED|SKIP|CHILD_)' } | Select-Object -Last 1)
    if (-not $line) { $line = ($out -replace "`r?`n", ' | ').Trim() }
    Write-Output ("{0,-34} {1,-16} {2,-11} -> {3}" -f $Nhan, $Piece, $Mode, $line)
}

function Go-Luat {
    $r = Get-NetFirewallRule -DisplayName 'p6b-spike-*' -ErrorAction SilentlyContinue
    if ($r) { $r | Remove-NetFirewallRule; Write-Output ("DA GO " + $r.Count + " luat p6b-spike-*") }
    else { Write-Output 'KHONG con luat p6b-spike-* nao' }
}

try {
    Write-Output '===== 0) Truoc khi dat luat (doi chung) ====='
    Thu-Probe 'L0-truoc' 'probe.js' 'tcp_rawip'
    Thu-Probe 'L0-truoc' 'piece-spawn-node.js' 'tcp_rawip'
    Thu-Probe 'L0-truoc' 'piece-spawn-curl.js' 'tcp_rawip'

    Write-Output ''
    Write-Output '===== 1) Luat theo SID NGUOI DUNG (-LocalUser) ====='
    Write-Output ("SDDL = " + $sddl)
    New-NetFirewallRule -DisplayName 'p6b-spike-localuser' -Direction Outbound -Action Block `
        -RemoteAddress $Ip4 -Protocol TCP -RemotePort 80, 443 -LocalUser $sddl -Profile Any | Out-Null
    Thu-Probe 'L1a-localuser' 'probe.js' 'tcp_rawip'
    Thu-Probe 'L1a-localuser' 'piece-spawn-node.js' 'tcp_rawip'
    Thu-Probe 'L1a-localuser' 'piece-spawn-curl.js' 'tcp_rawip'
    Get-NetFirewallRule -DisplayName 'p6b-spike-localuser' | Remove-NetFirewallRule

    Write-Output ''
    Write-Output '===== 1b) DOI CHUNG AM: cung luat do, nhung gan cho SID KHAC (LOCAL SERVICE) ====='
    Write-Output ("SDDL = " + $sddlKhac)
    New-NetFirewallRule -DisplayName 'p6b-spike-localuser-khac' -Direction Outbound -Action Block `
        -RemoteAddress $Ip4 -Protocol TCP -RemotePort 80, 443 -LocalUser $sddlKhac -Profile Any | Out-Null
    Thu-Probe 'L1a-doi-chung-am(SID khac)' 'probe.js' 'tcp_rawip'
    Thu-Probe 'L1a-doi-chung-am(SID khac)' 'piece-spawn-node.js' 'tcp_rawip'
    Get-NetFirewallRule -DisplayName 'p6b-spike-localuser-khac' | Remove-NetFirewallRule

    Write-Output ''
    Write-Output '===== 2) Luat theo DUONG DAN CHUONG TRINH (-Program) ====='
    Write-Output ("Program = " + $node)
    New-NetFirewallRule -DisplayName 'p6b-spike-program' -Direction Outbound -Action Block `
        -RemoteAddress $Ip4 -Protocol TCP -RemotePort 80, 443 -Program $node -Profile Any | Out-Null
    Thu-Probe 'L1b-program' 'probe.js' 'tcp_rawip'
    Thu-Probe 'L1b-program' 'piece-spawn-node.js' 'tcp_rawip'
    Thu-Probe 'L1b-program' 'piece-spawn-curl.js' 'tcp_rawip'
}
finally {
    Write-Output ''
    Write-Output '===== GO SACH ====='
    Go-Luat
    Get-NetFirewallRule -DisplayName 'p6b-spike-*' -ErrorAction SilentlyContinue | Select-Object DisplayName
}
