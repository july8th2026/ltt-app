<#
.SYNOPSIS
    Buoc 4 - Nghiem thu toan he thong. Chi doc, khong thay doi gi.

.DESCRIPTION
    Kiem tra dung nhung thu de hong ma khong bao loi ro rang.
    Chay lai bat cu luc nao, nhat la sau moi lan cap nhat.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\4-nghiem-thu.ps1
#>
[CmdletBinding()]
param(
    [string]$Hostname = 'app.lttstudios.com',
    [string]$Root = 'C:\LTTPlatform',
    [int]$Port = 8100
)

$ErrorActionPreference = 'Continue'
$script:Fail = 0
$script:Warn = 0
function Head($m) { Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK]   $m" -ForegroundColor Green }
function Bad($m)  { Write-Host "  [LOI]  $m" -ForegroundColor Red;    $script:Fail++ }
function Warn($m) { Write-Host "  [CANH] $m" -ForegroundColor Yellow; $script:Warn++ }

$appDir  = Join-Path $Root 'app'
$dataDir = Join-Path $Root 'data'
$secrets = Join-Path $Root 'secrets'
$logs    = Join-Path $Root 'logs'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'

Head 'Dich vu'
foreach ($s in @('LTTStudioWeb', 'LTTStudioWorker', 'cloudflared')) {
    $svc = Get-Service $s -ErrorAction SilentlyContinue
    if (-not $svc) { Bad "Khong co dich vu $s" }
    elseif ($svc.Status -ne 'Running') { Bad "$s dang $($svc.Status)" }
    else { Ok "$s dang chay" }
}

Head 'App tra loi tren loopback'
try {
    $r = Invoke-RestMethod "http://127.0.0.1:$Port/health/ready" -TimeoutSec 10
    if ($r.status -eq 'ready') { Ok "ready (environment=$($r.environment))" }
    else { Bad "health/ready tra status=$($r.status)" }
} catch { Bad "Khong goi duoc health/ready tren loopback: $($_.Exception.Message)" }

Head 'Cong ung dung chi nghe loopback'
# Neu nghe 0.0.0.0 thi ai cung goi thang vao app duoc, bo qua Cloudflare.
$listen = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listen) {
    $addrs = ($listen | Select-Object -ExpandProperty LocalAddress -Unique) -join ', '
    if ($addrs -match '0\.0\.0\.0|::') { Bad "Dang nghe $addrs - PHAI chi nghe 127.0.0.1" }
    else { Ok "Chi nghe $addrs" }
} else { Bad "Khong co gi nghe cong $Port" }

Head 'Vao duoc tu Internet'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
try {
    $r = Invoke-RestMethod "https://$Hostname/health/ready" -TimeoutSec 15
    Ok "https://$Hostname -> status=$($r.status)"
} catch { Bad "Khong vao duoc https://$Hostname : $($_.Exception.Message)" }

Head 'Catalog cong khai'
try {
    $r = Invoke-WebRequest "https://$Hostname/" -TimeoutSec 15 -UseBasicParsing -MaximumRedirection 5
    if ($r.Content -match 'id="catsearch"' -and $r.Content -match 'class="appcard"') {
        Ok 'Catalog cong khai hien ra'
    } else { Bad 'Vao duoc nhung khong thay catalog app' }
} catch { Bad "Khong tai duoc trang chu: $($_.Exception.Message)" }

Head 'Tai lieu API bi chan o production'
# /docs liet ke toan bo route va tham so - do an cho ke tan cong.
try {
    $r = Invoke-WebRequest "https://$Hostname/docs" -TimeoutSec 10 -UseBasicParsing `
         -ErrorAction SilentlyContinue
    if ($r.StatusCode -eq 200) { Bad '/docs dang MO - phai bi chan ngoai development' }
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 404) { Ok '/docs tra 404 (dung)' }
    else { Warn "/docs tra $($_.Exception.Response.StatusCode.value__)" }
}

Head 'Bi mat'
if (Test-Path (Join-Path $secrets 'app.env')) {
    Ok 'co secrets\app.env'
    $txt = Get-Content (Join-Path $secrets 'app.env') -Raw
    $missing = @()
    foreach ($k in @('LTT_SESSION_SECRET', 'LTT_TOKEN_ENCRYPTION_KEY')) {
        if ($txt -notmatch "(?m)^$k=\S") { $missing += $k }
    }
    if ($missing.Count -gt 0) { Bad "Chua dien: $($missing -join ', ')" }
    else { Ok 'Da co du bi mat runtime bat buoc' }
    if ($txt -match '(?m)^LTT_ENV=(production|prod)\s*$') {
        if ($txt -match '(?m)^LTT_ADMIN_PASSWORD_HASH=\S') {
            Bad 'Production con bat admin-env; Q29 yeu cau vo hieu duong nay'
        } else { Ok 'Admin-env da vo hieu o production (Q29)' }
    }
    $acl = (Get-Acl $secrets).Access | Where-Object { $_.IdentityReference -match 'Users|Everyone' }
    if ($acl) { Warn 'secrets\ con cho Users/Everyone truy cap' } else { Ok 'Quyen secrets\ da siet' }
} else { Bad 'THIEU secrets\app.env' }

Head 'Cau hinh'
$cfg = Join-Path $dataDir 'config.json'
if (Test-Path $cfg) {
    $bytes = [IO.File]::ReadAllBytes($cfg)[0..2]
    if ($bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) {
        # Code doc bang utf-8-sig nen van chay, nhung sua bang cong cu khac
        # thi de vo. Bao de biet.
        Warn 'config.json co BOM - nen ghi lai khong BOM'
    } else { Ok 'config.json khong BOM' }
    try {
        $j = Get-Content $cfg -Raw | ConvertFrom-Json
        $n = ($j.PSObject.Properties | Measure-Object).Count
        Ok "config.json doc duoc, $n khoa"
        $todo = @()
        foreach ($k in @('sheet_id', 'google_credentials_path')) {
            if ("$($j.$k)" -match 'REPLACE_ME|^$') { $todo += $k }
        }
        if ($todo.Count -gt 0) { Warn "Chua dien that: $($todo -join ', ')" }
    } catch { Bad "config.json khong phai JSON hop le: $($_.Exception.Message)" }
} else { Bad 'THIEU data\config.json' }

Head 'App da nap'
if (Test-Path $venvPy) {
    Push-Location $appDir
    $out = & $venvPy -c "from platform_core.registry import discover; d=discover(); print(len(d)); [print(a.manifest.slug, a.manifest.route_prefix, a.error or 'ok') for a in d]" 2>&1
    Pop-Location
    if ($LASTEXITCODE -eq 0) {
        $lines = @($out)
        Ok "$($lines[0]) app da nap"
        foreach ($l in $lines[1..($lines.Count - 1)]) {
            if ($l -match 'ok$') { Ok "  $l" } else { Bad "  $l" }
        }
    } else { Bad "Khong nap duoc registry: $out" }
} else { Bad "Khong co $venvPy" }

Head 'Log gan day'
$errLog = Join-Path $logs 'service-err.log'
if (Test-Path $errLog) {
    $tail = Get-Content $errLog -Tail 40 -ErrorAction SilentlyContinue
    $errs = $tail | Where-Object { $_ -match 'Traceback|CRITICAL|ERROR' }
    if ($errs) {
        Warn "Co $($errs.Count) dong loi trong 40 dong cuoi:"
        $errs | Select-Object -First 5 | ForEach-Object { Write-Host "    $_" }
    } else { Ok 'Khong co loi trong log gan day' }
}

Write-Host ""
Write-Host ("-" * 62)
if ($script:Fail -gt 0) {
    Write-Host "KET QUA: $($script:Fail) loi, $($script:Warn) canh bao" -ForegroundColor Red
    exit 1
} elseif ($script:Warn -gt 0) {
    Write-Host "KET QUA: chay duoc, con $($script:Warn) canh bao" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "KET QUA: he thong hoan chinh." -ForegroundColor Green
    Write-Host "Vao https://$Hostname de dung." -ForegroundColor Green
    exit 0
}
