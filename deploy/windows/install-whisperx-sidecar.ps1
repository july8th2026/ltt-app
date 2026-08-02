<#
.SYNOPSIS
    Install WhisperX in an isolated CUDA venv.

.DESCRIPTION
    WhisperX 3.8.6 requires torch 2.8.x. The platform venv uses a newer
    Blackwell torch build, so installing WhisperX in-place would downgrade and
    break other GPU apps. This script is idempotent and keeps it under Root.
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$ReleaseDir = '',
    [string]$PythonExe = 'python'
)

$ErrorActionPreference = 'Stop'
if (-not $ReleaseDir) { $ReleaseDir = Join-Path $Root 'app' }
$venv = Join-Path $Root 'whisperx-venv'
$python = Join-Path $venv 'Scripts\python.exe'
$requirements = Join-Path $ReleaseDir 'requirements-whisperx.txt'
if (-not (Test-Path $requirements)) { throw 'requirements-whisperx.txt is missing' }

if (-not (Test-Path $python)) {
    & $PythonExe -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create WhisperX venv' }
}

& $python -c "import torch,sys; ok=torch.__version__.startswith('2.8.') and torch.cuda.is_available(); sys.exit(0 if ok else 1)" 2>$null
$torchOk = ($LASTEXITCODE -eq 0)
if (-not $torchOk) {
    & $python -m pip install --upgrade pip --quiet
    & $python -m pip install 'torch==2.8.0' 'torchvision==0.23.0' 'torchaudio==2.8.0' --index-url https://download.pytorch.org/whl/cu128 --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install WhisperX CUDA torch' }
}

& $python -c "import whisperx,sys; import importlib.metadata as m; sys.exit(0 if m.version('whisperx')=='3.8.6' else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $python -m pip install -r $requirements --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install WhisperX dependencies' }
}

& $python -c "import torch,whisperx,sys; sys.exit(0 if torch.cuda.is_available() else 1)"
if ($LASTEXITCODE -ne 0) { throw 'WhisperX sidecar cannot access CUDA' }
Write-Output $python
