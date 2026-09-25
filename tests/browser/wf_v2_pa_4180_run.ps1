<#
.SYNOPSIS
    Chay tests/browser/wf_v2_pa_4180_canvas_bam_that.js tren mot may chu thu
    that (khong phai production 8100).

.DESCRIPTION
    Dang nhap KHONG go mat khau: ve SSO mot lan qua setup/ve_dang_nhap_thu.ps1
    (song 90 giay, dung mot lan), roi goi playwright-cli de doi trinh duyet
    that qua kich ban .js canh nhau. Can Administrator (ve SSO doc app.env).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\tests\browser\wf_v2_pa_4180_run.ps1
    powershell -ExecutionPolicy Bypass -File .\tests\browser\wf_v2_pa_4180_run.ps1 -Email khach2.thu@lttstudios.local -Port 8199
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Email = 'khach3.thu@lttstudios.local',
    [int]$Port = 8199,
    [string]$Session = 'wfb3'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot | Split-Path -Parent
$goc = "http://127.0.0.1:$Port"

Write-Output "[1/3] Mint ve SSO cho $Email -> $goc"
$ve = & powershell -ExecutionPolicy Bypass -File (Join-Path $repo 'setup\ve_dang_nhap_thu.ps1') `
    -Root $Root -Email $Email -Goc $goc
if ($LASTEXITCODE -ne 0 -or -not $ve) { throw "Khong mint duoc ve SSO (thoat $LASTEXITCODE)" }
Write-Output "  ve: $ve"

Write-Output "[2/3] Doi ve (song 90 giay, dung mot lan) va vao Canvas"
playwright-cli "-s=$Session" goto "$ve" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "playwright-cli goto ve SSO that bai" }

Write-Output "[3/3] Chay kich ban that: wf_v2_pa_4180_canvas_bam_that.js"
$scriptPath = Join-Path $PSScriptRoot 'wf_v2_pa_4180_canvas_bam_that.js'
$outLines = playwright-cli "-s=$Session" run-code "--filename=$scriptPath" 2>&1
$outLines | Write-Output
$out = ($outLines | Out-String)

# Xet DUNG noi dung tra ve cua kich ban (`return {status:'PASS',...}`), KHONG
# xet $LASTEXITCODE cua playwright-cli: no phan anh "co console error nao
# khong" noi chung (vd loi da biet, da duoc kich ban loc rieng va CO Y bo
# qua — xem canh bao dau tep .js), khong phai kich ban co throw hay khong.
# ⚠️ `$out` PHAI la MOT chuoi (Out-String), khong phai mang dong: `-match`/
#    `-notmatch` tren mot MANG loc TUNG PHAN TU va tra ve mang ket qua —
#    mot mang khong rong la truthy trong `if`, nen `$out -notmatch X` gan
#    nhu luon dung (moi dong KHAC dong chua X deu "khong khop X").
if ($out -match '### Error' -or $out -notmatch '"status":\s*"PASS"') {
    Write-Output ''
    Write-Output 'RESULT: FAIL'
    exit 1
}
Write-Output ''
Write-Output 'RESULT: PASS'
exit 0
