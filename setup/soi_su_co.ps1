<#
.SYNOPSIS
    Chay tools/soi_su_co.py voi moi truong production da nap. CHI DOC.

.DESCRIPTION
    `secrets\app.env` bi khoa ACL (chi SYSTEM va Administrators doc duoc), va
    ACL do LA DUNG - dung noi long no.

    Script nay la CAY CAU HEP, cung khuon voi `tai_khoan_thu.ps1`: doc app.env,
    dat vao MOI TRUONG CUA RIENG TIEN TRINH NAY, chay dung mot cong cu co ten,
    roi thoat. No khong ghi app.env, khong cham dich vu nao, khong in gia tri
    nao ra man hinh.

    Cong cu duoc goi CHI DOC: no doc cong tac ngat, doc so `public_api_requests`,
    roi hoi may B (GET /health + mot yeu cau thu 8 token). Khong but toan credit
    nao cua khach dinh vao day.

.PARAMETER KhongGoiThu
    Chi doc /health, khong gui yeu cau thu nao.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\soi_su_co.ps1

.NOTES
    Can Administrator (de doc app.env dang bi khoa ACL).
    Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = '',
    [switch]$KhongGoiThu
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\soi_su_co.py'

# !! DO DUNG THU CAN DO, VA DO NO TRUOC MOI THU KHAC.
#
#    Ban dau tep nay hoi `IsInRole(Administrator)` roi moi `Test-Path` ba duong
#    dan. Ca hai deu sai cho:
#
#    1. THU TU. Voi `$ErrorActionPreference = 'Stop'`, `Test-Path` tren mot tep
#       bi ACL tu NEM "Access to the path is denied" -- tuc no chay truoc va
#       nuot mat thong diep ro rang cua phep kiem quyen. Nguoi chay nhan mot
#       loi he thong thay vi mot cau bao ho phai lam gi.
#
#    2. PHEP DO. "Co phai admin khong" chi la NGUOI DAI DIEN cho cau hoi that,
#       va no sai duoc theo ca hai chieu: mot token UAC da loc van thuoc nhom
#       Administrators nhung khong doc duoc, con mot tai khoan dich vu doc duoc
#       ma khong phai admin. Cau hoi that la "toi co doc duoc tep nay khong",
#       va no do truc tiep duoc.
try {
    $null = Get-Content $envFile -TotalCount 1 -ErrorAction Stop
} catch {
    throw @"
Khong doc duoc $envFile

ACL cua tep do (chi SYSTEM + Administrators) LA DUNG -- dung noi long no.
Mo PowerShell bang 'Run as administrator' roi chay lai lenh nay.
"@
}

foreach ($p in @($venvPy, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

# utf-8-sig o phia Python; o day chi can chiu duoc BOM neu ai do soan bang cong
# cu chen BOM. Quy tac 1 cam GHI BOM, doc thi phai chiu duoc.
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

$doiSo = @()
if ($KhongGoiThu) { $doiSo += '--khong-goi-thu' }

# !! BAY DA DINH BON LAN TRONG HAI NGAY. Voi `$ErrorActionPreference = 'Stop'`,
#    mot exe NGOAI ghi ra stderr thanh NativeCommandError va KET THUC script.
#    Python ghi stderr vi nhieu ly do binh thuong (SyntaxWarning, mot dong chan
#    doan), va khi do dong doc `$LASTEXITCODE` KHONG BAO GIO CHAY - mot loi vo
#    hai doc len giong het mot lan treo.
# !! GHI RA TEP, KHONG CHI RA MAN HINH.
#
#    Script nay phai chay CO QUYEN, tuc no chay trong mot cua so khac voi cua so
#    dang lam viec. Ket qua nam tren man hinh do la ket qua khong ai doc lai
#    duoc, va lan chay dau tien (31/08) da mat dung mot vong vi the.
#
#    An toan o day, khac han `tai_khoan_thu.ps1`: cong cu duoc goi KHONG in bi
#    mat nao - chi id khoa rut gon va DO DAI credential. Nen ghi ra tep la ghi
#    mot ban chan doan, khong phai ghi mot bi mat.
#
# !! Va tep dich nam trong `tmp/`, thu muc DA co trong .gitignore. Khong bao gio
#    ghi thu nay vao `logs\` - mot bi mat trong thu muc log la mot bi mat trong
#    moi ban sao luu, va quy tac do dung ca khi lan nay khong co bi mat: cho dat
#    tep quyet dinh ai se doc no ve sau.
$raThuMuc = Join-Path $Repo 'tmp'
if (-not (Test-Path $raThuMuc)) { New-Item -ItemType Directory -Path $raThuMuc | Out-Null }
$raTep = Join-Path $raThuMuc 'soi_su_co.txt'

$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
# !! KHONG DUNG `Tee-Object -Encoding`. Tham so do CHI CO tu PowerShell 6; tren
#    Windows PowerShell 5.1 no la `ParameterBindingException`, va -- day moi la
#    phan dat -- loi ay xay ra luc RANG BUOC PIPELINE, tuc cong cu python KHONG
#    BAO GIO CHAY. Man hinh van in "[OK] Da luu ket qua", nen no doc len giong
#    het mot lan chay thanh cong voi ket qua rong.
#
# !! Va `[Parser]::ParseFile` KHONG bat duoc chuyen nay: no soat CU PHAP, khong
#    soat tham so co ton tai hay khong. Mot script "cu phap OK" van co the vo
#    ngay dong dau tien tren phien ban PowerShell that.
#
# !! Ghi bang .NET, khong BOM -- dung khuon cua quy tac 1 trong CLAUDE.md.
#    `Out-File -Encoding utf8` tren 5.1 chen BOM.
$ket = (& $venvPy $tool @doiSo 2>&1 | Out-String)
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc

Write-Host $ket
[IO.File]::WriteAllText($raTep, $ket, (New-Object Text.UTF8Encoding($false)))

Write-Host ""
Write-Host "  [OK] Da luu ket qua vao: $raTep" -ForegroundColor Green
exit $ma
