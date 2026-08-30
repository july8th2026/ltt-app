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

# WHY THIS HELPER EXISTS, AND WHY `2>$null` IS NOT ENOUGH.
#
#   Under `$ErrorActionPreference = 'Stop'` (set above), a native exe writing to
#   stderr becomes a NativeCommandError and TERMINATES the script -- even when we
#   are only ASKING a question ("is torch installed yet?") and "no" is the normal
#   answer. `2>$null` redirects the stream but does not undo the preference.
#
#   MEASURED 2026-08-30: this is exactly why this script threw on 2026-08-05,
#   after which 2-cai-dat.ps1 wrapped it in try/catch and skipped it. It has not
#   installed anything since. `C:\LTTPlatform\whisperx-venv` was 0.01 GB -- a bare
#   venv, no packages -- so `whisperx_available()` returned False and
#   apps/autosubvideo silently ran its faster-whisper fallback, losing word-level
#   alignment. It labelled the degradation honestly
#   (`alignment_status: fallback_unaligned`) but nobody was reading the label.
#
#   A PROBE must never kill the install.
function Test-Py {
    param([string]$Code)
    $before = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $python -c $Code *> $null
        return ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = $before
    }
}

$torchOk = Test-Py "import torch,sys; ok=torch.__version__.startswith('2.8.') and torch.cuda.is_available(); sys.exit(0 if ok else 1)"
if (-not $torchOk) {
    & $python -m pip install --upgrade pip --quiet
    & $python -m pip install 'torch==2.8.0' 'torchvision==0.23.0' 'torchaudio==2.8.0' --index-url https://download.pytorch.org/whl/cu128 --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install WhisperX CUDA torch' }
}

if (-not (Test-Py "import whisperx,sys; import importlib.metadata as m; sys.exit(0 if m.version('whisperx')=='3.8.6' else 1)")) {
    & $python -m pip install -r $requirements --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install WhisperX dependencies' }
}

if (-not (Test-Py "import torch,whisperx,sys; sys.exit(0 if torch.cuda.is_available() else 1)")) {
    throw 'WhisperX sidecar cannot access CUDA'
}
Write-Output $python
