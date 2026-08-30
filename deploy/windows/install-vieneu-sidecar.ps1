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
    Pure ASCII (CLAUDE.md rule 2). PowerShell 5.1 reads .ps1 without BOM as ANSI.
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$ReleaseDir = '',
    [string]$PythonExe = 'python',
    [switch]$SkipWarmCache
)

$ErrorActionPreference = 'Stop'
if (-not $ReleaseDir) { $ReleaseDir = Join-Path $Root 'app' }

$venv    = Join-Path $Root 'vieneu-venv'
$python  = Join-Path $venv 'Scripts\python.exe'
$hfCache = Join-Path $Root 'hf-cache'

# Ghim chinh xac. Doi so o day = doi ban va = phai chay lai cong chat luong V10.
$TORCH_VER        = '2.8.0'
$TRANSFORMERS_VER = '4.57.6'
$VIENEU_VER       = '3.3.0'
$PERTH_VER        = '1.0.1'          # resemble-perth
$CU_INDEX         = 'https://download.pytorch.org/whl/cu128'

# Model repo + revision. GHIM REVISION, khong lay `main`: v3 full sap ra va se
# doi hanh vi ma khong doi ten repo.
$MODEL_REPO = 'pnnbao-ump/VieNeu-TTS-v3-Turbo'
$MODEL_REV  = '2da0efab622a1722125991736524f080b751ef5b'

function Write-Step($m) { Write-Host "  [..] $m" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }

# 🔴 VI SAO CAN HAM NAY, VA VI SAO `2>$null` KHONG DU.
#
#    Voi `$ErrorActionPreference = 'Stop'`, mot exe NGOAI ghi ra stderr se thanh
#    NativeCommandError va KET THUC script — ke ca khi ta chi dang HOI mot cau
#    ("da co torch chua?") va mot cau tra loi "chua" la hoan toan binh thuong.
#    `2>$null` chuyen huong stream nhung KHONG go bo hanh vi cua preference.
#
#    Do dung lop loi da lam `install-whisperx-sidecar.ps1` nem loi ngay 2026-08-05
#    va bi `2-cai-dat.ps1` phai boc lai trong try/catch de bo qua. Sua o day thay
#    vi boc lai: mot phep DO khong duoc phep giet quy trinh cai.
function Test-Py {
    param([string]$Code)
    $truoc = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $python -c $Code *> $null
        return ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = $truoc
    }
}

# ---------------------------------------------------------------- venv --------
if (-not (Test-Path $python)) {
    Write-Step 'Tao vieneu-venv'
    & $PythonExe -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create vieneu venv' }
    & $python -m pip install --upgrade pip --quiet
}

# ------------------------------------------------------- torch (cu128) -------
# Kiem THEO PHIEN BAN va CUDA, khong chi kiem "co torch khong".
& $python -c "import torch,sys; sys.exit(0 if torch.__version__.startswith('$TORCH_VER') and torch.cuda.is_available() else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Step "Cai torch $TORCH_VER + cu128 (tai ve lon, cho vai phut)"
    & $python -m pip install "torch==$TORCH_VER" "torchaudio==$TORCH_VER" --index-url $CU_INDEX --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install CUDA torch for vieneu' }
}
Write-Ok "torch $TORCH_VER"

# ------------------------------------------------------- transformers --------
& $python -c "import importlib.metadata as m,sys; sys.exit(0 if m.version('transformers')=='$TRANSFORMERS_VER' else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Step "Cai transformers $TRANSFORMERS_VER (ban upstream ghim cho GPU SDK)"
    & $python -m pip install "transformers==$TRANSFORMERS_VER" --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install transformers' }
}
Write-Ok "transformers $TRANSFORMERS_VER"

# ------------------------------------------------------------- vieneu --------
& $python -c "import importlib.metadata as m,sys; sys.exit(0 if m.version('vieneu')=='$VIENEU_VER' else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Step "Cai vieneu $VIENEU_VER"
    & $python -m pip install "vieneu==$VIENEU_VER" --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install vieneu' }
}
Write-Ok "vieneu $VIENEU_VER"

# --------------------------------------------------------- WATERMARK ---------
# Xem chu thich dai trong requirements-vieneu.txt. Day la mot BAN VA cho upstream
# issue #191: goi `perth` tren PyPI la mot thu vien threading, khong phai
# watermarker. Ca hai goi cung chiem ten module `perth` nen PHAI go truoc.
& $python -c "import perth,sys; sys.exit(0 if hasattr(perth,'PerthImplicitWatermarker') else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Step 'Va watermark: go `perth` (goi SAI), cai `resemble-perth`'
    & $python -m pip uninstall -y perth --quiet 2>$null | Out-Null
    & $python -m pip install "resemble-perth==$PERTH_VER" --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install resemble-perth' }
}

# ----------------------------------------------------- may chu sidecar -------
& $python -c "import fastapi,uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Step 'Cai fastapi + uvicorn cho sidecar'
    & $python -m pip install "fastapi>=0.141.1,<1.0" "uvicorn[standard]>=0.52.0,<1.0" --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install sidecar server deps' }
}

# ------------------------------------------------------- lam am cache --------
# Tai truoc ~320 MB trong so. Khong lam thi lan khoi dong dau tien cua dich vu
# phai tai mang, va no im lang trong vai phut trong nhu treo.
if (-not $SkipWarmCache) {
    if (-not (Test-Path $hfCache)) { New-Item -ItemType Directory -Path $hfCache -Force | Out-Null }
    $warm = Join-Path $ReleaseDir 'voice_sidecar\lam_am_cache.py'
    if (Test-Path $warm) {
        Write-Step 'Lam am cache HuggingFace (~320 MB)'
        $env:HF_HOME = $hfCache
        & $python $warm --repo $MODEL_REPO --revision $MODEL_REV
        if ($LASTEXITCODE -ne 0) { throw 'Failed to warm the HuggingFace cache' }
        Write-Ok 'Cache HF san sang'
    } else {
        Write-Host "  [SKIP] khong thay $warm" -ForegroundColor Yellow
    }
}

# ----------------------------------------------------------- nghiem thu ------
& $python -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)"
if ($LASTEXITCODE -ne 0) { throw 'vieneu sidecar cannot access CUDA' }

& $python -c "import perth,sys; sys.exit(0 if hasattr(perth,'PerthImplicitWatermarker') else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Watermarker missing: `perth` is still the wrong package (upstream issue 191)' }

& $python -c "import vieneu,sys" 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Cannot import vieneu' }

Write-Output $python
