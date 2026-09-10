# bat_co_v3_nang_quyen.ps1 - LOP TRONG. Bat (hoac TAT) sau co ChatLTT V3.
#
# KHONG CHAY TAY TEP NAY. No duoc goi boi lop ngoai:
#
#     Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
#       '-File','"D:\LTTSTUDIOSAPP\setup\bat_co_v3_nang_quyen.ps1"' -Verb RunAs
#
# Tat gap (duong lui, KHONG phai viet script moi duoi ap luc):
#
#     ... '-File','"...\bat_co_v3_nang_quyen.ps1"','-Tat' -Verb RunAs
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! VI SAO CAN NANG QUYEN VA VI SAO PHAI HAI LOP
#
#    `C:\LTTPlatform\secrets\` siet ACL ve SYSTEM + Administrators (hang muc
#    W1.5). Va `Start-Process` KHONG cho dung `-Verb RunAs` cung `-Redirect*`:
#    hai tham so loai tru nhau va no hong IM LANG. Nen lop ngoai chi nang
#    quyen, lop nay ghi ket qua ra tep.
#
# !! VI SAO SUA app.env ROI Restart-Service LA KHONG DU
#
#    nssm NUONG bien moi truong vao dang ky dich vu LUC CAI. Restart dich vu
#    chi lam no len lai voi ENV CU - khong loi nao bao, chi la co moi khong co
#    tac dung. Da dinh BA lan trong du an nay. Nen script goi `nap_lai_env.ps1`.
#
# !! GHI KHONG BOM. `Out-File -Encoding utf8` va `Set-Content -Encoding utf8`
#    cua PowerShell 5.1 CHEN BOM, va mot BOM trong app.env da that su lam sap
#    production o du an nay. Dung [IO.File]::WriteAllText voi UTF8Encoding($false).
#
# !! KHONG IN GIA TRI NAO cua app.env ra man hinh hay log. Tep do chua khoa
#    phien, khoa ma hoa token, hash mat khau. Script chi in TEN co va so dong.

[CmdletBinding()]
param(
    [string]$Root   = 'C:\LTTPlatform',
    [string]$Repo   = 'D:\LTTSTUDIOSAPP',
    [string]$LogDir = 'C:\LTTPlatform\logs',
    [switch]$Tat
)

$ErrorActionPreference = 'Stop'

$CoV3 = @(
    'LTT_CHATLTT_V3_TOOLS',
    'LTT_CHATLTT_V3_PAID_TOOLS',
    'LTT_CHATLTT_V3_FILES',
    'LTT_CHATLTT_V3_MEMORY',
    'LTT_CHATLTT_V3_PROJECTS',
    'LTT_CHATLTT_V3_RESEARCH'
)
$GiaTri = if ($Tat) { '0' } else { '1' }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$sum = Join-Path $LogDir "co-v3-$stamp.ket.txt"

"BAT DAU=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content $sum -Encoding utf8
"ADMIN=$isAdmin"      | Add-Content $sum -Encoding utf8
"HANH DONG=$(if ($Tat) { 'TAT' } else { 'BAT' })" | Add-Content $sum -Encoding utf8

if (-not $isAdmin) {
    # Ghi ra roi thoat, KHONG throw: throw chi lam cua so bien mat.
    "EXITCODE=-1" | Add-Content $sum -Encoding utf8
    "LY_DO=khong co quyen Administrator - lop ngoai phai dung -Verb RunAs" |
        Add-Content $sum -Encoding utf8
    exit 1
}

$envFile = Join-Path $Root 'secrets\app.env'
if (-not (Test-Path $envFile)) {
    "EXITCODE=-2" | Add-Content $sum -Encoding utf8
    "LY_DO=khong thay $envFile" | Add-Content $sum -Encoding utf8
    exit 1
}

# ---- Sao luu TRUOC khi cham vao ------------------------------------------
# Mot ban sao canh tep goc la duong lui re nhat; khong co no thi mot loi go
# sai bien thanh mot buoi khoi phuc.
$backup = "$envFile.truoc-co-v3-$stamp"
Copy-Item $envFile $backup -Force
"SAO LUU=$backup" | Add-Content $sum -Encoding utf8

# ---- Doc, sua, ghi lai KHONG BOM -----------------------------------------
$dong = [IO.File]::ReadAllLines($envFile)
$moi = New-Object System.Collections.Generic.List[string]
$daDat = @{}

foreach ($d in $dong) {
    $ten = ''
    if ($d -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') { $ten = $Matches[1] }
    if ($ten -and ($CoV3 -contains $ten)) {
        # Thay dong cu chu KHONG them dong moi: hai dong cung ten thi dong sau
        # thang, va mot tep co hai dong cung ten la mot tep noi doi.
        $moi.Add("$ten=$GiaTri")
        $daDat[$ten] = $true
    } else {
        $moi.Add($d)
    }
}
foreach ($c in $CoV3) {
    if (-not $daDat.ContainsKey($c)) { $moi.Add("$c=$GiaTri") }
}

# LF, khong BOM. Xem chu thich dau tep.
$noiDung = ($moi -join "`n") + "`n"
[IO.File]::WriteAllText($envFile, $noiDung, (New-Object Text.UTF8Encoding($false)))

# Doi chung ngay: doc lai va DEM, khong in gia tri.
$sauKhiGhi = [IO.File]::ReadAllLines($envFile)
$dem = 0
foreach ($d in $sauKhiGhi) {
    foreach ($c in $CoV3) { if ($d -eq "$c=$GiaTri") { $dem++ } }
}
"SO CO DA DAT=$dem/$($CoV3.Count)" | Add-Content $sum -Encoding utf8
"SO DONG app.env=$($sauKhiGhi.Count)" | Add-Content $sum -Encoding utf8

$bom = [IO.File]::ReadAllBytes($envFile)
$coBom = ($bom.Length -ge 3 -and $bom[0] -eq 0xEF -and $bom[1] -eq 0xBB -and $bom[2] -eq 0xBF)
"CO BOM=$coBom" | Add-Content $sum -Encoding utf8
if ($coBom) {
    "EXITCODE=-3" | Add-Content $sum -Encoding utf8
    "LY_DO=app.env co BOM sau khi ghi - da khoi phuc tu sao luu" | Add-Content $sum -Encoding utf8
    Copy-Item $backup $envFile -Force
    exit 1
}
if ($dem -ne $CoV3.Count) {
    "EXITCODE=-4" | Add-Content $sum -Encoding utf8
    "LY_DO=chi dat duoc $dem/$($CoV3.Count) co - da khoi phuc tu sao luu" |
        Add-Content $sum -Encoding utf8
    Copy-Item $backup $envFile -Force
    exit 1
}

# ---- Nap lai vao nssm + restart dich vu ----------------------------------
# Xem chu thich dau tep: khong co buoc nay thi co moi KHONG CO TAC DUNG.
$napLai = Join-Path $Repo 'setup\nap_lai_env.ps1'
if (-not (Test-Path $napLai)) {
    "EXITCODE=-5" | Add-Content $sum -Encoding utf8
    "LY_DO=khong thay $napLai" | Add-Content $sum -Encoding utf8
    exit 1
}

# Don PSModulePath truoc khi sinh tien trinh con 5.1 - xem deploy_nang_quyen.ps1.
$psmp = @(
    "$env:ProgramFiles\WindowsPowerShell\Modules",
    "$env:SystemRoot\system32\WindowsPowerShell\v1.0\Modules"
) -join ';'
$env:PSModulePath = $psmp

$out = Join-Path $LogDir "co-v3-$stamp.out.log"
$err = Join-Path $LogDir "co-v3-$stamp.err.log"
$p = Start-Process powershell `
        -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$napLai`"" `
        -RedirectStandardOutput $out -RedirectStandardError $err `
        -Wait -PassThru

"NAP LAI EXITCODE=$($p.ExitCode)" | Add-Content $sum -Encoding utf8
"EXITCODE=$($p.ExitCode)" | Add-Content $sum -Encoding utf8
"KET THUC=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Add-Content $sum -Encoding utf8

if ($p.ExitCode -eq 0) {
    Write-Host ''
    Write-Host "CO V3 DA $(if ($Tat) { 'TAT' } else { 'BAT' }) - $dem co, EXITCODE=0." -ForegroundColor Green
} else {
    Write-Host ''
    Write-Host "HONG o buoc nap lai env - EXITCODE=$($p.ExitCode). Xem $err" -ForegroundColor Red
}
Write-Host "Ket qua: $sum"
Start-Sleep -Seconds 6
exit $p.ExitCode
