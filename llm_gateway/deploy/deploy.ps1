# deploy.ps1 - chep cong VLM tu MAY A sang MAY B. CHAY TREN MAY A.
#
#     powershell -ExecutionPolicy Bypass -File llm_gateway\deploy\deploy.ps1
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md). Da dinh mot lan trong phien nay:
# mot dau gach dai trong mot .ps1 lam vo ca script va bao loi o dong khac.
#
# BA DIEU KHONG BAO GIO DUOC DOI:
#   1. Ma nguon viet o MAY A, trong repo. Deploy bang script. KHONG BAO GIO sua tay
#      tren may B - lan deploy sau la mat trang, mat am tham (Q102).
#   2. May B KHONG giu bi mat nao cua nen tang: khong mat khau CSDL, khong khoa R2,
#      khong LTT_TOKEN_ENCRYPTION_KEY. No chi biet mot bearer token cua chinh no.
#   3. llama-server va llama-swap CHI nghe 127.0.0.1. Chi cong VLM nghe LAN.

[CmdletBinding()]
param(
    [string]$MayB    = "192.168.2.66",
    [string]$User    = "lengo",
    [string]$Khoa    = "$env:USERPROFILE\.ssh\nexus_b",
    [string]$Goc     = "H:/LTT_LLM",
    [switch]$BoQuaVenv                      # chi chep ma, khong dung venv lai
)

$ErrorActionPreference = "Stop"
$RepoGoc = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Buoc($s) { Write-Host ""; Write-Host "== $s" -ForegroundColor Cyan }
function Dat($s)  { Write-Host "  [OK]  $s" -ForegroundColor Green }
function Loi($s)  { Write-Host "  [LOI] $s" -ForegroundColor Red }
# !! `Canh` KHAC `Loi`: canh bao la "deploy xong nhung co dieu ban can biet",
#    con `Loi` la "deploy that bai". Gop hai cai lam mot thi hoac ta bao dong
#    gia, hoac ta nuot mat mot dieu can noi.
#
# !! Hai ham nay TUNG THIEU, va khoi canh bao cau hinh o buoc 3 goi chung nen
#    deploy CHET NGAY O DO - moi lan, khong tru lan nao. No qua duoc vong kiem
#    truoc day vi kiem do chi chay `[Parser]::ParseFile`, ma cu phap KHONG bat
#    duoc mot lenh khong ton tai. Bai hoc: mot script deploy chi duoc coi la da
#    kiem khi no CHAY HET, khong phai khi no PHAN TICH DUOC.
function Canh($s) { Write-Host "  [!]   $s" -ForegroundColor Yellow }
function Note($s) { Write-Host "$s" -ForegroundColor DarkGray }

# !! KHONG dat ten ham la `SSH`: PowerShell KHONG phan biet hoa thuong, nen ben
#    trong ham `& ssh` se phan giai ve CHINH HAM DO -> de quy vo han -> "call depth
#    overflow". Da dinh mot lan. Ten khac + goi `ssh.exe` tuong minh.
function ChayTrenB($lenh) {
    # !! `$ErrorActionPreference = "Stop"` bien MOI dong stderr cua mot .exe
    #    thanh NativeCommandError va lam ca script chet. OpenSSH nay in mot
    #    CANH BAO VO HAI ra stderr moi lan ket noi:
    #
    #      ** WARNING: connection is not using a post-quantum key exchange...
    #
    #    Ket qua: script CHET NGAY O BUOC 0, du ssh chay binh thuong. Da dinh
    #    24/08, va no chi cach nhau mot ban cap nhat OpenSSH.
    #
    #    Nen ha `ErrorActionPreference` quanh dung loi goi, va van chot bang
    #    `$LASTEXITCODE` - do moi la thu noi ssh thanh cong hay khong.
    $cu = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $r = & ssh.exe -i $Khoa -o BatchMode=yes "$User@$MayB" $lenh 2>&1
    } finally {
        $ErrorActionPreference = $cu
    }
    if ($LASTEXITCODE -ne 0) { Loi "ssh that bai: $lenh"; $r | Write-Host; exit 1 }
    # Bo dong canh bao cua ssh khoi ket qua tra ve, neu khong ben goi se coi
    # no la mot phan cua output tu may B.
    return ($r | Where-Object { $_ -notmatch 'post-quantum|store now|openssh' })
}

# --- 0. Kiem lien lac ----------------------------------------------------------
Buoc "0. Lien lac voi may B"
if (-not (Test-Path $Khoa)) { Loi "khong thay khoa SSH $Khoa"; exit 1 }
ChayTrenB "echo ok" | Out-Null
Dat "ssh $User@$MayB chay duoc"

# --- 1. Thu muc ----------------------------------------------------------------
Buoc "1. Thu muc tren may B"
$g = $Goc -replace "/", "\"
ChayTrenB "if not exist $g\gateway mkdir $g\gateway" | Out-Null
ChayTrenB "if not exist $g\logs mkdir $g\logs"       | Out-Null
ChayTrenB "if not exist $g\work mkdir $g\work"       | Out-Null
Dat "$Goc/gateway, /logs, /work"

# --- 2. Chep ma nguon ----------------------------------------------------------
# `llm_gateway` can `render_gateway.busy` (D-013/D-022 - khong chep lai 275 dong do).
# Hai goi nay deploy CUNG NHAU, do la giao uoc.
Buoc "2. Chep ma nguon"
foreach ($goi in @("llm_gateway", "render_gateway")) {
    $nguon = Join-Path $RepoGoc $goi
    if (-not (Test-Path $nguon)) { Loi "khong thay $nguon"; exit 1 }
    # Xoa __pycache__ o dich de khong con .pyc cu cua ban truoc.
    ChayTrenB "if exist $g\gateway\$goi\__pycache__ rd /s /q $g\gateway\$goi\__pycache__" | Out-Null
    & scp.exe -i $Khoa -o BatchMode=yes -q -r $nguon "${User}@${MayB}:$Goc/gateway/"
    if ($LASTEXITCODE -ne 0) { Loi "scp $goi that bai"; exit 1 }
    Dat "$goi"
}

# --- 3. Cau hinh llama-swap ----------------------------------------------------
Buoc "3. Cau hinh llama-swap"
& scp.exe -i $Khoa -o BatchMode=yes -q (Join-Path $PSScriptRoot "llama-swap.yaml") `
    "${User}@${MayB}:$Goc/gateway/llama-swap.yaml"
if ($LASTEXITCODE -ne 0) { Loi "scp llama-swap.yaml that bai"; exit 1 }
Dat "llama-swap.yaml"

# !! CHEP MOT TEP CAU HINH MA KHONG RESTART THI TEP AY KHONG PHAI CAU HINH.
#
#    `llama-swap` doc cau hinh MOT LAN luc khoi dong. Tep moi nam tren dia BAT
#    DONG cho toi khi co thu khac restart dich vu - co the vai ngay sau, va khi
#    do no co hieu luc AM THAM, khong ai cho doi.
#
#    Do 31/08: tep tren dia ghi luc 18:37 mo ta "input public 65K", tien trinh
#    llama-swap khoi dong luc 18:34, va `/running` van bao "90K". Ba con so, hai
#    su that khac nhau, khong mot dong canh bao nao.
#
# ! Script nay KHONG tu restart. `llama-swap` restart la unload model, va mot
#    lan unload giua gio phuc vu la mot quyet dinh van hanh chu khong phai mot
#    buoc phu cua deploy. Nhung IM LANG thi khong chap nhan duoc - nen no PHAT
#    HIEN va NOI.
# !! DONG NAY DA TUNG LAM VO CA SCRIPT. Ban dau no la mot chuoi NHAY KEP chua
#    `\"` va `^|`. PowerShell KHONG thoat bang backslash, nen `\"` ket thuc chuoi
#    SOM va phan con lai thanh lenh:
#
#      The term '\' is not recognized as the name of a cmdlet...
#
#    Va `$p` trong chuoi nhay kep bi may A khai trien thanh rong TRUOC khi gui.
#    Cung ho voi quy tac 3 cua CLAUDE.md ("PowerShell nuot dau ngoac kep").
#
# => NHAY DON o ngoai: may A khong khai trien gi, `"` ben trong la ky tu that,
#    `''` la mot dau nhay don. Va BO HAN dau ong - `@(...)[0]` thay cho
#    `| Select-Object -First 1`, nen khong con phai lo cmd.exe co an `|` khong
#    (do la ly do ban cu phai chap va `^|`).
$qSwap = 'powershell -NoProfile -Command "$p=@(Get-Process llama-swap -EA SilentlyContinue)[0]; if ($p) { $p.StartTime.ToString(''yyyy-MM-ddTHH:mm:ss'') } else { ''KHONG_CHAY'' }"'
$tuoiSwap = ChayTrenB $qSwap
$tuoiSwap = ($tuoiSwap -join "").Trim()
if ($tuoiSwap -and $tuoiSwap -ne "KHONG_CHAY") {
    try {
        $batDau = [datetime]::Parse($tuoiSwap)
        if ($batDau -lt (Get-Date).AddMinutes(-1)) {
            Canh "llama-swap dang chay tu $tuoiSwap - CAU HINH VUA CHEP CHUA CO HIEU LUC."
            Note "    Cau hinh dang chay van la ban CU. De ap ban moi:"
            Note "      Restart-Service LTTLlamaSwap    (tren may B - se UNLOAD model)"
            Note "    Neu chi doi ma cong (khong doi llama-swap.yaml) thi bo qua dong nay."
        }
    } catch { Canh "khong doc duoc thoi diem khoi dong cua llama-swap: $tuoiSwap" }
}

# --- 4. venv -------------------------------------------------------------------
if (-not $BoQuaVenv) {
    Buoc "4. venv + thu vien"
    $py = "C:\Users\$User\AppData\Local\Programs\Python\Python312\python.exe"
    ChayTrenB "if not exist $g\venv $py -m venv $g\venv" | Out-Null
    $pip = "$g\venv\Scripts\python.exe -m pip"
    ChayTrenB "$pip install --quiet --upgrade pip" | Out-Null
    ChayTrenB "$pip install --quiet fastapi uvicorn httpx psutil" | Out-Null
    Dat "fastapi uvicorn httpx psutil"
} else {
    Buoc "4. venv - BO QUA (-BoQuaVenv)"
}

# --- 5. Tep moi truong ---------------------------------------------------------
# !! GHI KHONG BOM (quy tac 1 cua CLAUDE.md). PowerShell 5.1 chen BOM voi
#    Out-File/Set-Content, va mot BOM o day lam dong dau tien doc sai.
Buoc "5. C:\ProgramData\LTTLlm\gateway.env"
$envDir = "C:\ProgramData\LTTLlm"
ChayTrenB "if not exist $envDir mkdir $envDir" | Out-Null

$co = ChayTrenB "if exist $envDir\gateway.env (echo CO) else (echo KHONG)"
if (($co -join "") -match "CO") {
    # Cap van hanh khong phai bi mat: migrate tai cho, giu nguyen token/model.
    # Khong dung PowerShell remote inline; scp file tam de tranh loi quoting va
    # dam bao UTF-8 khong BOM tren Windows PowerShell 5.1.
    $tamEnv = Join-Path $env:TEMP "gateway.env.migrate"
    & scp.exe -i $Khoa -o BatchMode=yes -q "${User}@${MayB}:C:/ProgramData/LTTLlm/gateway.env" $tamEnv
    if ($LASTEXITCODE -ne 0) { Loi "scp gateway.env ve de migrate that bai"; exit 1 }
    $dong = [IO.File]::ReadAllLines($tamEnv)
    $daInput = $false
    $daOutput = $false
    $daDongThoi = $false
    $dong = @($dong | ForEach-Object {
        if ($_ -match '^LTT_LLM_MAX_INPUT_TOKENS=') {
            $daInput = $true
            'LTT_LLM_MAX_INPUT_TOKENS=96256'
        } elseif ($_ -match '^LTT_LLM_MAX_OUTPUT_TOKENS=') {
            $daOutput = $true
            'LTT_LLM_MAX_OUTPUT_TOKENS=32768'
        } elseif ($_ -match '^LTT_LLM_MAX_DONG_THOI=') {
            $daDongThoi = $true
            'LTT_LLM_MAX_DONG_THOI=1'
        } else { $_ }
    })
    if (-not $daInput) { $dong += 'LTT_LLM_MAX_INPUT_TOKENS=96256' }
    if (-not $daOutput) { $dong += 'LTT_LLM_MAX_OUTPUT_TOKENS=32768' }
    if (-not $daDongThoi) { $dong += 'LTT_LLM_MAX_DONG_THOI=1' }
    [IO.File]::WriteAllText($tamEnv, ($dong -join "`n") + "`n", (New-Object Text.UTF8Encoding($false)))
    & scp.exe -i $Khoa -o BatchMode=yes -q $tamEnv "${User}@${MayB}:C:/ProgramData/LTTLlm/gateway.env"
    $rc = $LASTEXITCODE
    Remove-Item $tamEnv -Force -ErrorAction SilentlyContinue
    if ($rc -ne 0) { Loi "scp gateway.env da migrate that bai"; exit 1 }
    Dat "gateway.env da migrate input 96256, output 32768, concurrency 1 (giu token/model)"
} else {
    # Token sinh mot lan, ngau nhien. No KHONG phai bi mat cua nen tang - no chi
    # bao ve cong VLM tren LAN. Nhung van khong duoc in ra log.
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $token = [Convert]::ToBase64String($bytes) -replace "[+/=]", ""

    $noiDung = @(
        "# gateway.env - cong VLM may B. Sinh boi deploy.ps1, KHONG sua tay.",
        "LTT_LLM_HOST=127.0.0.1",
        "LTT_LLM_PORT=8299",
        "LTT_LLM_TOKEN=$token",
        "LTT_LLM_UPSTREAM_URL=http://127.0.0.1:8280",
        "LTT_LLM_COMFY_URL=http://127.0.0.1:8188",
        "# Fail-closed (Q92): rong = KHONG mo model nao. Mo bang cach liet ke ten.",
        "LTT_LLM_MODELS=",
        "# Tran do duoc o P5 (SO_DO_P2_P6.md). Doi thi phai do lai.",
        "LTT_LLM_MAX_INPUT_TOKENS=96256",
        "LTT_LLM_MAX_OUTPUT_TOKENS=32768",
        "LTT_LLM_MAX_DONG_THOI=1",
        "LTT_LLM_MAX_IMAGES=4",
        "# Nen do duoc: desktop 1515-1612 MiB, ComfyUI thuong tru 6211-16620 MiB.",
        "LTT_LLM_VRAM_SACH_MB=2500",
        "LTT_LLM_RAM_TRONG_GB=48"
    ) -join "`n"

    $tam = Join-Path $env:TEMP "gateway.env"
    [IO.File]::WriteAllText($tam, $noiDung, (New-Object Text.UTF8Encoding($false)))
    & scp.exe -i $Khoa -o BatchMode=yes -q $tam "${User}@${MayB}:C:/ProgramData/LTTLlm/gateway.env"
    Remove-Item $tam -Force
    Dat "gateway.env da tao (token sinh ngau nhien, KHONG in ra day)"
    Write-Host "  Doc token khi can:" -ForegroundColor Yellow
    Write-Host "    ssh -i $Khoa $User@$MayB ""findstr LTT_LLM_TOKEN $envDir\gateway.env""" -ForegroundColor Yellow
}

# --- 6. Kiem nhanh -------------------------------------------------------------
Buoc "6. Kiem import tren may B"
# !! Chay mot TEP .py, khong phai `python -c "..."` - quy tac 3 cua CLAUDE.md:
#    PowerShell nuot dau ngoac kep khi truyen cho .exe, va qua them mot lop ssh
#    nua thi hong chac chan. Da dinh mot lan trong phien nay.
$kq = ChayTrenB "$g\venv\Scripts\python.exe $g\gateway\llm_gateway\deploy\kiem_import.py"
$kq | ForEach-Object { Write-Host "  $_" }

Buoc "Xong"
Write-Host "  Buoc ke tiep:"
Write-Host "    1. Mo model:  sua LTT_LLM_MODELS trong $envDir\gateway.env"
Write-Host "    2. Cai dich vu (can Administrator tren may B):"
Write-Host "         powershell -ExecutionPolicy Bypass -File $Goc/gateway/llm_gateway/deploy/cai_dat_dich_vu.ps1"
Write-Host "    3. Nghiem thu:"
Write-Host "         powershell -ExecutionPolicy Bypass -File llm_gateway\deploy\kiem_tra.ps1"
