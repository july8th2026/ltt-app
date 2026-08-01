<#
.SYNOPSIS
    Buoc 2 - Cai dat tai cho tu chinh folder nay. Chay lai duoc nhieu lan.

.DESCRIPTION
    Khac voi deploy\windows\install.ps1 (can file zip), script nay cai TRUC
    TIEP tu folder da copy sang. Dung khi ban chep ca thu muc sang may moi.

    Tu dong lam:
      - tao C:\LTTPlatform (data, secrets, logs, backups) va copy code
      - tao venv rieng, cai thu vien
      - TU SINH cac bi mat (session secret, khoa ma hoa token, mat khau admin)
      - tai NSSM neu chua co
      - dang ky va khoi dong dich vu Windows

    An toan khi chay lai: KHONG BAO GIO ghi de data\config.json,
    secrets\app.env, hay khoa ma hoa da co.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [int]$Port = 8100,
    [string]$ServiceName = 'LTTStudioWeb',
    [string]$WorkerServiceName = 'LTTStudioWorker',
    [string]$AdminUser = 'admin'
)

$ErrorActionPreference = 'Stop'
function Head($m) { Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Note($m) { Write-Host "  $m" -ForegroundColor Yellow }

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw 'Can quyen Administrator. Mo PowerShell bang Run as administrator.' }

$src     = Split-Path -Parent $PSScriptRoot
$appDir  = Join-Path $Root 'app'
$dataDir = Join-Path $Root 'data'
$secrets = Join-Path $Root 'secrets'
$logs    = Join-Path $Root 'logs'
$backups = Join-Path $Root 'backups'
$tools   = Join-Path $Root 'tools'
$venv    = Join-Path $Root 'venv'
$venvPy  = Join-Path $venv 'Scripts\python.exe'

# Ghi file KHONG BOM. PowerShell 5.1 mac dinh chen BOM, va BOM lam
# json.load() vo -> /health/ready tra 503 trong khi dich vu van chay binh
# thuong. Loi nay da that su xay ra o du an nay.
function Write-NoBom($path, $text) {
    [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
}

Head 'Tao cau truc thu muc'
foreach ($d in @($Root, $dataDir, $secrets, $logs, $backups, $tools)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}
Ok "Da tao $Root"

Head 'Copy ma nguon'
# Dung dich vu truoc khi dong vao app\. Khi chay LAI tren may dang phuc vu that,
# python.exe cua service khoa file trong app\ -> Move-Item/robocopy that bai
# (loi "being used by another process"). Script se cai lai + khoi dong o cuoi.
Stop-Service $WorkerServiceName -Force -ErrorAction SilentlyContinue
Stop-Service $ServiceName -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
# Giu ban truoc de rollback duoc.
if (Test-Path $appDir) {
    $prev = Join-Path $Root 'app.previous'
    if (Test-Path $prev) { Remove-Item $prev -Recurse -Force }
    Move-Item $appDir $prev
    Ok "Ban cu chuyen sang app.previous (dung de rollback)"
}
New-Item -ItemType Directory -Path $appDir -Force | Out-Null
# /XD: khong copy du lieu van hanh, bi mat, cache. Chung song o ngoai app\
# (ADR-009) de cap nhat code khong dong vao du lieu.
$rc = robocopy $src $appDir /E /NFL /NDL /NJH /NJS /NP `
      /XD data secrets logs .venv venv __pycache__ .pytest_cache .git dist build temp_videos `
      /XF *.pyc *.log
if ($LASTEXITCODE -ge 8) { throw "robocopy loi (ma $LASTEXITCODE)" }
$global:LASTEXITCODE = 0
$n = (Get-ChildItem $appDir -Recurse -File).Count
Ok "Da copy $n file vao $appDir"

Head 'Tai nguyen nguon di kem code'
# data\translations va data\assets la TAI NGUYEN NGUON (ban dich giao dien,
# logo TikTok cho audit), khong phai du lieu van hanh - phai di theo code.
foreach ($sub in @('translations', 'assets')) {
    $s = Join-Path $src "data\$sub"
    if (Test-Path $s) {
        $d = Join-Path $dataDir $sub
        robocopy $s $d /E /NFL /NDL /NJH /NJS /NP | Out-Null
        $global:LASTEXITCODE = 0
        Ok "data\$sub"
    }
}

Head 'Moi truong Python'
if (-not (Test-Path $venvPy)) {
    & python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Tao venv that bai' }
    Ok 'Da tao venv'
} else { Ok 'venv da co' }
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r (Join-Path $appDir 'requirements.txt') --quiet
& $venvPy -m pip install -r (Join-Path $appDir 'requirements-server.txt') --quiet
Ok 'Da cai thu vien'

Head 'Cau hinh van hanh'
$cfg = Join-Path $dataDir 'config.json'
if (Test-Path $cfg) {
    Ok 'config.json da co - GIU NGUYEN (khong ghi de cau hinh that cua ban)'
} else {
    Copy-Item (Join-Path $appDir 'config.example.json') $cfg -Force
    Ok 'Tao config.json tu config.example.json'
    Note 'CAN LAM: sua Sheet ID, ten cot, va thong tin app trong data\config.json'
}

Head 'Siet quyen thu muc bi mat'
icacls $secrets /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" | Out-Null
Ok 'Chi SYSTEM va Administrators doc duoc secrets\'

Head 'Sinh bi mat'
$envFile = Join-Path $secrets 'app.env'
$newPassword = $null
if (Test-Path $envFile) {
    Ok 'app.env da co - GIU NGUYEN'
    Note 'Neu mat mat khau admin: xoa dong LTT_ADMIN_PASSWORD_HASH roi chay lai script nay.'
} else {
    # Sinh ngau nhien bang thu vien mat ma cua Python, khong dung Get-Random.
    $sessionSecret = & $venvPy -c "import secrets;print(secrets.token_urlsafe(32))"
    $tokenKey      = & $venvPy -c "import secrets;print(secrets.token_urlsafe(32))"
    $newPassword   = & $venvPy -c "import secrets,string;a=string.ascii_letters+string.digits;print(''.join(secrets.choice(a) for _ in range(20)))"
    $hash = & $venvPy -c "import sys;sys.path.insert(0,r'$appDir');from server.auth.password_hashing import hash_password;print(hash_password(sys.argv[1]))" $newPassword
    if (-not $hash) { throw 'Khong tao duoc hash mat khau' }

    $lines = @(
        '# LTT AI Studio - bi mat production. KHONG BAO GIO commit file nay.',
        'LTT_ENV=production',
        "LTT_ADMIN_USERNAME=$AdminUser",
        "LTT_ADMIN_PASSWORD_HASH=$hash",
        "LTT_SESSION_SECRET=$sessionSecret",
        "LTT_TOKEN_ENCRYPTION_KEY=$tokenKey",
        "LTT_DATA_DIR=$dataDir",
        "LTT_SECRETS_DIR=$secrets",
        "LTT_LOGS_DIR=$logs"
    )
    Write-NoBom $envFile ($lines -join "`r`n")
    Ok 'Da sinh app.env voi bi mat ngau nhien'
}

Head 'PostgreSQL'
# CSDL cua nen tang (quyet dinh Q2). Cai dat va tao database + role rieng.
# Chay lai duoc nhieu lan: da co thi dung lai, KHONG BAO GIO ghi de mat khau
# hay du lieu dang co.
$pgBin = $null
foreach ($v in @('18','17','16','15','14')) {
    $p = "C:\Program Files\PostgreSQL\$v\bin"
    if (Test-Path (Join-Path $p 'psql.exe')) { $pgBin = $p; break }
}
if (-not $pgBin) {
    $cmd = Get-Command psql.exe -ErrorAction SilentlyContinue
    if ($cmd) { $pgBin = Split-Path $cmd.Source }
}

if ($pgBin) {
    Ok "PostgreSQL da co: $pgBin"
} else {
    Note 'Chua co PostgreSQL - dang cai bang winget...'
    $wg = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wg) {
        throw 'Khong co winget va cung khong co PostgreSQL. Cai PostgreSQL thu cong roi chay lai script nay.'
    }
    # Mat khau superuser sinh ngau nhien va CHI dung luc cai. Ung dung khong
    # dung tai khoan nay - no chay bang role rieng tao o duoi.
    $pgSuper = & $venvPy -c "import secrets,string;a=string.ascii_letters+string.digits;print(''.join(secrets.choice(a) for _ in range(24)))"
    winget install --id PostgreSQL.PostgreSQL.17 --silent --accept-package-agreements --accept-source-agreements --override "--mode unattended --unattendedmodeui none --superpassword $pgSuper --serverport 5432" 2>&1 | Out-Null
    foreach ($v in @('18','17','16','15','14')) {
        $p = "C:\Program Files\PostgreSQL\$v\bin"
        if (Test-Path (Join-Path $p 'psql.exe')) { $pgBin = $p; break }
    }
    if (-not $pgBin) { throw 'Cai PostgreSQL that bai - khong tim thay psql.exe' }
    # Ghi lai mat khau superuser vao secrets\ de con vao bao tri CSDL sau nay.
    Write-NoBom (Join-Path $secrets 'postgres-superuser.txt') $pgSuper
    Ok 'Da cai PostgreSQL. Mat khau superuser luu o secrets\postgres-superuser.txt'
}

Head 'CSDL cua ung dung'
# Tao database + role RIENG cho ung dung. Ung dung khong bao gio chay bang
# tai khoan superuser: mot lo hong SQL injection voi quyen superuser doc duoc
# moi database tren may, con voi role rieng thi chi trong pham vi cua no.
$envText = if (Test-Path $envFile) { Get-Content $envFile -Raw } else { '' }
if ($envText -match '(?m)^LTT_DATABASE_URL=') {
    Ok 'LTT_DATABASE_URL da co trong app.env - GIU NGUYEN'
} else {
    $superFile = Join-Path $secrets 'postgres-superuser.txt'
    if (-not (Test-Path $superFile)) {
        Note 'Khong co mat khau superuser PostgreSQL (CSDL nay da co truoc khi cai).'
        Note 'CAN LAM THU CONG - chay 2 lenh sau bang tai khoan postgres:'
        Note '  CREATE ROLE ltt_app LOGIN PASSWORD ''<dat-mat-khau>'';'
        Note '  CREATE DATABASE lttplatform OWNER ltt_app;'
        Note 'Roi them dong nay vao secrets\app.env:'
        Note '  LTT_DATABASE_URL=postgresql+psycopg://ltt_app:<mat-khau>@127.0.0.1:5432/lttplatform'
    } else {
        $superPw = (Get-Content $superFile -Raw).Trim()
        $appPw   = & $venvPy -c "import secrets,string;a=string.ascii_letters+string.digits;print(''.join(secrets.choice(a) for _ in range(24)))"
        $psql    = Join-Path $pgBin 'psql.exe'
        $env:PGPASSWORD = $superPw

        # Tao role neu chua co. DO_ block de chay lai duoc nhieu lan.
        $sqlRole = "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='ltt_app') THEN CREATE ROLE ltt_app LOGIN PASSWORD '$appPw'; END IF; END `$`$;"
        & $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -v ON_ERROR_STOP=1 -c $sqlRole | Out-Null
        if ($LASTEXITCODE -ne 0) { $env:PGPASSWORD=$null; throw 'Tao role ltt_app that bai' }

        # CREATE DATABASE khong chay duoc trong DO block -> kiem tra roi tao.
        $coDb = & $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='lttplatform'"
        if ($coDb -ne '1') {
            & $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -v ON_ERROR_STOP=1 -c 'CREATE DATABASE lttplatform OWNER ltt_app;' | Out-Null
            if ($LASTEXITCODE -ne 0) { $env:PGPASSWORD=$null; throw 'Tao database lttplatform that bai' }
            Ok 'Da tao database lttplatform'
        } else {
            Ok 'Database lttplatform da co'
            # Da co database nhung chua co dong trong app.env -> mat khau cu
            # khong con biet. Dat lai de hai ben khop nhau.
            & $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -v ON_ERROR_STOP=1 -c "ALTER ROLE ltt_app PASSWORD '$appPw';" | Out-Null
        }
        $env:PGPASSWORD = $null

        $url = "postgresql+psycopg://ltt_app:$appPw@127.0.0.1:5432/lttplatform"
        Write-NoBom $envFile ($envText.TrimEnd() + "`r`n" + "LTT_DATABASE_URL=$url" + "`r`n")
        Ok 'Da tao role + database va ghi LTT_DATABASE_URL vao app.env'
    }
}

Head 'Di tru luoc do CSDL'
# Chay migration TRUOC khi khoi dong dich vu: dich vu khoi dong voi luoc do cu
# se loi o request dau tien chu khong loi luc khoi dong - kho truy hon nhieu.
$envText = if (Test-Path $envFile) { Get-Content $envFile -Raw } else { '' }
if ($envText -match '(?m)^LTT_DATABASE_URL=(.+)$') {
    $env:LTT_DATABASE_URL = $Matches[1].Trim()
    Push-Location $appDir
    & $venvPy -m alembic upgrade head
    $rc = $LASTEXITCODE
    Pop-Location
    $env:LTT_DATABASE_URL = $null
    if ($rc -ne 0) { throw 'alembic upgrade head that bai - xem thong bao o tren' }
    Ok 'Luoc do CSDL da o ban moi nhat'
} else {
    Note 'Bo qua migration - chua co LTT_DATABASE_URL'
}

Head 'NSSM (trinh quan ly dich vu)'
$nssmExe = Join-Path $tools 'nssm.exe'
if (-not (Test-Path $nssmExe)) {
    $cmd = Get-Command nssm.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        Copy-Item $cmd.Source $nssmExe -Force
        Ok 'Lay nssm.exe tu PATH'
    } else {
        Note 'Dang tai NSSM...'
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $zip = Join-Path $env:TEMP 'nssm.zip'
        $ex  = Join-Path $env:TEMP 'nssm-extract'
        Invoke-WebRequest 'https://nssm.cc/release/nssm-2.24.zip' -OutFile $zip -UseBasicParsing
        if (Test-Path $ex) { Remove-Item $ex -Recurse -Force }
        Expand-Archive $zip $ex -Force
        $found = Get-ChildItem $ex -Recurse -Filter nssm.exe |
                 Where-Object { $_.FullName -match 'win64' } | Select-Object -First 1
        if (-not $found) { throw 'Khong tim thay nssm.exe trong file tai ve' }
        Copy-Item $found.FullName $nssmExe -Force
        Remove-Item $zip, $ex -Recurse -Force -ErrorAction SilentlyContinue
        Ok 'Da tai va cai NSSM'
    }
} else { Ok 'nssm.exe da co' }

Head 'Dang ky dich vu Windows'
$existing = Get-Service $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.Status -eq 'Running') { Stop-Service $ServiceName -Force; Start-Sleep -Seconds 2 }
    Ok "Dich vu $ServiceName da co - cap nhat cau hinh"
} else {
    & $nssmExe install $ServiceName $venvPy "-m uvicorn server.run:app --host 127.0.0.1 --port $Port" | Out-Null
    Ok "Da tao dich vu $ServiceName"
}
# AppDirectory PHAI la app\ - mot so duong dan trong code tinh theo thu muc
# lam viec. Sai cho nay thi dich vu chay nhung moi trang tra 500.
& $nssmExe set $ServiceName AppDirectory   $appDir | Out-Null
& $nssmExe set $ServiceName AppStdout      (Join-Path $logs 'service-out.log') | Out-Null
& $nssmExe set $ServiceName AppStderr      (Join-Path $logs 'service-err.log') | Out-Null
& $nssmExe set $ServiceName AppRotateFiles 1 | Out-Null
# Xoay log theo KICH THUOC, khong chi khi restart (AppRotateFiles mot minh de log
# phong to vo han giua hai lan restart). AppRotateOnline 1 = xoay khi dang chay;
# AppRotateBytes 10MB = moi file toi 10MB roi xoay.
& $nssmExe set $ServiceName AppRotateOnline 1 | Out-Null
& $nssmExe set $ServiceName AppRotateBytes 10485760 | Out-Null
& $nssmExe set $ServiceName Start          SERVICE_AUTO_START | Out-Null
& $nssmExe set $ServiceName AppExit Default Restart | Out-Null
& $nssmExe set $ServiceName AppRestartDelay 10000 | Out-Null

# Nap bi mat vao moi truong cua dich vu. Doc lai tu app.env moi lan chay de
# lan chay lai cung cap nhat duoc thay doi.
$envPairs = @()
foreach ($line in (Get-Content $envFile)) {
    $t = $line.Trim()
    if ($t -and -not $t.StartsWith('#') -and $t.Contains('=')) { $envPairs += $t }
}
& $nssmExe set $ServiceName AppEnvironmentExtra ($envPairs -join "`r`n") | Out-Null
Ok 'Da nap bi mat vao moi truong dich vu'

Head 'Dich vu Worker (hang doi job)'
# Worker chay TIEN TRINH RIENG voi web (Q6): job nang khong lam cham web, va
# cap nhat web khong giet job dang chay. Cung AppDirectory, cung bi mat.
$existingW = Get-Service $WorkerServiceName -ErrorAction SilentlyContinue
if ($existingW) {
    if ($existingW.Status -eq 'Running') { Stop-Service $WorkerServiceName -Force; Start-Sleep -Seconds 2 }
    Ok "Dich vu $WorkerServiceName da co - cap nhat cau hinh"
} else {
    & $nssmExe install $WorkerServiceName $venvPy 'job_worker.py' | Out-Null
    Ok "Da tao dich vu $WorkerServiceName"
}
& $nssmExe set $WorkerServiceName AppDirectory   $appDir | Out-Null
& $nssmExe set $WorkerServiceName AppStdout      (Join-Path $logs 'worker-out.log') | Out-Null
& $nssmExe set $WorkerServiceName AppStderr      (Join-Path $logs 'worker-err.log') | Out-Null
& $nssmExe set $WorkerServiceName AppRotateFiles 1 | Out-Null
& $nssmExe set $WorkerServiceName AppRotateOnline 1 | Out-Null
& $nssmExe set $WorkerServiceName AppRotateBytes 10485760 | Out-Null
& $nssmExe set $WorkerServiceName Start          SERVICE_AUTO_START | Out-Null
& $nssmExe set $WorkerServiceName AppExit Default Restart | Out-Null
& $nssmExe set $WorkerServiceName AppRestartDelay 10000 | Out-Null
& $nssmExe set $WorkerServiceName AppEnvironmentExtra ($envPairs -join "`r`n") | Out-Null
Ok 'Da nap bi mat vao moi truong worker'

Head 'Khoi dong'
Start-Service $ServiceName
Start-Sleep -Seconds 6
$svc = Get-Service $ServiceName
if ($svc.Status -ne 'Running') {
    Write-Host "  [LOI] Dich vu web khong chay. Xem log:" -ForegroundColor Red
    Get-Content (Join-Path $logs 'service-err.log') -Tail 25 -ErrorAction SilentlyContinue
    throw 'Dich vu web khoi dong that bai'
}
Ok "Dich vu $ServiceName dang chay"

Start-Service $WorkerServiceName
Start-Sleep -Seconds 3
$svcW = Get-Service $WorkerServiceName
if ($svcW.Status -ne 'Running') {
    Write-Host "  [LOI] Dich vu worker khong chay. Xem log:" -ForegroundColor Red
    Get-Content (Join-Path $logs 'worker-err.log') -Tail 25 -ErrorAction SilentlyContinue
    throw 'Dich vu worker khoi dong that bai'
}
Ok "Dich vu $WorkerServiceName dang chay"

Head 'Kiem tra suc khoe'
$okHealth = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $r = Invoke-RestMethod "http://127.0.0.1:$Port/health/ready" -TimeoutSec 5
        Write-Host "  status=$($r.status) environment=$($r.environment)"
        $okHealth = ($r.status -eq 'ready'); break
    } catch { Start-Sleep -Seconds 2 }
}
if ($okHealth) { Ok 'Ung dung san sang' }
else { Note 'Chua ready - thuong do config.json chua dien. Xem logs\service-err.log' }

Write-Host ""
Write-Host ("-" * 62)
if ($newPassword) {
    Write-Host "MAT KHAU ADMIN (chi hien MOT LAN, luu lai ngay):" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    Tai khoan : $AdminUser"
    Write-Host "    Mat khau  : $newPassword"
    Write-Host ""
    Write-Host "Mat khau khong luu o dau ca - chi luu dang hash." -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "Buoc tiep theo:" -ForegroundColor Cyan
Write-Host "  1. Sua $dataDir\config.json (Sheet ID, ten cot, thong tin app)"
Write-Host "  2. Chay: .\setup\3-cloudflare.ps1   (can ban dang nhap Cloudflare)"
Write-Host "  3. Chay: .\setup\4-nghiem-thu.ps1"
Write-Host ""
Write-Host "QUAN TRONG: sao luu $secrets\app.env ra cho an toan." -ForegroundColor Yellow
Write-Host "Mat LTT_TOKEN_ENCRYPTION_KEY la mat toan bo token Facebook/TikTok da luu." -ForegroundColor Yellow
