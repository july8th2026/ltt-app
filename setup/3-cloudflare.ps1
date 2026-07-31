<#
.SYNOPSIS
    Buoc 3 - Dung Cloudflare Tunnel de app.lttstudios.com tro ve may nay.

.DESCRIPTION
    Claude chay duoc gan het script nay. Chi CO MOT buoc can ban:
    dang nhap Cloudflare bang trinh duyet (buoc 2 ben duoi). Script se DUNG
    LAI, in ra duong link, cho ban lam xong roi tu chay tiep.

    Tunnel khong can mo cong tren may, khong can IP tinh.

    BA GIOI HAN cua Cloudflare anh huong den cach viet app (goi Free/Pro):
      - Upload toi da 100 MB moi request. Lon hon bi tra HTTP 413 TRUOC KHI
        toi may chu.
      - Cho phan hoi toi da 100 giay. Lau hon bi loi 524 du bot van chay tot.
        Vi vay moi viec dai PHAI di qua hang doi job.
      - Serve video/file lon khong host tren Cloudflare bi han che theo ToS.
    Khi cham cac tran nay: chuyen file sang R2, sua o platform_core\storage.py.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\3-cloudflare.ps1 -Hostname app.lttstudios.com
#>
[CmdletBinding()]
param(
    [string]$Hostname = 'app.lttstudios.com',
    [string]$TunnelName = 'ltt-app',
    [string]$Root = 'C:\LTTPlatform',
    [int]$Port = 8100,
    [switch]$DisableCaddy
)

$ErrorActionPreference = 'Stop'
function Head($m) { Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Note($m) { Write-Host "  $m" -ForegroundColor Yellow }

# Chay cloudflared va gom ca stdout+stderr thanh CHUOI ma KHONG coi stderr la loi.
# cloudflared ghi log INF ra stderr; voi ErrorActionPreference='Stop', neu dung
# 2>&1 (gop vao pipeline) thi dong stderr bien thanh NativeCommandError va lam
# DUNG script du lenh da chay xong (da that su xay ra o buoc 5/6 route dns).
# Cach chac chan: chuyen stderr ra FILE (2>$f) nen no khong bao gio thanh error
# record trong pipeline, roi doc lai gop vao. Kiem ket qua qua chuoi tra ve.
function Invoke-Cf {
    param([Parameter(ValueFromRemainingArguments = $true)]$CfArgs)
    # HAI lop bao ve, deu can:
    #  - EAP='Continue': stderr cua native KHONG thanh loi dung script (bat buoc;
    #    thieu no la crash du da 2> ra file - da xay ra o lan chay truoc).
    #  - 2> $errFile: chuyen stderr ra file nen khong hien dong do tren man hinh.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $errFile = [IO.Path]::GetTempFileName()
    try {
        $out = (& $cfExe @CfArgs 2> $errFile | Out-String)
        $err = (Get-Content $errFile -Raw -ErrorAction SilentlyContinue)
        return (("$out`n$err").Trim())
    } finally {
        $ErrorActionPreference = $prev
        Remove-Item $errFile -Force -ErrorAction SilentlyContinue
    }
}

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw 'Can quyen Administrator.' }

$tools = Join-Path $Root 'tools'
$cfDir = Join-Path $Root 'cloudflare'
$logs  = Join-Path $Root 'logs'
$cfExe = Join-Path $tools 'cloudflared.exe'
foreach ($d in @($tools, $cfDir, $logs)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

function Write-NoBom($path, $text) {
    [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
}

Head '1/6 Tai cloudflared'
if (Test-Path $cfExe) {
    Ok "Da co: $(& $cfExe --version 2>&1 | Select-Object -First 1)"
} else {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $url = 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe'
    Note "Dang tai tu $url"
    Invoke-WebRequest $url -OutFile $cfExe -UseBasicParsing
    Ok "Da tai: $(& $cfExe --version 2>&1 | Select-Object -First 1)"
}

Head '2/6 Dang nhap Cloudflare  <-- CAN BAN LAM'
# DIEU KIEN TIEN QUYET (quyet dinh Q27 - chuyen ca zone sang Cloudflare):
#   TRUOC khi chay buoc nay, ban phai da:
#   1. Them "lttstudios.com" nhu mot SITE trong Cloudflare (goi Free);
#   2. Kiem DU ban ghi DNS hien co (@ /www /app...), de @ va www o "DNS only";
#   3. Doi nameserver o nha dang ky ten mien sang 2 NS Cloudflare cap;
#   4. Doi zone bao "Active" o Cloudflare.
# Doi NS KHONG chuyen hosting - trang chu van o inet.vn OnePanel.
# Neu chua lam, xem docs/05_LEN_MANG_CLOUDFLARE.md truoc.
$zone = ($Hostname -split '\.')[-2..-1] -join '.'   # app.lttstudios.com -> lttstudios.com
$cert = Join-Path $env:USERPROFILE '.cloudflared\cert.pem'
if (Test-Path $cert) {
    Ok 'Da dang nhap tu truoc (co cert.pem)'
} else {
    Write-Host ""
    Write-Host "  Lenh ben duoi se in ra MOT DUONG LINK." -ForegroundColor Yellow
    Write-Host "  Mo link tren trinh duyet BAT KY MAY NAO, dang nhap Cloudflare," -ForegroundColor Yellow
    Write-Host "  va chon zone '$zone' (ca ten mien - da chuyen sang Cloudflare)." -ForegroundColor Yellow
    Write-Host "  Xong thi script tu chay tiep." -ForegroundColor Yellow
    Write-Host ""
    & $cfExe tunnel login
    if (-not (Test-Path $cert)) { throw 'Dang nhap chua xong - khong thay cert.pem. Chay lai script.' }
    Ok 'Dang nhap thanh cong'
}

Head '3/6 Tao tunnel'
$list = Invoke-Cf tunnel list
if ($list -match [regex]::Escape($TunnelName)) {
    Ok "Tunnel '$TunnelName' da ton tai"
} else {
    & $cfExe tunnel create $TunnelName
    if ($LASTEXITCODE -ne 0) { throw "Tao tunnel that bai" }
    Ok "Da tao tunnel '$TunnelName'"
}

# Lay tunnel ID tu danh sach - dang tin hon la doc output luc tao.
$list = Invoke-Cf tunnel list
$tunnelId = $null
foreach ($line in $list -split "`n") {
    if ($line -match "^([0-9a-f\-]{36})\s+$([regex]::Escape($TunnelName))\s") { $tunnelId = $Matches[1]; break }
}
if (-not $tunnelId) { throw "Khong doc duoc tunnel ID cua '$TunnelName'" }
Ok "Tunnel ID: $tunnelId"

# File credentials mac dinh nam trong %USERPROFILE%\.cloudflared - chuyen vao
# cho co dinh de dich vu (chay bang tai khoan khac) van doc duoc.
$credSrc = Join-Path $env:USERPROFILE ".cloudflared\$tunnelId.json"
$credDst = Join-Path $cfDir "$tunnelId.json"
if ((Test-Path $credSrc) -and -not (Test-Path $credDst)) {
    Move-Item $credSrc $credDst
    Ok 'Da chuyen file credentials vao C:\LTTPlatform\cloudflare'
}
if (-not (Test-Path $credDst)) { throw "Khong tim thay credentials: $credDst" }
icacls $cfDir /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" | Out-Null

Head '4/6 Ghi cau hinh'
$cfgPath = Join-Path $cfDir 'config.yml'
$cfg = @"
# Sinh tu dong boi setup\3-cloudflare.ps1
tunnel: $tunnelId
credentials-file: $credDst

loglevel: info
logfile: $logs\cloudflared.log
retries: 5
grace-period: 30s

ingress:
  - hostname: $Hostname
    service: http://127.0.0.1:$Port
    originRequest:
      connectTimeout: 30s
      tcpKeepAlive: 30s
      disableChunkedEncoding: false

  # Quy tac cuoi bat buoc - thieu la cloudflared tu choi khoi dong.
  - service: http_status:404
"@
# KHONG dung Out-File: PowerShell 5.1 chen BOM va cloudflared se khong doc
# duoc dong dau tien cua YAML.
Write-NoBom $cfgPath $cfg
Ok "Da ghi $cfgPath (khong BOM)"

Head '5/6 Tro ten mien'
# route dns tao ban ghi trong ZONE cua Cloudflare. Neu zone '$Hostname' chua
# duoc them + uy quyen (dieu kien tien quyet Q22), lenh nay se bao khong tim
# thay zone - bat loi do va giai thich, thay vi de mot loi mo mit.
$routeOut = Invoke-Cf tunnel route dns $TunnelName $Hostname
Write-Host $routeOut.Trim()
if ($routeOut -match 'already exists|record with that host') {
    Note 'Ban ghi da co tu truoc - giu nguyen.'
} elseif ($routeOut -match 'could not find zone|zone not found|no zone|failed to add') {
    throw ("Khong tim thay zone cho '$Hostname' o Cloudflare. Ban da chuyen " +
           "'$zone' sang Cloudflare (doi nameserver) va doi zone bao Active chua? " +
           "Xem docs/05_LEN_MANG_CLOUDFLARE.md (quyet dinh Q27).")
}
Ok "$Hostname -> tunnel $TunnelName"

Head '6/6 Cai dich vu Windows (qua NSSM)'
# KHONG dung `cloudflared service install`: ban 2026.x tao service voi ImagePath
# TRAN (khong tham so) -> service chay nhung khong biet chay tunnel/config nao
# -> tunnel KHONG ket noi -> loi 1033/530. NSSM cho ta kiem soat DUNG dong lenh
# (--config <path> tunnel run), giong cach cai LTTStudioWeb/Worker o setup\2.
$nssmExe = Join-Path $tools 'nssm.exe'
if (-not (Test-Path $nssmExe)) {
    throw "Khong thay $nssmExe. Chay setup\2-cai-dat.ps1 truoc (buoc do tai NSSM)."
}
$svcName = 'cloudflared'

# Go moi ban dich vu cu (ke ca ban ImagePath tran do 'cloudflared service
# install' tao ra) de cai lai cho dung.
# KHONG dung Stop-Service: ban ImagePath tran khong xu ly tin hieu stop nen dich
# vu ket o StopPending va Stop-Service cho mai mai. Kill THANG tien trinh de xoa
# StopPending, roi go dich vu bang ca 3 cach cho chac.
$svc = Get-Service $svcName -ErrorAction SilentlyContinue
if ($svc) {
    Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    & $cfExe service uninstall 2> $null | Out-Null
    & $nssmExe remove $svcName confirm 2> $null | Out-Null
    & sc.exe delete $svcName 2> $null | Out-Null
    Start-Sleep -Seconds 3
    Ok 'Da go dich vu cloudflared cu'
}

# $cfgPath khong co dau cach nen khong can bao ngoac kep.
& $nssmExe install $svcName $cfExe "--config $cfgPath tunnel run" | Out-Null
& $nssmExe set $svcName AppDirectory   $cfDir | Out-Null
& $nssmExe set $svcName AppStdout      (Join-Path $logs 'cloudflared-nssm-out.log') | Out-Null
& $nssmExe set $svcName AppStderr      (Join-Path $logs 'cloudflared-nssm-err.log') | Out-Null
& $nssmExe set $svcName AppRotateFiles 1 | Out-Null
& $nssmExe set $svcName AppRotateOnline 1 | Out-Null
& $nssmExe set $svcName AppRotateBytes 10485760 | Out-Null
& $nssmExe set $svcName Start          SERVICE_AUTO_START | Out-Null
& $nssmExe set $svcName AppExit Default Restart | Out-Null
& $nssmExe set $svcName AppRestartDelay 10000 | Out-Null
Start-Service $svcName
Ok 'Da cai (NSSM) va khoi dong cloudflared'
Start-Sleep -Seconds 6
$svc = Get-Service $svcName
Ok "cloudflared: $($svc.Status)"

if ($DisableCaddy) {
    Head 'Tat Caddy'
    # Cloudflare lo phan HTTPS roi, giu them Caddy chi la mot tang co the hong.
    $caddy = Get-Service Caddy -ErrorAction SilentlyContinue
    if ($caddy) {
        Stop-Service Caddy -Force -ErrorAction SilentlyContinue
        Set-Service Caddy -StartupType Disabled
        Ok 'Da dung va tat Caddy'
    } else { Ok 'Khong co Caddy tren may nay' }
}

Head 'Kiem tra tu ben ngoai'
Note 'DNS can vai chuc giay de lan truyen.'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$reached = $false
for ($i = 1; $i -le 12; $i++) {
    try {
        $r = Invoke-RestMethod "https://$Hostname/health/ready" -TimeoutSec 10
        Write-Host "  status=$($r.status) environment=$($r.environment)"
        $reached = $true; break
    } catch {
        Write-Host "  lan $i/12 chua duoc, cho 10 giay..."
        Start-Sleep -Seconds 10
    }
}

Write-Host ""
Write-Host ("-" * 62)
if ($reached) {
    Write-Host "XONG. https://$Hostname da vao duoc." -ForegroundColor Green
    Write-Host "Chay tiep: .\setup\4-nghiem-thu.ps1" -ForegroundColor Cyan
} else {
    Write-Host "Tunnel da dung nhung chua goi duoc tu ben ngoai." -ForegroundColor Yellow
    Write-Host "Kiem tra theo thu tu:" -ForegroundColor Yellow
    Write-Host "  Get-Service cloudflared, LTTStudioWeb"
    Write-Host "  Get-Content $logs\cloudflared.log -Tail 30"
    Write-Host "  Invoke-RestMethod http://127.0.0.1:$Port/health/ready   # app co song khong"
    Write-Host ""
    Write-Host "  Loi 1033 = tunnel chua chay hoac DNS chua tro"
    Write-Host "  Loi 502  = tunnel chay nhung app chet"
}
