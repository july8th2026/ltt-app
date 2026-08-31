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

    An toan khi chay lai: KHONG BAO GIO ghi de du lieu van hanh,
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
# --------------------------------------------------------------- Invoke-Ngoai
# Voi `$ErrorActionPreference = 'Stop'`, MOT EXE NGOAI ghi ra stderr se thanh
# `NativeCommandError` va KET THUC script -- ngay ca khi exe do tra ve 0.
#
# pip, python, cloudflared va pg_dump deu ghi ra stderr trong luc chay binh
# thuong (canh bao, thanh tien trinh, mot dong chan doan). Hau qua khong phai
# "bao loi sai" ma la IM LANG: dong `if ($LASTEXITCODE -ne 0)` ngay sau do
# KHONG BAO GIO CHAY, script chet giua chung, va nhat ky dung lai o dong cuoi
# in duoc. Mot loi vo hai doc len giong het mot lan treo.
#
# Bay nay da dinh BON LAN trong hai ngay (30-31/08/2026): installer sidecar,
# `Test-Py`, `tai_khoan_thu.ps1`, roi buoc lam am HF cache.
#
# Boc loi goi lai: ha xuong 'Continue' dung trong khoi, roi tra lai. Khoi la
# `scriptblock` nen bien cua ham goi van thay duoc, va `$LASTEXITCODE` giu
# nguyen tu lenh cuoi -- moi phep kiem ma san co van dung.
function Invoke-Ngoai {
    param([Parameter(Mandatory = $true)][scriptblock]$Khoi)
    $truoc = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Khoi } finally { $ErrorActionPreference = $truoc }
}
function Head($m) { Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Canh($m) { Write-Host "  [!!] $m" -ForegroundColor Yellow }
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

Head 'Kiem ma nguon truoc khi dong vao ban dang chay'
# ---------------------------------------------------------------------------
# VI SAO CHOT NAY O DAY, VA O TRUOC Stop-Service
#
# Deploy la robocopy + alembic. Truoc 2026-08-25 KHONG co gi chan mot tep .py
# cut: neu ai do dang ghi do mot tep luc deploy chay, ban cut duoc chep thang
# sang production va dich vu khong khoi dong lai duoc.
#
# Khong phai gia thuyet. Ngay 25/08 gate bao [FAIL] "bien dich duoc" mot nhip
# roi tu xanh lai, khong ai sua gi o giua -- no bat dung luc mot tep dang duoc
# ghi. Hai phien Claude lam song song tren cung cay nguon, va do la trang thai
# binh thuong cua du an nay.
#
# Chot chay TRUOC `Stop-Service`: hong o day thi dich vu VAN DANG CHAY va
# khong ai mat gi. Dat sau do thi ta da tu tay tao ra downtime roi moi phat
# hien khong deploy duoc.
$pyKiem = $null
foreach ($ung in @($venvPy, 'python', 'py')) {
    if ($ung -and (Get-Command $ung -ErrorAction SilentlyContinue)) { $pyKiem = $ung; break }
}
if ($pyKiem) {
    # compileall: doc va bien dich MOI tep .py trong cay nguon. -q chi in loi.
    # /XD cua robocopy o duoi khong ap dung o day nen loai tay may thu muc lon.
    $bo = @('-m', 'compileall', '-q', '-j', '0',
            '-x', '(node_modules|\.git|\.venv|venv|__pycache__|dist|build)',
            $src)
    & $pyKiem @bo 2>&1 | Out-String -OutVariable kqKiem | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host $kqKiem -ForegroundColor Red
        throw "Co tep .py KHONG bien dich duoc. DUNG deploy, dich vu chua bi dung."
    }
    Ok "Toan bo .py bien dich duoc"
    $global:LASTEXITCODE = 0
} else {
    Canh "Khong tim thay python de kiem ma nguon - BO QUA chot bien dich"
}

Head 'WhisperX sidecar rieng'
# Sidecar nay chi phuc vu autosubvideo.
#
# !! CHUYEN LEN DAY 2026-08-30, TRUOC MOI `Stop-Service`.
#
#    Chu thich cu ngay tai cho nay da ghi: *"script da dung dich vu o tren,
#    nen mot loi o day de production nam im"* - tuc no BIET minh nam trong cua
#    so downtime, va chi ne bang try/catch. Ne mot loi thi production van nam
#    trong suot thoi gian no tai ve (torch ~3,5 GB). Chuyen di thi khong.
#
#    Cung ngay do, khoi cai `vieneu-venv` mac dung loi ay va lam production
#    nam 19 phut. `test_45::test_viec_dai_khong_nam_trong_cua_so_ngung_dich_vu`
#    gio chan ca hai.
#
#    Ngay 2026-08-05 buoc nay nem loi (xem `Test-Py` trong chinh tep sidecar)
#    va bi bo qua -> `whisperx-venv` rong toi tan 30/08, va `autosubvideo` chay
#    nhanh du phong `faster-whisper`, MAT can chinh theo tu. No co ghi nhan
#    (`alignment_status: fallback_unaligned`) nhung khong ai doc nhan do.
#
#    Goi tu `$src` chu khong `$appDir`: `$appDir` chi co noi dung moi sau
#    robocopy, ma robocopy thi sau Stop-Service.
# Khi may DA co LTT_WHISPERX_PYTHON thi bo qua duoc: chi autosubvideo giam
# chuc nang. Khi CHUA co (cai moi) thi van phai dung, neu khong auto-sub hong
# am tham.
$whisperPy = $null
try {
    $whisperOut = @(& (Join-Path $src 'deploy\windows\install-whisperx-sidecar.ps1') `
        -Root $Root -ReleaseDir $src -PythonExe 'python')
    $whisperPy = $whisperOut[-1]
} catch {
    Note "WhisperX sidecar loi: $($_.Exception.Message)"
}
if (-not $whisperPy) {
    $envProbe = Join-Path $secrets 'app.env'
    $hasWhisper = (Test-Path $envProbe) -and
        ((Get-Content $envProbe -Raw) -match '(?m)^LTT_WHISPERX_PYTHON=')
    if (-not $hasWhisper) { throw 'Khong cai duoc WhisperX sidecar va app.env chua co LTT_WHISPERX_PYTHON' }
    Note 'BO QUA WhisperX sidecar - app.env da co LTT_WHISPERX_PYTHON cu.'
    Note 'autosubvideo co the giam chuc nang. Chay lai sidecar rieng khi ranh.'
} else {
    Ok 'WhisperX CUDA sidecar da san sang'
}

Head 'Venv giong noi (LTT VOICE) - CAI TRUOC KHI DUNG DICH VU'
# !! VI SAO KHOI NAY O DAY - TRUOC CA `Head 'Copy ma nguon'`.
#
#    Ngay 2026-08-30 no nam o duoi, SAU `Stop-Service`. Mot lan tai ve ~6 GB
#    (torch cu128) do dai bang dung mot khoang production sap. Tien trinh nang
#    quyen chet trong luc tai => production nam 19 phut, `EXITCODE` rong.
#
#    Chu thich o `Head 'Copy ma nguon'` da canh bao san dieu nay: tac gia loai
#    700 MB node_modules chi de RUT NGAN cua so do, va ghi rang mot lan treo
#    robocopy da lam production ngung 20 phut ngay 2026-08-05. Toi tha 6 GB vao
#    dung cua so ay.
#
#    Chay tu `$src` chu khong `$appDir`: `$appDir` chi co noi dung moi SAU
#    robocopy, ma robocopy thi sau Stop-Service. Ban cai trong cay nguon giong
#    het, va no cai mot venv NGOAI `app\` nen khong quan trong ban nao goi.
#
# !! BAI HOC, va no rong hon LTT VOICE: **khong dat mot viec DAI va CO THE HONG
#    vao giua cua so ngung dich vu.** Cai venv khong can dich vu nao dung ca; no
#    o duoi chi vi no "thuoc ve" app do trong dau nguoi viet. Su gan gui ve mat
#    khai niem khong phai ly do de xep thu tu thi hanh.
#
#    Cai o day thi cung mot lan tai ve 6 GB do KHONG lam ai mat mot giay dich vu,
#    va neu no hong thi buoc dang ky dich vu ben duoi tu bo qua (`$voicePy` rong).
#
# LTT VOICE chay VieNeu-TTS v3 Turbo tren GPU may nay (Q117/Q118). Khac ba dich vu
# kia, no chay tu MOT VENV CACH LY: vieneu ghim transformers==4.57.6 va
# torch==2.8.0+cu128; cai de len venv nen tang se ha cap torch Blackwell va lam
# hong moi app GPU khac. Cung ly do da sinh ra whisperx-venv.
#
# LTT_VOICE_VENV_ROOT: venv nay ~8 GB. Bo trong thi dung $Root.
$VoiceServiceName = 'LTTStudioVoice'
$voiceVenvRoot = $env:LTT_VOICE_VENV_ROOT
if (-not $voiceVenvRoot) { $voiceVenvRoot = $Root }
$voicePy = ''
try {
    $out = @(& (Join-Path $src 'deploy\windows\install-vieneu-sidecar.ps1') `
             -Root $Root -ReleaseDir $src -VenvRoot $voiceVenvRoot -PythonExe 'python')
    $voicePy = ($out | Where-Object { $_ -like '*python.exe' } | Select-Object -Last 1)
} catch {
    # Khong chan ca ban cai vi mot app: nen tang van chay duoc khong co giong noi,
    # va the app se tu hien "can thiet lap". Nhung PHAI in ro, khong nuot.
    Write-Host "  [BO QUA] Khong cai duoc vieneu-venv: $($_.Exception.Message)" -ForegroundColor Yellow
}

Head 'Copy ma nguon'
# Dung dich vu truoc khi dong vao app\. Khi chay LAI tren may dang phuc vu that,
# python.exe cua service khoa file trong app\ -> Move-Item/robocopy that bai
# (loi "being used by another process"). Script se cai lai + khoi dong o cuoi.
# !! MOI dich vu co AppDirectory = app\ deu PHAI co trong danh sach nay.
#
#    `Move-Item` khong xoay duoc mot thu muc dang bi mot tien trinh mo. Bo sot
#    MOT dich vu la du: no giu app\, Move-Item nem IOException, va script chet
#    NGAY SAU khi da dung ba dich vu kia -> trang cong khai tra 502 cho toi khi
#    co nguoi bat lai bang tay.
#
#    Da xay ra that 31/08/2026: `LTTStudioVoice` duoc them (Q117) nhung khong
#    duoc them vao day. Deploy chay toi 09:36:46 roi dung; production 502 khoang
#    ba phut. Trieu chung nhin nhu mot loi quyen han, khong nhu mot dich vu bi
#    bo sot.
#
#    Nen danh sach o day duoc DAN XUAT tu chinh cac bien ten dich vu, va
#    `tests/test_45_deploy_scripts.py` chot rang moi dich vu duoc nssm dang ky
#    trong tep nay deu co mat. Them dich vu moi ma quen -> gate do, khong phai
#    production do.
$DichVuGiuAppDir = @($WorkerServiceName, $ServiceName, 'LTTStudioCodex',
                     $VoiceServiceName)
foreach ($svc in $DichVuGiuAppDir) {
    Stop-Service $svc -Force -ErrorAction SilentlyContinue
}
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
# (ADR-009) de cap nhat code khong dong vao du lieu. Them ca thu muc chi
# phuc vu phat trien: production khong chay Node/Vite/Playwright/pytest, va
# node_modules + .playwright-cli + tmp la ~700 MB rac keo dai cua so downtime.
# /R:2 /W:2 la BAT BUOC. Mac dinh robocopy la /R:1000000 /W:30 - mot file bi
# khoa hay ACL hong se treo VO HAN, trong khi dich vu DA bi dung o tren. Loi
# do da that su lam production ngung 20 phut ngay 2026-08-05.
$rc = robocopy $src $appDir /E /NFL /NDL /NJH /NJS /NP /R:2 /W:2 `
      /XD data secrets logs .venv venv __pycache__ .pytest_cache .git dist build temp_videos `
         node_modules .playwright-cli .playwright-mcp .claude test-results tmp `
      /XF *.pyc *.log
if ($LASTEXITCODE -ge 8) { throw "robocopy loi (ma $LASTEXITCODE)" }
$global:LASTEXITCODE = 0
$n = (Get-ChildItem $appDir -Recurse -File).Count
Ok "Da copy $n file vao $appDir"

# Canvas is prebuilt in the release with pinned Node 22.12.0. Production does
# not run Node/Vite and must never depend on a development server.
$canvasManifest = Join-Path $appDir 'server\static\agent-canvas\.vite\manifest.json'
$canvasMeta = Join-Path $appDir 'server\static\agent-canvas\build-meta.json'
if (-not (Test-Path $canvasManifest) -or -not (Test-Path $canvasMeta)) {
    throw 'Release thieu Agent Canvas production bundle'
}
Ok 'Agent Canvas production bundle da co (khong can Node tren server)'
$autosubManifest = Join-Path $appDir 'server\static\autosub-studio\.vite\manifest.json'
$autosubMeta = Join-Path $appDir 'server\static\autosub-studio\build-meta.json'
if (-not (Test-Path $autosubManifest) -or -not (Test-Path $autosubMeta)) {
    throw 'Release thieu Auto Sub Studio production bundle'
}
Ok 'Auto Sub Studio production bundle da co (khong can Node tren server)'

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
Invoke-Ngoai { & $venvPy -m pip install --upgrade pip --quiet }
if ($LASTEXITCODE -ne 0) { throw "Loi khi chay: & $venvPy -m pip install --upgrade pip --quiet" }
Invoke-Ngoai { & $venvPy -m pip install -r (Join-Path $appDir 'requirements.txt') --quiet }
if ($LASTEXITCODE -ne 0) { throw "Loi khi chay: & $venvPy -m pip install -r (Join-Path $appDir 'requirements" }
Invoke-Ngoai { & $venvPy -m pip install -r (Join-Path $appDir 'requirements-server.txt') --quiet }
if ($LASTEXITCODE -ne 0) { throw "Loi khi chay: & $venvPy -m pip install -r (Join-Path $appDir 'requirements" }
Ok 'Da cai thu vien'

# TAO CLIP NGAN (engine cutclipshort) can torch GPU. KHONG de trong requirements vi
# pip keo ban CPU tu PyPI; card Blackwell (RTX 50xx) BAT BUOC torch cu128. Chi cai khi
# torch chua co / chua thay CUDA (tranh tai lai ~2.5GB moi lan deploy).
Invoke-Ngoai { & $venvPy -c "import importlib.util,sys; sys.exit(0) if importlib.util.find_spec('torch') else sys.exit(1)" 2>$null | Out-Null; $hasTorch = ($LASTEXITCODE -eq 0) }
$cudaOk = $false
if ($hasTorch) { & $venvPy -c "import torch,sys; sys.exit(0) if torch.cuda.is_available() else sys.exit(1)" 2>$null; $cudaOk = ($LASTEXITCODE -eq 0) }
if ($cudaOk) {
    Ok 'torch CUDA da san sang - GIU NGUYEN'
} else {
    Note 'Cai torch cu128 (Blackwell) - lan dau ~2.5GB, cho chut'
    Invoke-Ngoai { & $venvPy -m pip install "torch>=2.7" "torchaudio>=2.7" "torchvision>=0.22" --index-url https://download.pytorch.org/whl/cu128 --quiet }
    Invoke-Ngoai { & $venvPy -c "import torch,sys; sys.exit(0) if torch.cuda.is_available() else sys.exit(1)" 2>$null }
    if ($LASTEXITCODE -eq 0) { Ok 'Da cai torch cu128 (CUDA OK)' }
    else { Note 'CANH BAO: torch chua thay CUDA - Tao Clip ngan se chay CPU rat cham (kiem tra driver NVIDIA / dung card Blackwell can cu128)' }
}

Head 'Cau hinh van hanh'
# BUOC TAO data\config.json DA BO 2026-08-25 (Q108).
#
# Tep do la cau hinh cua app socialbot (Meta App ID, Sheet ID, ten cot, chong
# spam) va app do da bi go han. Nen tang KHONG doc tep cau hinh nao luc khoi
# dong nua: ho so moi truong suy ra tu LTT_ENV, moi thu con lai nam trong
# secrets\app.env.
#
# Tep cu con nam lai trong data\ tren may da cai thi khong sao - khong tien
# trinh nao mo no. Xoa la viec cua chu san pham, khong phai cua bo cai.
Ok 'Khong con buoc cau hinh - nen tang doc bien moi truong, khong doc tep'

Head 'Siet quyen thu muc bi mat'
# !!!! DONG NAY TRUOC 2026-08-27 KHONG LAM DUOC DIEU NO IN RA.
#
#   icacls $secrets /inheritance:r /grant:r "SYSTEM:..." "Administrators:..."
#
# `/inheritance:r` bo cac ACE THUA KE. `/grant:r` thay quyen cua nhung chu the
# DUOC LIET KE. Khong cai nao dung toi mot ACE TUONG MINH cua chu the khac -
# no song sot nguyen ven, va bo cai van in 'Ok'.
#
# Do duoc 27/08 tren may dang chay: secrets\ co ACE tuong minh cho tai khoan
# nguoi dung, tuc app.env - noi giu khoa phien, khoa ma hoa token, hash mat khau
# admin, token Proxmox, khoa Vultr - nam duoi mot ACL yeu hon cau ta vua in ra.
#
# Cach dung: LIET KE roi XOA tung chu the ngoai danh sach, roi KIEM LAI. Mot
# buoc bao mat khong tu kiem la mot buoc se noi doi vao dung ngay no that bai.
$chuThePhep = @('SYSTEM', 'Administrators', 'TrustedInstaller')
icacls $secrets /inheritance:r | Out-Null
foreach ($ace in @((Get-Acl $secrets).Access)) {
    $day = $ace.IdentityReference.Value
    if ($chuThePhep -notcontains ($day -split '\\')[-1]) {
        icacls $secrets /remove:g "$day" | Out-Null
    }
}
icacls $secrets /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" | Out-Null
Get-ChildItem $secrets -File | ForEach-Object { icacls $_.FullName /reset | Out-Null }
$conThua = @((Get-Acl $secrets).Access |
    ForEach-Object { ($_.IdentityReference.Value -split '\\')[-1] } |
    Where-Object { $chuThePhep -notcontains $_ } | Select-Object -Unique)
if ($conThua.Count -gt 0) {
    throw "Khong siet duoc secrets\ - van con chu the: $($conThua -join ', ')"
}
Ok 'Chi SYSTEM va Administrators doc duoc secrets\ (da kiem lai)'

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

# Bao dam co token cho SIDECAR Codex (CHAT AI STUDIO). Idempotent: chi them neu thieu.
# Token bao ve dich vu loopback LTTStudioCodex (chi web/worker cung may goi duoc).
$envTxt = Get-Content $envFile -Raw
if ($envTxt -notmatch 'LTT_CODEX_SIDECAR_TOKEN=') {
    $codexTok = & $venvPy -c "import secrets;print(secrets.token_urlsafe(32))"
    $add = "LTT_CODEX_SIDECAR_TOKEN=$codexTok`r`nLTT_CODEX_SIDECAR_PORT=8110`r`nCODEX_SERVER_HOME=$dataDir\codex-home"
    [IO.File]::AppendAllText($envFile, "`r`n" + $add + "`r`n", (New-Object Text.UTF8Encoding($false)))
    Ok 'Da them LTT_CODEX_SIDECAR_TOKEN + port + CODEX_SERVER_HOME vao app.env'
} else {
    Ok 'LTT_CODEX_SIDECAR_TOKEN da co - GIU NGUYEN'
}

$envTxt = Get-Content $envFile -Raw
if ($envTxt -notmatch '(?m)^LTT_WHISPERX_PYTHON=') {
    [IO.File]::AppendAllText($envFile, "`r`nLTT_WHISPERX_PYTHON=$whisperPy`r`n", (New-Object Text.UTF8Encoding($false)))
    Ok 'Da them LTT_WHISPERX_PYTHON vao app.env'
} else {
    Ok 'LTT_WHISPERX_PYTHON da co - GIU NGUYEN'
}
$envTxt = [IO.File]::ReadAllText($envFile)
if ($envTxt -notmatch '(?m)^LTT_HF_TOKEN=') {
    [IO.File]::AppendAllText($envFile, "`r`nLTT_HF_TOKEN=`r`n", (New-Object Text.UTF8Encoding($false)))
    Ok 'Da them placeholder LTT_HF_TOKEN (Pyannote chi bat khi operator dien token)'
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
    Invoke-Ngoai { & $venvPy -m alembic upgrade head }
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

Head 'Dich vu Sidecar Codex (CHAT AI STUDIO)'
# SIDECAR giu Codex app-server song (stateful) tach khoi web/worker. Chi nghe loopback,
# bao ve bang LTT_CODEX_SIDECAR_TOKEN. Chi CHAT + anh (sandbox read-only).
$CodexServiceName = 'LTTStudioCodex'
$existingC = Get-Service $CodexServiceName -ErrorAction SilentlyContinue
if ($existingC) {
    if ($existingC.Status -eq 'Running') { Stop-Service $CodexServiceName -Force; Start-Sleep -Seconds 2 }
    Ok "Dich vu $CodexServiceName da co - cap nhat cau hinh"
} else {
    & $nssmExe install $CodexServiceName $venvPy 'codex_sidecar_main.py' | Out-Null
    Ok "Da tao dich vu $CodexServiceName"
}
& $nssmExe set $CodexServiceName AppDirectory   $appDir | Out-Null
& $nssmExe set $CodexServiceName AppStdout      (Join-Path $logs 'codex-out.log') | Out-Null
& $nssmExe set $CodexServiceName AppStderr      (Join-Path $logs 'codex-err.log') | Out-Null
& $nssmExe set $CodexServiceName AppRotateFiles 1 | Out-Null
& $nssmExe set $CodexServiceName AppRotateOnline 1 | Out-Null
& $nssmExe set $CodexServiceName AppRotateBytes 10485760 | Out-Null
& $nssmExe set $CodexServiceName Start          SERVICE_AUTO_START | Out-Null
& $nssmExe set $CodexServiceName AppExit Default Restart | Out-Null
& $nssmExe set $CodexServiceName AppRestartDelay 10000 | Out-Null
& $nssmExe set $CodexServiceName AppEnvironmentExtra ($envPairs -join "`r`n") | Out-Null
Ok 'Da nap bi mat vao moi truong sidecar codex'

Head 'Dich vu Giong noi (LTT VOICE)'
# Phan CAI DAT da chay o tren, TRUOC khi dung dich vu nao. Khoi nay chi con viec
# dang ky dich vu -- vai giay.
if ($voicePy -and (Test-Path $voicePy)) {
    $hfCache = Join-Path $voiceVenvRoot 'hf-cache'
    $envTxt2 = Get-Content $envFile -Raw -ErrorAction SilentlyContinue
    if ($envTxt2 -notmatch 'LTT_VOICE_SIDECAR_TOKEN=') {
        $voiceTok = & $venvPy -c "import secrets;print(secrets.token_urlsafe(32))"
        $add2 = "LTT_VOICE_SIDECAR_TOKEN=$voiceTok`r`nLTT_VOICE_SIDECAR_PORT=8120`r`nLTT_VIENEU_PYTHON=$voicePy`r`nHF_HOME=$hfCache"
        [IO.File]::AppendAllText($envFile, "`r`n$add2`r`n", (New-Object Text.UTF8Encoding($false)))
        Ok 'Da them LTT_VOICE_SIDECAR_TOKEN + port + HF_HOME vao app.env'
    } else {
        Ok 'LTT_VOICE_SIDECAR_TOKEN da co - GIU NGUYEN'
    }
    # Doc lai app.env de dich vu giong nhan duoc cac bien vua them.
    $envPairs2 = @()
    foreach ($line in (Get-Content $envFile -ErrorAction SilentlyContinue)) {
        $l = $line.Trim()
        if ($l -and -not $l.StartsWith('#') -and $l.Contains('=')) { $envPairs2 += $l }
    }

    $existingV = Get-Service $VoiceServiceName -ErrorAction SilentlyContinue
    if ($existingV) {
        if ($existingV.Status -eq 'Running') { Stop-Service $VoiceServiceName -Force; Start-Sleep -Seconds 2 }
        Ok "Dich vu $VoiceServiceName da co - cap nhat cau hinh"
    } else {
        & $nssmExe install $VoiceServiceName $voicePy 'voice_sidecar_main.py' | Out-Null
        Ok "Da tao dich vu $VoiceServiceName"
    }
    & $nssmExe set $VoiceServiceName Application    $voicePy | Out-Null
    & $nssmExe set $VoiceServiceName AppDirectory   $appDir | Out-Null
    & $nssmExe set $VoiceServiceName AppStdout      (Join-Path $logs 'voice-out.log') | Out-Null
    & $nssmExe set $VoiceServiceName AppStderr      (Join-Path $logs 'voice-err.log') | Out-Null
    & $nssmExe set $VoiceServiceName AppRotateFiles 1 | Out-Null
    & $nssmExe set $VoiceServiceName AppRotateOnline 1 | Out-Null
    & $nssmExe set $VoiceServiceName AppRotateBytes 10485760 | Out-Null
    & $nssmExe set $VoiceServiceName Start          SERVICE_AUTO_START | Out-Null
    & $nssmExe set $VoiceServiceName AppExit Default Restart | Out-Null
    & $nssmExe set $VoiceServiceName AppRestartDelay 10000 | Out-Null
    & $nssmExe set $VoiceServiceName AppEnvironmentExtra ($envPairs2 -join "`r`n") | Out-Null
    Ok 'Da nap bi mat vao moi truong dich vu giong noi'
} else {
    Write-Host '  [BO QUA] Chua cai duoc dich vu giong noi - app LTT VOICE se hien "can thiet lap".' -ForegroundColor Yellow
}

Head 'Khoi dong'
Start-Service $ServiceName
Start-Service $CodexServiceName -ErrorAction SilentlyContinue

# Sau cung: nap ~320 MB trong so len GPU, mat khoang 20 giay moi san sang.

Start-Service $VoiceServiceName -ErrorAction SilentlyContinue

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
else { Note 'Chua ready - thuong do CSDL chua noi duoc. Xem logs\service-err.log' }

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
Write-Host "  2. Chay: .\setup\3-cloudflare.ps1   (can ban dang nhap Cloudflare)"
Write-Host "  3. Chay: .\setup\4-nghiem-thu.ps1"
Write-Host ""
Write-Host "QUAN TRONG: sao luu $secrets\app.env ra cho an toan." -ForegroundColor Yellow
Write-Host "Mat LTT_TOKEN_ENCRYPTION_KEY la mat toan bo token Facebook/TikTok da luu." -ForegroundColor Yellow
