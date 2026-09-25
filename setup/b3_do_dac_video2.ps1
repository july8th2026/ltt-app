<#
.SYNOPSIS
    Chon tep phim LON HON (~275s) trong asv_e2e_that/ va chay b3_do_dac.ps1
    voi duong ra RIENG, khong de ghi de bao cao/MP4 cua video 1 (~190s).
#>
$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot

$thuMucPhim = Join-Path $Repo 'tests\fixtures\asv_e2e_that'
$tep = Get-ChildItem $thuMucPhim -File |
    Where-Object { $_.Extension -in '.mp4', '.mov', '.mkv', '.webm', '.m4v' } |
    Sort-Object Length -Descending | Select-Object -First 1
if (-not $tep) { throw "Khong tim thay phim nao trong $thuMucPhim" }

$env:LTT_B3_TEN_TEP = $tep.Name
$env:LTT_B3_RA       = Join-Path $Repo '_ket_qua\b3_bao_cao_video2_275s.json'
$env:LTT_B3_MP4_RA   = Join-Path $Repo '_ket_qua\b3_giai_doan1_video2_275s.mp4'

Write-Host "  [OK] Video 2 chon: $($tep.Name) ($([math]::Round($tep.Length/1MB,1)) MiB)" -ForegroundColor Green

& (Join-Path $PSScriptRoot 'b3_do_dac.ps1')
exit $LASTEXITCODE
