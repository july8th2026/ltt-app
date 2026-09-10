<#
.SYNOPSIS
    Do ti le hong cua `chuyen_loi_thoai` tren may B, CO DOI CHUNG.

.DESCRIPTION
    Khuon lay tu `setup\nghiem_thu_asv.ps1`: doc `secrets\app.env`, dat vao
    TIEN TRINH NAY thoi, chay dung MOT lenh, roi thoat. Khong ghi app.env,
    khong dung dich vu nao, khong in mot gia tri nao ra man hinh.

    VI SAO CAN. Khoa goi may B khong nam trong mot bien moi truong - no la mot
    DONG POOL trong CSDL, va `api_pool.chon_key` la thu duy nhat biet chon dong
    nao. De doc duoc pool phai co `LTT_DATABASE_URL` va
    `LTT_TOKEN_ENCRYPTION_KEY`, ca hai nam trong app.env dang bi ACL chan.

    VI SAO HEP. Mot script "chay lenh bat ky voi moi truong production" huu
    dung hon nhieu, va do chinh la ly do no khong nen ton tai: no bien moi
    shell ve sau thanh mot shell doc duoc khoa ma hoa token. Script nay goi
    ten cong cu cua no TRONG MA.

    KHONG TAO KHOA NAO, khong ghi vao CSDL nao. Cong cu ben duoi chi GOI model
    va dem ket qua.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\do_on_dinh.ps1
    powershell -ExecutionPolicy Bypass -File .\setup\do_on_dinh.ps1 -Vong 20

.NOTES
    Can Administrator (de doc app.env dang bi ACL chan).
    Pure ASCII (CLAUDE.md quy tac 2).
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = '',
    [int]$Vong = 15,
    [string]$Python = '',
    # Noi ghi ket qua do. Rong = chi in ra man hinh.
    [string]$Ra = '',
    # !! TAP DONG, va no PHAI dong. Docstring cua tep nay ghi ly do: mot script
    #    "chay lenh bat ky voi moi truong production" huu dung hon nhieu, va do
    #    chinh la ly do no khong nen ton tai - no bien moi shell ve sau thanh
    #    mot shell doc duoc khoa ma hoa token.
    #
    #    Nen tham so nay KHONG nhan mot duong dan. No nhan mot TU KHOA, va bang
    #    anh xa tu khoa -> tep nam ngay duoi day, trong ma nguon nay.
    [ValidateSet('on-dinh', 'ngan-sach')]
    [string]$Do = 'on-dinh'
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'

# Anh xa TU KHOA -> tep. Ca hai ten deu go thang o day, khong ghep tu tham so.
$bangCongCu = @{
    'on-dinh'   = 'tools\do_on_dinh_chuyen_loi_thoai.py'
    'ngan-sach' = 'tools\do_ngan_sach_chuyen_loi_thoai.py'
}
$congCu = Join-Path $Repo $bangCongCu[$Do]

# !! KIEM ADMIN TRUOC MOI `Test-Path`, va thu tu nay khong phai tuy y.
#
#    `Test-Path` len mot tep bi ACL chan KHONG tra `$false` - no NEM
#    `UnauthorizedAccessException`, va voi `$ErrorActionPreference='Stop'` thi
#    script chet ngay tai do. Ket qua: chot kiem admin o duoi khong bao gio
#    chay, va nguoi chay nham quyen nhan mot `Access is denied` tho thay vi
#    cau "Can quyen Administrator".
#
#    Do that 09/09: chay khong nang quyen -> chet o dong `Test-Path`, khong mot
#    chu nao noi ra rang thu con thieu la QUYEN.
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw "Can quyen Administrator de doc $envFile (ACL cua no la dung, dung noi long)."
}

foreach ($p in @($envFile, $congCu)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

# !! Cong cu nay KHONG can pytest - no goi thang `apps.auto_scan_video.ai`.
#    Nhung no CAN mot python co `sqlalchemy` va `psycopg`, tuc venv san pham
#    hoac python he thong deu duoc. Thu venv truoc vi no la cai production
#    dung that.
function Tim-Python {
    param([string[]]$UngVien)
    $cuTP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        foreach ($u in $UngVien) {
            if (-not $u) { continue }
            $duong = $null
            $c = Get-Command $u -ErrorAction SilentlyContinue
            if ($c) { $duong = $c.Source } elseif (Test-Path $u) { $duong = $u }
            if (-not $duong) { continue }
            # !! PHAI co ca `pytest`. Cong cu goi `tests.fixtures.asv_e2e`
            #    (de dung lai `nap_khoa_pool` thay vi chep lai), va tep do keo
            #    theo `asv_media` -> `import pytest`.
            #
            #    Do that 09/09: venv san pham co sqlalchemy + psycopg nhung
            #    KHONG co pytest (co y - no cai thu SAN PHAM chay), nen no
            #    duoc chon roi chet o dong import, SAU khi da nap 76 bien.
            & $duong -c "import sqlalchemy, psycopg, pytest" 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) { return $duong }
        }
    } finally {
        $ErrorActionPreference = $cuTP
    }
    return $null
}

$venvPy = Join-Path $Root 'venv\Scripts\python.exe'
$pyChay = Tim-Python @($Python, $venvPy, 'python.exe', 'py.exe')
if (-not $pyChay) { throw "Khong tim thay python nao co sqlalchemy + psycopg + pytest." }
Write-Host "  [OK] Chay bang: $pyChay" -ForegroundColor Green

# !! KHONG dat ten bien la `$so` - xem ghi chu trong `nghiem_thu_asv.ps1`.
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

if (-not $env:LTT_DATABASE_URL) { throw "app.env khong co LTT_DATABASE_URL." }

# !! `LTT_ASV_POOL_URL` la mot bien RIENG va no phai the: khong co fixture nao
#    ghi de o day, nhung cong cu doc CUNG mot bien voi bo test de hai duong
#    khong lech nhau. Xem `tests/fixtures/asv_e2e.py:397`.
$env:LTT_ASV_POOL_URL = $env:LTT_DATABASE_URL

# !! `-u`: KHONG dem stdout. Python dem khi dau ra khong phai TTY, nen mot
#    luot dai se khong in mot byte nao cho toi luc ket thuc - va nhin tu ngoai
#    thi "dang chay" va "treo" trong y het nhau. Do that 09/09.
$dsThamSo = @('-u', $congCu, '--vong', "$Vong")
Write-Host "  [OK] Bat dau do $Vong vong (moi vong goi CA HAI thao tac)" -ForegroundColor Green
Write-Host ""

# !! KHONG dung `Tee-Object` nua. Lop NGOAI (`do_on_dinh_nang_quyen.ps1`)
#    chuyen huong bang `-RedirectStandardOutput`, va do la cho DUY NHAT lam
#    duoc viec ay: `-Verb RunAs` loai tru `-RedirectStandardOutput`.
& $pyChay @dsThamSo
$ma = $LASTEXITCODE
Write-Host ""
Write-Host "  EXITCODE=$ma"
exit $ma
