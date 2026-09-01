<#
.SYNOPSIS
    Chay MOT viec da khai bao san, voi moi truong production da nap. CHI DOC.

.DESCRIPTION
    `secrets\app.env` bi khoa ACL (chi SYSTEM + Administrators), va ACL do LA
    DUNG - dung noi long no. Tep nay la CAY CAU HEP: doc app.env, dat vao MOI
    TRUONG CUA RIENG TIEN TRINH NAY, chay dung MOT viec trong danh sach trang,
    roi thoat.

    !! VI SAO KHONG PHAI MOT HAM "CHAY LENH BAT KY VOI ENV PRODUCTION".
       Mot cong cu nhu vay bang voi viec cap quyen doc secrets cho moi thu -
       chi khac la no di qua mot lop giay. Danh sach trang o duoi la thu lam
       cho quyen nay HEP HON quyen doc tep, chu khong rong hon.

    !! NO KHONG IN GIA TRI NAO. Khong echo env, khong dump, khong ghi log
       chua bi mat. Neu ban can doc mot gia tri that thi do la viec cua chu
       may, khong phai cua script nay.

.PARAMETER Viec
    Ten viec trong danh sach trang:

      test-daluong   pytest tests/test_214_multi_process_runtime.py
                     (bat bien da tien trinh - bang chung DUY NHAT cho viec
                     webhook khong gui trung va credit khop khi nhieu worker
                     chay cung luc)
      cong-daluong   tools/check_multiproc.py  (buoc cua `gate.py`)
      soi-su-co      tools/soi_su_co.py        (doc so request + hoi may B)
      kiem-llm       tools/kiem_ltt_llm.py     (kiem toan tuyen A -> B)

      tao-tk-canary  tools/tai_khoan_thu.py    (tai khoan .local + nap credit)
      khoa-canary    tools/khoa_thu_api.py     (phat khoa /api/v1 cho tk do)
      canary-api     tools/api_prod_canary.py  (goi that qua Cloudflare)

    !! `khoa-canary` IN RA MOT KHOA SONG. Ket qua duoc ghi vao `tmp/` (da
       gitignore) nhung van la mot chung danh tren dia - dung chep no di dau.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\chay_voi_env.ps1 -Viec test-daluong

.NOTES
    Can Administrator (de doc app.env dang bi khoa ACL).
    Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('test-daluong', 'cong-daluong', 'soi-su-co', 'kiem-llm',
                 'tao-tk-canary', 'khoa-canary', 'canary-api', 'soi-canary')]
    [string]$Viec,

    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = ''
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'

# !! DO DUNG THU CAN DO, VA DO NO TRUOC MOI THU KHAC.
#
#    "Co phai admin khong" chi la NGUOI DAI DIEN cho cau hoi that, va no sai
#    duoc theo ca hai chieu: mot token UAC da loc van thuoc nhom Administrators
#    nhung khong doc duoc, con mot tai khoan dich vu doc duoc ma khong phai
#    admin. Cau hoi that la "toi co doc duoc tep nay khong".
#
#    Va phai do TRUOC `Test-Path`: voi `ErrorActionPreference = 'Stop'`,
#    `Test-Path` tren mot tep bi ACL tu NEM va nuot mat thong diep ro rang.
try {
    $null = Get-Content $envFile -TotalCount 1 -ErrorAction Stop
} catch {
    throw @"
Khong doc duoc $envFile

ACL cua tep do (chi SYSTEM + Administrators) LA DUNG -- dung noi long no.
Mo PowerShell bang 'Run as administrator' roi chay lai lenh nay.
"@
}

# Danh sach trang. Them mot dong o day la mot quyet dinh co y thuc, va no hien
# ra trong diff cho nguoi review thay - khac han voi mot cong cu chay-gi-cung-duoc.
# !! DUNG PYTHON HE THONG, KHONG PHAI VENV PRODUCTION.
#
#    `C:\LTTPlatform\venv` la venv VAN HANH: no chi co thu vien de CHAY dich vu,
#    khong co `pytest`. Goi no cho mot buoc test se ra
#    "No module named pytest" - mot loi trong het nhu moi truong hong, trong khi
#    that ra la chon nham trinh thong dich. Da dinh mot lan ngay 31/08.
#
#    Bon viec trong danh sach trang deu la CONG CU KIEM, khong phai ma dich vu,
#    nen chung thuoc ve python he thong.
# !! VA DUNG DUA VAO PATH. Tep nay chay duoc bang LocalSystem (qua Nexus), va
#    LocalSystem co profile RIENG - `python` cua nguoi dung nam trong
#    `C:\Users\<ai do>\AppData\Local\...` va khong he co tren PATH cua no.
#    Trieu chung: "Khong tim thay python tren PATH" tren mot may ro rang co
#    python. Nen do PATH truoc, roi do cac cho cai dat that.
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    $ungVien = @()
    foreach ($hs in (Get-ChildItem 'C:\Users' -Directory -ErrorAction SilentlyContinue)) {
        $ungVien += Join-Path $hs.FullName 'AppData\Local\Programs\Python\Python313\python.exe'
    }
    $ungVien += 'C:\Program Files\Python313\python.exe'
    $py = $ungVien | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $py) { throw "Khong tim thay python (da do PATH va cac cho cai dat thong thuong)." }

# !! MOI VIEC LA MOT DANH SACH DOI SO CO DINH. Do la tinh chat quan trong nhat
#    cua bang nay: khong co cho nao nhan doi so tu ben goi, nen khong co cho de
#    tiem. Neu mot ngay nao do can tham so, dung them mot `-Tham` chung -- them
#    MOT DONG MOI voi doi so co dinh, va de nguoi review thay no trong diff.
#
#    Email thu la mot HANG SO o day, khong phai tham so, vi dung ly do do. Duoi
#    `.local` la chot cua `khoa_thu_api.py`: mot khoa API tieu TIEN THAT cua chu
#    so huu, nen no khong bao gio duoc phat cho tai khoan khach.
$EMAIL_CANARY = 'canary.api@lttstudios.local'

$viecCuThe = @{
    'test-daluong' = @($py, '-m', 'pytest', 'tests/test_214_multi_process_runtime.py', '-q')
    'cong-daluong' = @($py, 'tools/check_multiproc.py')
    'soi-su-co'    = @($py, 'tools/soi_su_co.py')
    'kiem-llm'     = @($py, 'tools/kiem_ltt_llm.py')
    # Ba viec duoi cho nghiem thu E15-E17: tai khoan thu -> khoa thu -> canary.
    # Chung DUNG TIEN THAT cua tai khoan `.local` do -- co y, vi mot canary khong
    # di qua duong tinh tien la mot canary khong kiem duoc duong tinh tien.
    'tao-tk-canary' = @($py, 'tools/tai_khoan_thu.py', '--email', $EMAIL_CANARY,
                        '--ten', 'Canary API', '--nap', '2000')
    'khoa-canary'   = @($py, 'tools/khoa_thu_api.py', '--email', $EMAIL_CANARY,
                        '--ten', 'canary-e15')
    'canary-api'    = @($py, 'tools/api_prod_canary.py')
    # Soi so request cua CHINH tai khoan canary. Cung cong cu, khac mot
    # doi so co dinh -- dung khuon ma chu thich o tren mo ta.
    'soi-canary'    = @($py, 'tools/soi_su_co.py', '--email', $EMAIL_CANARY,
                        '--gio', '2', '--khong-goi-thu')
}
$argv = $viecCuThe[$Viec]
if (-not $argv) { throw "Viec khong co trong danh sach trang: $Viec" }

# utf-8-sig o phia doc: quy tac 1 cam GHI BOM, doc thi phai chiu duoc.
$so = 0
foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    $ten = $d.Substring(0, $i).Trim()
    $gt  = $d.Substring($i + 1)
    if ($ten) {
        # KHONG in gia tri nao: tep nay giu khoa ma hoa token va mat khau CSDL.
        Set-Item -Path "Env:$ten" -Value $gt
        $so++
    }
}
Write-Host "  [OK] Nap $so bien tu app.env vao tien trinh nay (khong in gia tri)" -ForegroundColor Green
Write-Host "  [->] Chay: $Viec" -ForegroundColor Cyan

$raThuMuc = Join-Path $Repo 'tmp'
if (-not (Test-Path $raThuMuc)) { New-Item -ItemType Directory -Path $raThuMuc | Out-Null }
$raTep = Join-Path $raThuMuc "chay_voi_env_$Viec.txt"

# !! BAY DA DINH BON LAN TRONG HAI NGAY. Voi `ErrorActionPreference = 'Stop'`,
#    mot exe NGOAI ghi ra stderr thanh NativeCommandError va KET THUC script -
#    dong doc `$LASTEXITCODE` KHONG BAO GIO CHAY, va mot loi vo hai doc len
#    giong het mot lan treo.
#
# !! KHONG dung `Tee-Object -Encoding`: tham so do chi co tu PowerShell 6, va
#    tren 5.1 no vo LUC RANG BUOC PIPELINE nen lenh khong bao gio chay - trong
#    khi man hinh van in "da luu ket qua". Ghi bang .NET, khong BOM.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
Push-Location $Repo
$ket = (& $argv[0] $argv[1..($argv.Length - 1)] 2>&1 | Out-String)
$ma = $LASTEXITCODE
Pop-Location
$ErrorActionPreference = $truoc

Write-Host $ket
[IO.File]::WriteAllText($raTep, $ket, (New-Object Text.UTF8Encoding($false)))
Write-Host ""
Write-Host "  [OK] Ket qua luu tai: $raTep" -ForegroundColor Green
exit $ma
