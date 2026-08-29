# dat_bien_env.ps1 - dat MOT bien trong secrets\app.env, an toan.
#
#     powershell -ExecutionPolicy Bypass -File .\setup\dat_bien_env.ps1 -Ten LTT_GPU_MONG_DOI -Gia_tri 2
#     powershell -ExecutionPolicy Bypass -File .\setup\dat_bien_env.ps1 -Ten LTT_GPU_MONG_DOI -Xoa
#     powershell -ExecutionPolicy Bypass -File .\setup\dat_bien_env.ps1 -Ten LTT_GPU_MONG_DOI   # chi xem
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! VI SAO CAN MOT SCRIPT CHO MOT DONG TEXT.
#
#    `setup\cong_tac_tool_api.ps1` da tra gia de hoc ba cach hong, va ca ba deu
#    IM LANG. Nhung no chi che DUNG MOT bien (`LTT_PUBLIC_API_TOOLS`) - ba cach
#    hong do ap cho MOI bien:
#
#      1. Trinh soan thao chen BOM  -> `json.load()` vo o cho khac,
#         `/health/ready` tra 503 trong khi dich vu van chay.
#         Loi nay DA THUC SU LAM SAP PRODUCTION o du an nay.
#      2. Go de len mot dong khac   -> mat mot bien dang phuc vu, khong ai biet
#         cho toi khi co nguoi goi.
#      3. Sua xong roi restart      -> KHONG AN GI. nssm nuong bien moi truong
#         vao dang ky dich vu luc CAI (`AppEnvironmentExtra`); tien trinh doc
#         `os.environ`, khong doc lai app.env. Phai chay `nap_lai_env.ps1`.
#
#    Ngay 29/08 phai dat `LTT_GPU_MONG_DOI` va khong co cong cu nao - phai viet
#    mot script MOT LAN trong thu muc tam. Lan sau se lai nhu vay. Tep nay la de
#    khong con lan sau.
#
# !! KHONG IN GIA TRI CUA BIEN KHAC. Script chi doc/ghi dung mot dong va chi in
#    dong do. `-Xem` in ten bien co mat, KHONG in gia tri nao.
#
# !! KHONG DAT BI MAT BANG SCRIPT NAY. Khoa, token, mat khau khong duoc di qua
#    dong lenh: chung vao lich su shell, vao log, vao ban ghi tien trinh. Script
#    TU CHOI cac ten trong tu bi mat ben duoi. Bi mat thi sua tep truc tiep tren
#    may chu, boi nguoi.

[CmdletBinding()]
param(
    [string]$Ten,
    [string]$Gia_tri,
    [switch]$Xoa,
    [switch]$Xem,
    [string]$EnvFile = 'C:\LTTPlatform\secrets\app.env'
)

$ErrorActionPreference = 'Stop'

# Ten trong nay khong duoc dat qua dong lenh. Khop khong phan biet hoa thuong,
# va khop theo MANH de `..._KEY_2` hay `MY_SECRET_X` cung dinh.
$TU_BI_MAT = @('SECRET', 'TOKEN', 'PASSWORD', 'PASSWD', 'PEPPER', 'CREDENTIAL',
               'PRIVATE', 'APIKEY', 'API_KEY', 'DSN')

function Doc-Env([string]$duong) {
    if (-not (Test-Path -LiteralPath $duong)) {
        Write-Host "Khong thay $duong" -ForegroundColor Red; exit 1
    }
    $bytes = [IO.File]::ReadAllBytes($duong)
    # (1) BOM: DUNG LAI. Khong tu sua mot tep bi mat.
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Host "app.env dang co BOM - DUNG LAI. Khong tu sua tep bi mat." -ForegroundColor Red
        exit 2
    }
    return $bytes
}

$bytes = Doc-Env $EnvFile
$txt = [Text.Encoding]::UTF8.GetString($bytes)
# Giu nguyen kieu xuong dong cua tep, khong ap kieu cua may dang chay.
$nl  = if ($txt -match "`r`n") { "`r`n" } else { "`n" }
$dong = [Collections.ArrayList]@($txt -split "`r?`n")

if ($Xem -or -not $Ten) {
    # Chi in TEN, khong in gia tri.
    $ten_co = @()
    foreach ($d in $dong) {
        if ($d -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') { $ten_co += $Matches[1] }
    }
    Write-Host "Co $($ten_co.Count) bien (khong in gia tri):"
    $ten_co | Sort-Object | ForEach-Object { Write-Host "  $_" }
    exit 0
}

if ($Ten -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
    Write-Host "Ten bien khong hop le: $Ten" -ForegroundColor Red; exit 3
}
foreach ($tu in $TU_BI_MAT) {
    if ($Ten.ToUpper().Contains($tu)) {
        Write-Host "TU CHOI: '$Ten' trong nhu mot bi mat ('$tu')." -ForegroundColor Red
        Write-Host "Bi mat khong duoc di qua dong lenh - no vao lich su shell va vao log."
        Write-Host "Sua tep truc tiep tren may chu, boi nguoi."
        exit 4
    }
}
if (-not $Xoa -and -not $PSBoundParameters.ContainsKey('Gia_tri')) {
    Write-Host "Thieu -Gia_tri (hoac -Xoa)." -ForegroundColor Red; exit 3
}
if ($Gia_tri -match "[`r`n]") {
    Write-Host "Gia tri khong duoc chua ky tu xuong dong." -ForegroundColor Red; exit 3
}

# (2) Khop DUNG khoa bang bo chon neo dau dong, khong `StartsWith`:
#     `LTT_GPU` khong duoc khop `LTT_GPU_MONG_DOI`.
$i = -1
for ($k = 0; $k -lt $dong.Count; $k++) {
    if ($dong[$k] -match "^\s*$([regex]::Escape($Ten))\s*=") { $i = $k; break }
}

if ($Xoa) {
    if ($i -lt 0) { Write-Host "  $Ten von khong co - khong doi gi."; exit 0 }
    Write-Host "  bo dong: $Ten"
    $dong.RemoveAt($i)
} else {
    $moi = "$Ten=$Gia_tri"
    if ($i -ge 0) {
        if ($dong[$i] -eq $moi) { Write-Host "  $Ten da dung gia tri - khong doi gi."; exit 0 }
        $dong[$i] = $moi
    } else {
        while ($dong.Count -gt 0 -and $dong[$dong.Count - 1] -eq '') { $dong.RemoveAt($dong.Count - 1) }
        [void]$dong.Add($moi)
        [void]$dong.Add('')
    }
    Write-Host "  moi: $moi" -ForegroundColor Green
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$bak = "$EnvFile.truoc-$stamp"
[IO.File]::WriteAllBytes($bak, $bytes)
Write-Host "  sao luu: $bak"

# !! UTF8Encoding($false) = KHONG BOM. `Out-File`/`Set-Content -Encoding utf8`
#    tren PowerShell 5.1 chen BOM - quy tac 1 cua CLAUDE.md.
[IO.File]::WriteAllText($EnvFile, ($dong -join $nl), (New-Object Text.UTF8Encoding($false)))

# Doc LAI tu dia va dem. Kiem ket qua, khong kiem bien vua gan - mot cau hoi
# khong bao gio sai duoc thi khong phai mot chot chan.
$lai = [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($EnvFile))
$dem = ([regex]::Matches($lai, "(?m)^\s*$([regex]::Escape($Ten))\s*=")).Count
$mong = if ($Xoa) { 0 } else { 1 }
if ($dem -ne $mong) {
    Write-Host "HONG: so dong mang '$Ten' la $dem, mong doi $mong." -ForegroundColor Red
    Write-Host "Ban truoc con o: $bak"
    exit 5
}

Write-Host ""
Write-Host "CHUA CO TAC DUNG. nssm nuong bien moi truong luc cai, nen phai nap lai:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File .\setup\nap_lai_env.ps1"
exit 0
