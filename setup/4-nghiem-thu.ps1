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

Head 'LTT VOICE (neu da cai)'
# App nay chi kiem khi da cai. Chua cai KHONG phai loi: nen tang chay duoc ma
# khong co giong noi, va the app se tu hien "can thiet lap".
$voiceSvc = Get-Service 'LTTStudioVoice' -ErrorAction SilentlyContinue
if (-not $voiceSvc) {
    Write-Host '  [BO QUA] Chua cai dich vu giong noi' -ForegroundColor Yellow
} else {
    if ($voiceSvc.Status -ne 'Running') { Bad "LTTStudioVoice dang $($voiceSvc.Status)" }
    else { Ok 'LTTStudioVoice dang chay' }

    # /live KHONG can khoa - mot phep tham do song/chet khong nen phai mang bi mat.
    $vport = 8120
    $envF = Join-Path $secrets 'app.env'
    if (Test-Path $envF) {
        $m = (Select-String -Path $envF -Pattern '^LTT_VOICE_SIDECAR_PORT=(\d+)' -ErrorAction SilentlyContinue)
        if ($m) { $vport = [int]$m.Matches[0].Groups[1].Value }
    }
    try {
        $lv = Invoke-RestMethod "http://127.0.0.1:$vport/live" -TimeoutSec 10
        if ($lv.ok) { Ok "Cong giong tra loi tren 127.0.0.1:$vport" }
        else { Bad "Cong giong tra $($lv | ConvertTo-Json -Compress)" }
    } catch { Bad "Cong giong khong tra loi: $($_.Exception.Message)" }

    # LAN JOB `voice` TRONG DOI HINH WORKER.
    #
    #    platform_core/jobs.py loc bang
    #        set(manifest.requires).issubset(capabilities)
    #    App LTT VOICE khai requires=("voice",). Neu LTT_WORKER_POOLS DA duoc dat
    #    ma KHONG co lan `voice` thi job nam `queued` MAI MAI -- khong loi, khong
    #    canh bao, /health/ready van 200. Day la chot duy nhat bat duoc dieu do.
    if (Test-Path $envF) {
        $pools = (Select-String -Path $envF -Pattern '^LTT_WORKER_POOLS=(.*)$' -ErrorAction SilentlyContinue)
        if (-not $pools) {
            Ok 'LTT_WORKER_POOLS khong dat - worker da nang, job voice nhat duoc'
        } elseif ($pools.Matches[0].Groups[1].Value -match 'voice') {
            Ok 'LTT_WORKER_POOLS co lan voice'
        } else {
            Bad "LTT_WORKER_POOLS dat ma KHONG co lan 'voice' - job LTT VOICE se nam queued mai mai, khong loi nao bao. Them 'voice:1'."
        }
    }
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
    # !!!! PHEP KIEM NAY TRUOC 2026-08-27 DO NHAM THU.
    #
    # No chi tim `Users|Everyone`. Mot ACE TUONG MINH cho mot tai khoan nguoi
    # dung cu the (vd `DESKTOP-XXX\Thang Tuong`) khong khop ca hai, nen no in
    # `Ok 'Quyen secrets\ da siet'` trong khi ACL van ho. Do duoc 27/08: day la
    # cho THU BA cung noi mot cau sai, sau `2-cai-dat.ps1` va thong bao cua no.
    #
    # Cach dung la DANH SACH CHO PHEP: bat ky chu the nao ngoai danh sach deu la
    # mot van de, khong can doan truoc ten no.
    $chuThePhep = @('SYSTEM', 'Administrators', 'TrustedInstaller')
    $thua = @((Get-Acl $secrets).Access |
        ForEach-Object { ($_.IdentityReference.Value -split '\\')[-1] } |
        Where-Object { $chuThePhep -notcontains $_ } | Select-Object -Unique)
    if ($thua.Count -gt 0) {
        Bad "secrets\ con cho $($thua -join ', ') truy cap"
    } else { Ok 'Quyen secrets\ chi con SYSTEM + Administrators' }
} else { Bad 'THIEU secrets\app.env' }

# ============================================================================
Head 'Khoa SSH cua dich vu (VPS)'
# !!!! VI SAO BUOC NAY O DAY.
#
# 27/08 mot khach tra 1.490 credit va nhan ve chu "Loi": ba dich vu chay bang
# LocalSystem, con khoa SSH nam trong ho so nguoi dung noi ACL cho ca tai khoan
# ay - tu goc nhin SYSTEM do la khoa "ho" va OpenSSH TU CHOI dung no.
#
# Loi do IM LANG hoan toan: /vps van ban, /health/ready van 200, gate van xanh.
# Tin hieu duy nhat la mot khach da tra tien. Nghiem thu la cho phai biet dieu
# do, khong phai luc co khach.
$vpsBat = (Test-Path (Join-Path $secrets 'app.env')) -and
          ((Get-Content (Join-Path $secrets 'app.env') -Raw) -match '(?m)^LTT_VPS=1\s*$')
if (-not $vpsBat) {
    Ok 'LTT_VPS tat - bo qua'
} elseif (-not (Test-Path $venvPy)) {
    Warn 'Khong thay venv python - bo qua kiem khoa dich vu'
} else {
    & $venvPy (Join-Path $Root 'app\tools\vps_kiem_khoa.py') 2>&1 | ForEach-Object {
        Write-Host "    $_"
    }
    if ($LASTEXITCODE -eq 0) { Ok 'Khoa dich vu: quyen dung, noi duoc' }
    else { Bad "Khoa dich vu co van de (ma $LASTEXITCODE) - xem dong tren" }
}

Head 'Cau hinh'
# KIEM data\config.json DA BO 2026-08-25 (Q108): tep do la cau hinh cua app
# socialbot, va app do da bi go han. Nen tang khong doc tep cau hinh nao luc
# khoi dong - moi thu nam trong secrets\app.env, da kiem o muc tren.
Ok 'Nen tang khong doc tep cau hinh - da kiem secrets\app.env o tren'

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

Head 'Ban dang chay co dung la ban trong git khong'
# Cap nhat XOA VA THAY TOAN BO app\, nen cau hoi nay chi co hai dap an: khop
# het, hoac ai do da deploy de len. Truoc phep so nay, cach duy nhat de tra loi
# la MO TRANG RA NHIN, va cai do chi nhin duoc nhung trang khong can dang nhap.
#
# Do 27/08: 446 tep khop, 1 lech. Tep lech la `apps/vps/routes.py`, va cho lech
# dung la bo loc giau IP LAN noi bo khoi nhat ky khach xem duoc. Ban sua da
# commit, chua deploy. Khong trang nao bao gi, `/health/ready` van 200.
$soSanh = Join-Path $PSScriptRoot '..\tools\so_deploy.py'
if ((Test-Path $venvPy) -and (Test-Path $soSanh)) {
    $out = & $venvPy $soSanh 2>&1 | Out-String
    $dong = ($out -split "`n") | Where-Object { $_.Trim() }
    $tomTat = $dong | Where-Object { $_ -match '^khop:' } | Select-Object -First 1
    if ($LASTEXITCODE -eq 0) {
        Ok "  $tomTat"
    } elseif ($LASTEXITCODE -eq 2) {
        Warn '  Khong thay C:\LTTPlatform\app - chua cai?'
    } else {
        Bad "  $tomTat"
        $dong | Where-Object { $_ -match '^\s+(LECH|THIEU|THUA)' } |
            Select-Object -First 10 | ForEach-Object { Write-Host "    $_" }
        Write-Host '    Ban dang phuc vu khach KHONG phai ban trong git.' -ForegroundColor Yellow
    }
} else { Warn '  Bo qua: khong co venv hoac tools\so_deploy.py' }

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
