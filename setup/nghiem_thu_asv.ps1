<#
.SYNOPSIS
    Chay bo nghiem thu dau-cuoi cua Auto Scan Video V4 voi moi truong production.

.DESCRIPTION
    Khuon lay tu `setup\tai_khoan_thu.ps1`: doc `secrets\app.env`, dat vao
    TIEN TRINH NAY thoi, chay dung MOT lenh, roi thoat. Khong ghi app.env,
    khong dung dich vu nao, khong in mot gia tri nao ra man hinh.

    VI SAO CAN. `apps/ltt_voice/sidecar_client.py` va `voice_sidecar/server.py`
    doc CUNG mot bien `LTT_VOICE_SIDECAR_TOKEN`, va bien do nam trong app.env
    dang bi ACL chan. Nen mot tien trinh test chay bang tay khong the goi
    LTTStudioVoice that, va bo nghiem thu phai thay bang SAPI - mot giong
    en-US, khong noi duoc gi ve chat luong long tieng tieng Viet.

    VI SAO HEP. Mot script "chay lenh bat ky voi moi truong production" huu
    dung hon nhieu, va do chinh la ly do no khong nen ton tai: no bien moi
    shell ve sau thanh mot shell doc duoc khoa ma hoa token. Script nay goi
    ten bo test cua no trong ma.

    KHONG TAO KHOA NAO. Token giong noi da ton tai tu luc cai
    (`setup\2-cai-dat.ps1` sinh no bang `secrets.token_urlsafe(32)` va giu
    nguyen neu da co). Sinh mot token moi o day khong phai "tao cai dang
    thieu" - no la XOAY mot chung danh dang song, va vi hai dau doc chung mot
    bien, xoay ma khong khoi dong lai ca hai se lam hong tinh nang giong noi
    cua khach that.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\nghiem_thu_asv.ps1
    powershell -ExecutionPolicy Bypass -File .\setup\nghiem_thu_asv.ps1 -GiongSAPI
    powershell -ExecutionPolicy Bypass -File .\setup\nghiem_thu_asv.ps1 -QcAi

.NOTES
    Can Administrator (de doc app.env dang bi ACL chan).
    Pure ASCII (CLAUDE.md quy tac 2).
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = '',
    # Mac dinh dung LTTStudioVoice THAT. Bat co nay de chay lai duong SAPI.
    [switch]$GiongSAPI,
    # Mac dinh goi model THAT tren may B qua pool. Bat co nay de dung ban gia.
    [switch]$ModelGia,
    # Bat QC bang AI (mac dinh TAT vi no la mot khoan chi moi lan chay).
    #
    # Cong tat that la bien moi truong LTT_ASV_QC_AI o cap NGUOI VAN HANH,
    # khong phai mot truong trong settings cua khach: mot truong settings la
    # thu khach gui len, tuc khach tu bat duoc mot chi phi chua duoc dinh gia.
    #
    # Khong bat co nay thi luot nghiem thu do dung ban SE GIAO: giai doan
    # qc_ai van chay va van thanh cong, chi la no khong goi model.
    [switch]$QcAi,
    # Noi ghi bao cao nghiem thu. Rong = ghi de ban trong kho.
    [string]$BaoCao = ''
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$boTest  = Join-Path $Repo 'tests\test_448_asv_v4_e2e_nghiem_thu.py'

foreach ($p in @($envFile, $boTest)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

# !! KHONG dung venv cua SAN PHAM de chay pytest.
#
#    Do that hom nay: no la Python 3.13.12 voi `torch 2.11.0+cu128` va
#    `cuda True` - tuc dung trinh thong dich san pham can - nhung no
#    **khong co pytest**, va do la co y: venv do cai thu SAN PHAM chay,
#    khong cai bo cong cu kiem thu. `-m pytest` o day se hong ngay dong
#    dau voi 'No module named pytest', SAU khi da nap xong app.env.
#
# => Thu can tu cau nay la **app.env**, khong phai trinh thong dich.
#    Tu tim mot python CO pytest.
function Tim-Python {
    param([string[]]$UngVien)
    # !! DAY LA LAN THU TU CUA CUNG MOT BAY, va no dinh o chinh ham
    #    dung de TRANH mot loi khac. Voi `$ErrorActionPreference='Stop'`,
    #    mot exe NGOAI ghi ra stderr tro thanh NativeCommandError va KET
    #    THUC script - va phep do duoi day CO Y chay mot python thieu
    #    pytest, tuc no CHAC CHAN in mot traceback ra stderr.
    #
    #    `2>$null` khong cuu duoc: no vut bo VAN BAN, con PowerShell van
    #    sinh ban ghi loi truoc do. Phai ha preference quanh chinh lan goi.
    $cuTP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        foreach ($u in $UngVien) {
            if (-not $u) { continue }
            $duong = $null
            $c = Get-Command $u -ErrorAction SilentlyContinue
            if ($c) { $duong = $c.Source } elseif (Test-Path $u) { $duong = $u }
            if (-not $duong) { continue }
            & $duong -c "import pytest" 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) { return $duong }
        }
    } finally {
        $ErrorActionPreference = $cuTP
    }
    return $null
}

$venvPy = Join-Path $Root 'venv\Scripts\python.exe'
$pyChay = Tim-Python @($Python, $venvPy, 'python.exe', 'py.exe')
if (-not $pyChay) {
    throw "Khong tim thay python nao co pytest. Chi dinh bang -Python."
}
Write-Host "  [OK] Chay pytest bang: $pyChay" -ForegroundColor Green
if (-not $BaoCao) {
    $BaoCao = Join-Path $Repo 'docs\auto_scan_video_v4\evidence\nghiem_thu_hien_hanh.json'
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw "Can quyen Administrator de doc $envFile (ACL cua no la dung, dung noi long)."
}

# !! KHONG dat ten bien la `$so`. Xem `setup\nap_credit_tai_khoan_thu.ps1`:
#    PowerShell khong phan biet hoa thuong, nen mot bien noi bo ten `$so` da
#    tung ghi de tham so `-So` va lam sai mot but toan credit, im lang.
$soBien = 0
foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    $ten = $d.Substring(0, $i).Trim()
    $gt  = $d.Substring($i + 1)
    if ($ten) {
        # KHONG in gia tri nao: tep nay giu khoa ma hoa token va mat khau CSDL.
        Set-Item -Path "Env:$ten" -Value $gt
        $soBien++
    }
}
Write-Host "  [OK] Nap $soBien bien tu app.env vao tien trinh nay (khong in gia tri)" -ForegroundColor Green

$coToken = [bool]($env:LTT_VOICE_SIDECAR_TOKEN)
if (-not $coToken) {
    Write-Host "  [!!] app.env KHONG co LTT_VOICE_SIDECAR_TOKEN - se chay bang SAPI" -ForegroundColor Yellow
}

$coCsdl = [bool]($env:LTT_DATABASE_URL)
if (-not $coCsdl) {
    Write-Host "  [!!] app.env KHONG co LTT_DATABASE_URL - se dung ban model gia" -ForegroundColor Yellow
}

$env:LTT_TEST_NANG   = '1'
$env:LTT_ASV_E2E_RA  = $BaoCao

if ($QcAi) {
    $env:LTT_ASV_QC_AI = '1'
    Write-Host "  [OK] QC bang AI: BAT (soat nghia ban dich, co tinh tien)" -ForegroundColor Green
} else {
    Remove-Item Env:LTT_ASV_QC_AI -ErrorAction SilentlyContinue
    Write-Host "  [--] QC bang AI: TAT (mac dinh; dung -QcAi de bat)" -ForegroundColor Yellow
}

Remove-Item Env:LTT_ASV_POOL_URL -ErrorAction SilentlyContinue
if ($ModelGia -or -not $coCsdl) {
    Remove-Item Env:LTT_ASV_MODEL_THAT -ErrorAction SilentlyContinue
    Write-Host "  [--] Model: ban thay the (khong cham may B)" -ForegroundColor Yellow
} else {
    # KHONG go cung dia chi may B vao day. `Ket_noi.md` noi thang: tin cum chu
    # dung tin mot gia tri chep lai. Dia chi that nam o cot `base_url` cua dong
    # khoa trong pool, va `api_pool.chon_key` la thu duy nhat biet chon dong nao.
    #
    # !! `LTT_ASV_POOL_URL` la mot bien RIENG, va no phai the.
    #    Fixture `moi_truong` GHI DE `LTT_DATABASE_URL` bang mot SQLite
    #    dung-mot-lan truoc khi than bai test chay - de tao user/run/credit
    #    ma khong cham CSDL that. Nen bo test khong con duong nao doc lai
    #    URL cua pool tru khi ta giu no o mot cho khac.
    #
    # !! Bien nay chi de DOC mot dong khoa. Khong bo test nao duoc ghi
    #    vao CSDL production qua no.
    $env:LTT_ASV_MODEL_THAT = '1'
    $env:LTT_ASV_POOL_URL   = $env:LTT_DATABASE_URL

    # !! Model THAT doi PostgreSQL, khong chay duoc tren SQLite.
    #    Bo nay mo nhieu phien cung luc theo dung thiet ke (handler,
    #    ctx.progress, ctx.provider_dispatched - bat bien I5). SQLite chi
    #    cho MOT nguoi ghi, va mot loi goi model that giu ket noi vai
    #    giay, nen chung dam nhau: 'database is locked [SQL: UPDATE jobs'.
    #
    # !! Ten CSDL PHAI chua 'test' - `tests/pg_scratch.py` tu choi neu
    #    khong, vi cac bai nay goi `drop_all`.
    Write-Host "  [**] Model: THAT, qua pool khoa -> may B" -ForegroundColor Cyan
}

# CSDL la mot truc RIENG, khong di theo lua chon model.
#
# !! Truoc 06/09 khoi chon PostgreSQL nam TRONG nhanh "model that", nen
#    `-ModelGia` keo theo ca SQLite. Va SQLite khong song noi duong ong nay:
#    `compose` chay ffmpeg vai giay trong khi web va worker cung ghi, nen
#    luot chan doan chet o `compose` voi 'database is locked' - mot loi
#    TRONG GIONG loi san pham nhung thuc ra la cau hinh cua bo chay.
#
# !! Do that 06/09 11:19: ca hai preset deu `compose failed_terminal`, khong
#    preset nao toi duoc `render`. Chu thich cu da du bao dung hien tuong
#    nhung quy cho "loi goi model that giu ket noi vai giay"; lan nay KHONG
#    co loi goi model nao va no van khoa. Tuc thu phai co PostgreSQL la
#    DUONG ONG, khong phai model.
#
# !! Ten CSDL PHAI chua 'test' - `tests/pg_scratch.py` tu choi neu khong,
#    vi cac bai nay goi `drop_all`.
if ($coCsdl) {
    if (-not $env:LTT_TEST_DATABASE_URL) {
        $env:LTT_TEST_DATABASE_URL = ($env:LTT_DATABASE_URL -replace
            '/[^/?]+(\?|$)', '/lttplatform_test$1')
    }
    Write-Host "  [**] CSDL nghiem thu: PostgreSQL nhap (ten chua 'test')" -ForegroundColor Cyan
} else {
    Write-Host "  [!!] CSDL: SQLite - duong ong nay hay dinh 'database is locked' o compose" -ForegroundColor Yellow
}
if ($GiongSAPI -or -not $coToken) {
    Remove-Item Env:LTT_ASV_GIONG_THAT -ErrorAction SilentlyContinue
    Write-Host "  [--] Che do: SAPI (giong en-US thay the)" -ForegroundColor Yellow
} else {
    $env:LTT_ASV_GIONG_THAT = '1'
    Write-Host "  [**] Che do: LTTStudioVoice THAT o :8120" -ForegroundColor Cyan
}

# Kiem cong truoc khi ton demucs + ASR. Mot lan chay hong o buoc long tieng
# xay ra SAU vai phut xu ly nang, va do la vai phut khong can mat.
if ($env:LTT_ASV_GIONG_THAT -eq '1') {
    $cong = 8120
    if ($env:LTT_VOICE_SIDECAR_PORT) { $cong = [int]$env:LTT_VOICE_SIDECAR_PORT }
    $tcp = New-Object Net.Sockets.TcpClient
    try {
        $tcp.Connect('127.0.0.1', $cong)
        Write-Host "  [OK] Sidecar giong noi dang mo o :$cong" -ForegroundColor Green
    } catch {
        throw "Sidecar giong noi khong mo o :$cong. Bat LTTStudioVoice roi chay lai, hoac dung -GiongSAPI."
    } finally {
        $tcp.Dispose()
    }
}

Write-Host ''
Write-Host "  Bao cao se ghi vao: $BaoCao"
Write-Host ''

# !! BAY DA DINH BA LAN - xem `setup\tai_khoan_thu.ps1`.
#    Voi `$ErrorActionPreference = 'Stop'`, mot exe NGOAI ghi ra stderr thanh
#    NativeCommandError va KET THUC script, nen ma thoat khong bao gio duoc
#    doc. Python ghi stderr vi nhieu ly do binh thuong.
$cu = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $pyChay -m pytest -q -p no:randomly $boTest
$maThoat = $LASTEXITCODE
$ErrorActionPreference = $cu

Write-Host ''
if ($maThoat -eq 0) {
    Write-Host "  [OK] Nghiem thu xanh. EXITCODE=$maThoat" -ForegroundColor Green
    Write-Host "  Doc `"giong_that`", `"model_that`" va `"thay_the`" trong bao cao"
    Write-Host "  de biet cua nao da chay THAT. Danh sach `"thay_the`" RONG nghia la"
    Write-Host "  ca hai cua deu that - va hai co kia phai cung noi vay."
} else {
    Write-Host "  [FAIL] Nghiem thu do. EXITCODE=$maThoat" -ForegroundColor Red
}
exit $maThoat
