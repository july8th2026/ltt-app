<#
.SYNOPSIS
    Run the LTT VOICE end-to-end check with production's environment loaded.

.DESCRIPTION
    Same narrow bridge as tai_khoan_thu.ps1: read app.env into THIS process only,
    run one named tool, exit. Never prints a value from app.env.

    The tool submits a real job and waits for the REAL production worker to pick
    it up. It does not call the handler itself -- a script that does would stay
    green even when the queue is broken, when the worker pool lacks the `voice`
    lane, or when the voice service is down. Those are the three things that
    actually break on deploy.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\chay_thu_giong.ps1 -TaiVe out.wav

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root  = 'C:\LTTPlatform',
    [string]$Repo  = '',
    [string]$Email = '',
    [string]$Text  = '',
    [string]$TaiVe = '',
    [int]$ChoGiay  = 300
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\chay_thu_ltt_voice.py'
foreach ($p in @($envFile, $venvPy, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Can quyen Administrator de doc $envFile" }

$so = 0
foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    # !! Ten bien phai KHONG trung mot tham so nao cua chinh script. PowerShell
    #    khong phan biet hoa thuong, nen mot vong lap dung $ten se ghi de tham
    #    so -Ten bang bien moi truong CUOI CUNG trong app.env. Da xay ra that o
    #    chay_thu_ghi_danh.ps1 ngay 31/08: giong duoc tao ra ten la "HF_HOME".
    #    `tools/check_ps_bien_trung_tham_so.py` chot viec nay.
    $bienEnv = $d.Substring(0, $i).Trim()
    if ($bienEnv) { Set-Item -Path "Env:$bienEnv" -Value $d.Substring($i + 1); $so++ }
}
Write-Host "  [OK] Nap $so bien tu app.env (khong in gia tri)" -ForegroundColor Green

$doiSo = @('--cho-giay', "$ChoGiay")
if ($Email) { $doiSo += @('--email', $Email) }
if ($Text)  { $doiSo += @('--text',  $Text) }
if ($TaiVe) { $doiSo += @('--tai-ve', $TaiVe) }

# !! BAY DA DINH BA LAN TRONG HAI NGAY - xem `Test-Py` trong
#    `deploy\windows\install-vieneu-sidecar.ps1`.
#
#    Voi `$ErrorActionPreference = 'Stop'`, mot exe NGOAI ghi ra stderr se thanh
#    NativeCommandError va KET THUC script. Python ghi ra stderr vi rat nhieu ly
#    do binh thuong (SyntaxWarning, mot dong chan doan), va khi do:
#      - lenh sau `;` KHONG chay  -> `EXITCODE=` khong bao gio duoc ghi
#      - va `EXITCODE` RONG doc len giong het "tien trinh khong chay"
#    tuc mot loi vo hai bi doc thanh mot loi nghiem trong.
#
#    Nen quanh LOI GOI CUOI: ha xuong 'Continue', doc $LASTEXITCODE, roi tra lai.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
