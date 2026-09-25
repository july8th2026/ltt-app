<#
.SYNOPSIS
    B3 - chay bai do dac mot lan (tests\test_b3_do_dac_mot_lan.py) voi moi
    truong production nap tu app.env, giong het khuon cua nghiem_thu_asv.ps1
    nhung KHONG chay bo test_448/test_3001 day du.

.NOTES
    Can Administrator (de doc secrets\app.env, ACL cua no la dung).
    Pure ASCII.
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = ''
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$boTest  = Join-Path $Repo 'tests\test_b3_do_dac_mot_lan.py'
foreach ($p in @($envFile, $boTest)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw "Can quyen Administrator de doc $envFile."
}

$soBien = 0
foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    $ten = $d.Substring(0, $i).Trim()
    $gt  = $d.Substring($i + 1)
    if ($ten) {
        Set-Item -Path "Env:$ten" -Value $gt
        $soBien++
    }
}
Write-Host "  [OK] Nap $soBien bien tu app.env (khong in gia tri)" -ForegroundColor Green

$coToken = [bool]($env:LTT_VOICE_SIDECAR_TOKEN)
$coCsdl  = [bool]($env:LTT_DATABASE_URL)

# Console Windows mac dinh cp1252, va bao cao mang van ban tieng Trung
# (ASR nguon) + tieng Viet co dau. Khong dat cai nay: mot print() cuoi bai
# nem UnicodeEncodeError SAU KHI da ghi xong tep, va pytest bao FAILED cho
# mot luot THAT RA da `done` (do that 25/09).
$env:PYTHONIOENCODING = 'utf-8'

$env:LTT_TEST_NANG = '1'

if (-not $env:LTT_ASV_PYTHON_TACH) {
    $pyTach = Join-Path $Root 'venv\Scripts\python.exe'
    if (Test-Path $pyTach) {
        $env:LTT_ASV_PYTHON_TACH = $pyTach
        Write-Host "  [OK] demucs se chay bang venv san pham: $pyTach" -ForegroundColor Green
    } else {
        Write-Host "  [!!] Khong thay $pyTach - demucs se dung trinh chay pytest." -ForegroundColor Yellow
    }
}

Remove-Item Env:LTT_ASV_POOL_URL -ErrorAction SilentlyContinue
if ($coCsdl) {
    $env:LTT_ASV_MODEL_THAT = '1'
    $env:LTT_ASV_POOL_URL   = $env:LTT_DATABASE_URL
    if (-not $env:LTT_TEST_DATABASE_URL) {
        $env:LTT_TEST_DATABASE_URL = ($env:LTT_DATABASE_URL -replace
            '/[^/?]+(\?|$)', '/lttplatform_test$1')
    }
    Write-Host "  [**] Model: THAT, qua pool khoa -> may B; CSDL: PostgreSQL nhap" -ForegroundColor Cyan
} else {
    Remove-Item Env:LTT_ASV_MODEL_THAT -ErrorAction SilentlyContinue
    Write-Host "  [--] Model: ban thay the (khong co LTT_DATABASE_URL trong app.env)" -ForegroundColor Yellow
}

if ($coToken) {
    $env:LTT_ASV_GIONG_THAT = '1'
    $cong = 8120
    if ($env:LTT_VOICE_SIDECAR_PORT) { $cong = [int]$env:LTT_VOICE_SIDECAR_PORT }
    $tcp = New-Object Net.Sockets.TcpClient
    try {
        $tcp.Connect('127.0.0.1', $cong)
        Write-Host "  [OK] Sidecar giong noi dang mo o :$cong - Che do: LTTStudioVoice THAT" -ForegroundColor Green
    } catch {
        throw "Sidecar giong noi khong mo o :$cong. Bat LTTStudioVoice roi chay lai."
    } finally {
        $tcp.Dispose()
    }
} else {
    Remove-Item Env:LTT_ASV_GIONG_THAT -ErrorAction SilentlyContinue
    Write-Host "  [--] Che do: SAPI (khong co LTT_VOICE_SIDECAR_TOKEN trong app.env)" -ForegroundColor Yellow
}

# Chon tep phim uu tien: tep NHO NHAT trong asv_e2e_that (= clip 190,0 s theo
# brief B3), tru khi nguoi goi da dat san LTT_B3_TEN_TEP.
if (-not $env:LTT_B3_TEN_TEP) {
    $thuMucPhim = Join-Path $Repo 'tests\fixtures\asv_e2e_that'
    $tepNho = Get-ChildItem $thuMucPhim -File |
        Where-Object { $_.Extension -in '.mp4', '.mov', '.mkv', '.webm', '.m4v' } |
        Sort-Object Length | Select-Object -First 1
    if ($tepNho) {
        $env:LTT_B3_TEN_TEP = $tepNho.Name
        Write-Host "  [OK] Phim chon: $($tepNho.Name) ($([math]::Round($tepNho.Length/1MB,1)) MiB)" -ForegroundColor Green
    }
}

if (-not $env:LTT_B3_RA) {
    $env:LTT_B3_RA = Join-Path $Repo '_ket_qua\b3_bao_cao.json'
}
if (-not $env:LTT_B3_MP4_RA) {
    $env:LTT_B3_MP4_RA = Join-Path $Repo '_ket_qua\b3_giai_doan1.mp4'
}

Write-Host ''
Write-Host "  Bao cao se ghi vao: $($env:LTT_B3_RA)"
Write-Host "  MP4 se ghi vao:     $($env:LTT_B3_MP4_RA)"
Write-Host ''

$cu = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& python -m pytest -q -p no:randomly $boTest -s
$maThoat = $LASTEXITCODE
$ErrorActionPreference = $cu

Write-Host ''
if ($maThoat -eq 0) {
    Write-Host "  [OK] Do dac xong. EXITCODE=$maThoat" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Do dac gap loi. EXITCODE=$maThoat" -ForegroundColor Red
}
exit $maThoat
