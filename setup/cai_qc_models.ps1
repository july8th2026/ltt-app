# Create C:\LTTPlatform\qc-venv for Auto Scan Video QC models (SQUIM, MetricX).
# Additive: does not touch app\, venv\ or other venvs. Safe to re-run.
# Models are NOT downloaded here; each runner downloads a pinned revision into HF_HOME
# (C:\LTTPlatform\hf-cache) and verifies its checksum.
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$PythonExe = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
)
$ErrorActionPreference = 'Stop'
$venv = Join-Path $Root 'qc-venv'
$req = Join-Path $PSScriptRoot 'qc_models_requirements.txt'
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    & $PythonExe -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'venv create failed' }
}
$py = Join-Path $venv 'Scripts\python.exe'
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r $req --quiet
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }
& $py -c "import torch, torchaudio, transformers, jiwer; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
if ($LASTEXITCODE -ne 0) { throw 'import check failed' }
Set-Content -Path (Join-Path $venv 'READY.txt') -Value (Get-Date -Format o) -Encoding ascii
Write-Host "OK $venv"
