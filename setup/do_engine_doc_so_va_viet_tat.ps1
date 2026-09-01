<#
.SYNOPSIS
    Measure how the engine ALREADY reads numbers, money and abbreviations.

.DESCRIPTION
    Answers the question that must come BEFORE porting the old system's text
    normalisation: does `sea-g2p` already handle these? Porting a number reader
    on top of a working number reader is not an upgrade -- it is two readers
    writing to the same place, and whichever runs last wins.

    Runs on the VieNeu venv (needs torch + the model), calls the engine
    directly. Touches the GPU; touches NO money -- no job, no credit entry.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\do_engine_doc_so_va_viet_tat.ps1
    powershell -ExecutionPolicy Bypass -File .\setup\do_engine_doc_so_va_viet_tat.ps1 -Nhom viettat

.NOTES
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Repo   = '',
    [string]$Preset = '',
    [string]$Nhom   = '',
    [string]$Ra     = 'tmp\engine_doc_so.json'
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

# !! DUNG interpreter cua VIENEU, khong phai venv nen tang. Sang 01/09 toi chay
#    nham `D:\LTTPlatform-runtime\vieneu-venv` thay vi duong that, va
#    `pyloudnorm` vang mat -> mot phep kiem bao "hong" trong khi no chi thieu
#    thu vien. Lay tu bien moi truong, dung doan.
$py = $env:LTT_VIENEU_PYTHON
if (-not $py) { $py = 'C:\LTTPlatform\vieneu-venv\Scripts\python.exe' }
$tool = Join-Path $Repo 'tools\do_engine_doc_so_va_viet_tat.py'
foreach ($p in @($py, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$env:PYTHONPATH = $Repo

$doiSo = @('--ra', $Ra)
if ($Preset) { $doiSo += @('--preset', $Preset) }
if ($Nhom)   { $doiSo += @('--nhom',   $Nhom) }

$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $py $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
