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
# DIEU KIEN TIEN QUYET (quyet dinh Q22 - uy quyen rieng subdomain):
#   TRUOC khi chay buoc nay, ban phai da:
#   1. Them "app.lttstudios.com" nhu mot SITE (zone) trong Cloudflare;
#   2. Lay 2 nameserver Cloudflare cap, them ban ghi NS cho "app" o inet.vn;
#   3. Doi DNS lan truyen (zone o Cloudflare bao "Active").
# Neu chua lam, xem docs/04_CLOUDFLARE_TUNNEL.md truoc.
$cert = Join-Path $env:USERPROFILE '.cloudflared\cert.pem'
if (Test-Path $cert) {
    Ok 'Da dang nhap tu truoc (co cert.pem)'
} else {
    Write-Host ""
    Write-Host "  Lenh ben duoi se in ra MOT DUONG LINK." -ForegroundColor Yellow
    Write-Host "  Mo link tren trinh duyet BAT KY MAY NAO, dang nhap Cloudflare," -ForegroundColor Yellow
    Write-Host "  va chon zone '$Hostname' (KHONG phai lttstudios.com goc -" -ForegroundColor Yellow
    Write-Host "  ta uy quyen rieng subdomain, xem quyet dinh Q22)." -ForegroundColor Yellow
    Write-Host "  Xong thi script tu chay tiep." -ForegroundColor Yellow
    Write-Host ""
    & $cfExe tunnel login
    if (-not (Test-Path $cert)) { throw 'Dang nhap chua xong - khong thay cert.pem. Chay lai script.' }
    Ok 'Dang nhap thanh cong'
}

Head '3/6 Tao tunnel'
$list = & $cfExe tunnel list 2>&1 | Out-String
if ($list -match [regex]::Escape($TunnelName)) {
    Ok "Tunnel '$TunnelName' da ton tai"
} else {
    & $cfExe tunnel create $TunnelName
    if ($LASTEXITCODE -ne 0) { throw "Tao tunnel that bai" }
    Ok "Da tao tunnel '$TunnelName'"
}

# Lay tunnel ID tu danh sach - dang tin hon la doc output luc tao.
$list = & $cfExe tunnel list 2>&1 | Out-String
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
$routeOut = & $cfExe tunnel route dns $TunnelName $Hostname 2>&1 | Out-String
Write-Host $routeOut.Trim()
if ($routeOut -match 'already exists|record with that host') {
    Note 'Ban ghi da co tu truoc - giu nguyen.'
} elseif ($routeOut -match 'could not find zone|zone not found|no zone|failed to add') {
    throw ("Khong tim thay zone cho '$Hostname' o Cloudflare. Ban da them " +
           "'$Hostname' nhu mot site va uy quyen NS o inet.vn chua? " +
           "Xem docs/04_CLOUDFLARE_TUNNEL.md (quyet dinh Q22).")
}
Ok "$Hostname -> tunnel $TunnelName"

Head '6/6 Cai dich vu Windows'
$svc = Get-Service cloudflared -ErrorAction SilentlyContinue
if ($svc) {
    Ok 'Dich vu cloudflared da co - khoi dong lai de nap cau hinh moi'
    Restart-Service cloudflared
} else {
    & $cfExe --config $cfgPath service install
    if ($LASTEXITCODE -ne 0) { throw 'Cai dich vu cloudflared that bai' }
    Start-Service cloudflared
    Ok 'Da cai va khoi dong cloudflared'
}
Start-Sleep -Seconds 5
$svc = Get-Service cloudflared
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
