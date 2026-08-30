<#
.SYNOPSIS
    Install VieNeu-TTS v3 Turbo into an isolated CUDA venv (LTT VOICE sidecar).

.DESCRIPTION
    vieneu 3.3.0 pins transformers==4.57.6 and the GPU path pins torch==2.8.0+cu128.
    The platform venv uses a newer Blackwell torch build, so installing vieneu
    in-place would downgrade it and break every other GPU app. Same rule that
    created whisperx-venv; this is the second instance.

    Idempotent BY VERSION, not by "already exists": rollback.ps1 restores app\
    but never touches this venv, so an installer that skips when the directory is
    present would leave a venv that does not match the restored code.

    Prints the venv python path on stdout so 2-cai-dat.ps1 can capture it.

.NOTES
    Pure ASCII (CLAUDE.md rule 2). PowerShell 5.1 reads .ps1 without BOM as ANSI,
    so a single Vietnamese diacritic corrupts a whole statement and reports the
    error on a different line.
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$ReleaseDir = '',
    [string]$PythonExe = 'python',

    # WHERE THE VENV AND THE MODEL CACHE LIVE. Defaults to $Root, but this is a
    # real parameter and not a tidy-up: torch+cu128 alone is ~6 GB and the model
    # cache is another ~0.4 GB, and on 2026-08-30 the platform drive was measured
    # at 5.6 GB free out of 930 GB. `pip install` died halfway with
    # `[Errno 28] No space left on device` and left a 4.2 GB broken venv behind.
    #
    # Both directories must stay OUTSIDE app\ regardless of which drive they are
    # on: update.ps1 rotates app\ away on every release, and rollback.ps1 never
    # touches them. That is also why this installer is idempotent BY VERSION.
    [string]$VenvRoot = '',
    [switch]$SkipWarmCache
)

$ErrorActionPreference = 'Stop'
if (-not $ReleaseDir) { $ReleaseDir = Join-Path $Root 'app' }
if (-not $VenvRoot)   { $VenvRoot   = $Root }

$venv    = Join-Path $VenvRoot 'vieneu-venv'
$python  = Join-Path $venv 'Scripts\python.exe'
$hfCache = Join-Path $VenvRoot 'hf-cache'

# Refuse rather than half-install. A partial torch tree is worse than none: it
# imports far enough to look installed and then fails on a missing DLL, which
# reads like a CUDA problem and sends the next person down the wrong path.
$drive = (Split-Path -Qualifier $venv)
$freeGB = [math]::Round((Get-PSDrive ($drive.TrimEnd(':'))).Free / 1GB, 1)
if ($freeGB -lt 12) {
    throw "Only $freeGB GB free on $drive. vieneu-venv needs about 8 GB (torch+cu128 ~6 GB, model cache ~0.4 GB, headroom for pip's temp copies). Point -VenvRoot at a drive with room."
}
Write-Host "  [..] venv root: $VenvRoot ($freeGB GB free)" -ForegroundColor Cyan

# Pinned exactly. Changing a number here is changing the build, and it must go
# back through the V10 quality gate before it ships.
$TORCH_VER        = '2.8.0'
$TRANSFORMERS_VER = '4.57.6'
$VIENEU_VER       = '3.3.0'
$PERTH_VER        = '1.0.1'          # resemble-perth, NOT `perth`
$CU_INDEX         = 'https://download.pytorch.org/whl/cu128'

# Model repo + revision. PIN THE REVISION, never `main`: v3 full is coming and
# will change behaviour without changing the repo name.
$MODEL_REPO = 'pnnbao-ump/VieNeu-TTS-v3-Turbo'
$MODEL_REV  = '2da0efab622a1722125991736524f080b751ef5b'

function Write-Step($m) { Write-Host "  [..] $m" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }

# WHY THIS HELPER EXISTS, AND WHY `2>$null` IS NOT ENOUGH.
#
#   Under `$ErrorActionPreference = 'Stop'`, a native exe writing to stderr turns
#   into a NativeCommandError and TERMINATES the script -- even when we are only
#   ASKING a question ("is torch installed yet?") and "no" is the normal answer.
#   `2>$null` redirects the stream but does not undo the preference.
#
#   This is the same failure class that made install-whisperx-sidecar.ps1 throw
#   on 2026-08-05, after which 2-cai-dat.ps1 had to wrap it in try/catch and skip
#   it. Fixed here instead of wrapped: a PROBE must never kill the install.
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

# ------------------------------------------------------------------ venv -----
if (-not (Test-Path $python)) {
    Write-Step 'Creating vieneu-venv'
    & $PythonExe -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create vieneu venv' }
    & $python -m pip install --upgrade pip --quiet
}

# ------------------------------------------------------- torch (cu128) -------
# Probe BY VERSION and BY CUDA, not merely "is torch importable".
if (-not (Test-Py "import torch,sys; sys.exit(0 if torch.__version__.startswith('$TORCH_VER') and torch.cuda.is_available() else 1)")) {
    Write-Step "Installing torch $TORCH_VER + cu128 (large download, several minutes)"
    & $python -m pip install "torch==$TORCH_VER" "torchaudio==$TORCH_VER" --index-url $CU_INDEX --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install CUDA torch for vieneu' }
}
Write-Ok "torch $TORCH_VER"

# ------------------------------------------------------- transformers --------
if (-not (Test-Py "import importlib.metadata as m,sys; sys.exit(0 if m.version('transformers')=='$TRANSFORMERS_VER' else 1)")) {
    Write-Step "Installing transformers $TRANSFORMERS_VER (upstream pin for the GPU SDK)"
    & $python -m pip install "transformers==$TRANSFORMERS_VER" --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install transformers' }
}
Write-Ok "transformers $TRANSFORMERS_VER"

# ------------------------------------------------------------- vieneu --------
if (-not (Test-Py "import importlib.metadata as m,sys; sys.exit(0 if m.version('vieneu')=='$VIENEU_VER' else 1)")) {
    Write-Step "Installing vieneu $VIENEU_VER"
    & $python -m pip install "vieneu==$VIENEU_VER" --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install vieneu' }
}
Write-Ok "vieneu $VIENEU_VER"

# ------------------------------------------------- huggingface_hub PIN -------
# MEASURED 2026-08-30, and it is a real upstream inconsistency, not a local mess.
#
#   transformers 4.57.6 requires  huggingface-hub>=0.34.0,<1.0
#   vieneu 3.3.0 declares         huggingface_hub          (no upper bound)
#
# Installing in the README's order (torch -> transformers -> vieneu) lets the
# LAST install pull hub 1.29.0, which is past the transformers ceiling. pip warns
# ("dependency resolver does not currently take into account all the packages
# that are installed") and carries on, so the venv looks fine until the first
# `import transformers`, which then dies with an ImportError that names hub --
# pointing at the wrong package entirely.
#
# vieneu only uses snapshot_download / hf_hub_download, both present in 0.x, so
# pinning down is safe. This step must run AFTER vieneu or vieneu re-raises it.
if (-not (Test-Py "import transformers, huggingface_hub")) {
    Write-Step 'Pinning huggingface_hub<1.0 (transformers 4.57.6 ceiling)'
    & $python -m pip install "huggingface_hub>=0.34.0,<1.0" --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to pin huggingface_hub' }
}
Write-Ok 'transformers + huggingface_hub agree'

# ---------------------------------------------------------- WATERMARK --------
# See the long note in requirements-vieneu.txt. This is a PATCH for upstream
# issue #191: the PyPI package named `perth` is a threading helper, not the
# Resemble watermarker. Both packages claim the module name `perth`, so the
# wrong one MUST be uninstalled first or the result is not deterministic.
if (-not (Test-Py "import perth,sys; sys.exit(0 if hasattr(perth,'PerthImplicitWatermarker') else 1)")) {
    Write-Step 'Watermark patch: uninstall `perth` (wrong package), install `resemble-perth`'
    $before = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $python -m pip uninstall -y perth *> $null
    $ErrorActionPreference = $before
    & $python -m pip install "resemble-perth==$PERTH_VER" --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install resemble-perth' }
}
Write-Ok "resemble-perth $PERTH_VER"

# ------------------------------------------------------ sidecar server -------
if (-not (Test-Py "import fastapi,uvicorn")) {
    Write-Step 'Installing fastapi + uvicorn for the sidecar'
    & $python -m pip install "fastapi>=0.141.1,<1.0" "uvicorn[standard]>=0.52.0,<1.0" --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install sidecar server deps' }
}

# --------------------------------------------------------- warm cache --------
# Pre-fetch ~320 MB of weights. Without this the service's first start pulls
# them over the network while logging nothing, which looks exactly like a hang.
if (-not $SkipWarmCache) {
    if (-not (Test-Path $hfCache)) { New-Item -ItemType Directory -Path $hfCache -Force | Out-Null }
    $warm = Join-Path $ReleaseDir 'voice_sidecar\lam_am_cache.py'
    if (Test-Path $warm) {
        Write-Step 'Warming the HuggingFace cache (~320 MB)'
        $env:HF_HOME = $hfCache
        & $python $warm --repo $MODEL_REPO --revision $MODEL_REV
        if ($LASTEXITCODE -ne 0) { throw 'Failed to warm the HuggingFace cache' }
        Write-Ok 'HF cache ready'
    } else {
        Write-Host "  [SKIP] not found: $warm" -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------- acceptance -------
if (-not (Test-Py "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)")) {
    throw 'vieneu sidecar cannot access CUDA'
}
if (-not (Test-Py "import perth,sys; sys.exit(0 if hasattr(perth,'PerthImplicitWatermarker') else 1)")) {
    throw 'Watermarker missing: perth is still the wrong package (upstream issue 191)'
}
if (-not (Test-Py "import vieneu")) { throw 'Cannot import vieneu' }
# Import the engine for real, not just the package: the hub/transformers clash
# above only shows up on the first `from transformers import ...`.
if (-not (Test-Py "from vieneu._v3_turbo_engine.inference_v3_turbo import VieNeuTTSv3Turbo")) {
    throw 'Cannot import the v3 Turbo engine (check transformers / huggingface_hub versions)'
}

Write-Output $python
