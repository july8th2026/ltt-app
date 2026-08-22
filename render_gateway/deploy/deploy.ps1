# deploy.ps1 - day cong render tu repo (may A) sang may B qua SSH.
#
# CHAY TREN MAY A:
#   powershell -ExecutionPolicy Bypass -File render_gateway\deploy\deploy.ps1
#
# QUY TAC BAT BUOC (CLAUDE.md):
#   1. Tep .ps1 nay THUAN ASCII. PowerShell 5.1 doc .ps1 khong BOM theo bang ma
#      ANSI; mot dau tieng Viet lam hong ca cau lenh va bao loi o dong khac.
#   2. Moi tep cau hinh ghi bang [IO.File]::WriteAllText voi UTF8Encoding($false)
#      - KHONG dung Out-File/Set-Content -Encoding utf8. PowerShell 5.1 chen BOM,
#      json.load() vo, va loi do DA TUNG LAM SAP PRODUCTION o du an nay.
#
# KHONG cai dich vu va KHONG dung tuong lua o day: hai viec do can quyen
# Administrator TREN MAY B. Script nay chuan bi het, roi in ra lenh de chu du an
# chay bang cua so nang quyen - xem cai_dat_dich_vu.ps1.

[CmdletBinding()]
param(
    [string]$MayB   = "192.168.2.66",
    [string]$User   = "lengo",
    [string]$Key    = "$env:USERPROFILE\.ssh\nexus_b",
    [string]$Dich   = "E:\AI\ltt_render",
    [switch]$ChiKiem                       # chi so hash, khong chep gi
)

$ErrorActionPreference = "Stop"
$RepoGoc = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Nguon   = Join-Path $RepoGoc "render_gateway"

function Buoc($s) { Write-Host ""; Write-Host "== $s" -ForegroundColor Cyan }
function Loi($s)  { Write-Host "  [LOI] $s" -ForegroundColor Red }
function Dat($s)  { Write-Host "  [OK]  $s" -ForegroundColor Green }

function ChayTrenB([string]$Lenh) {
    # -EncodedCommand: base64 cua UTF-16LE. PowerShell coi ca chuoi la MOT script.
    # Truyen thang qua ssh la bon lop thoat ky tu, moi lop mot kieu quy tac.
    $bytes = [Text.Encoding]::Unicode.GetBytes($Lenh)
    $enc   = [Convert]::ToBase64String($bytes)
    & ssh -i $Key -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 `
        "$User@$MayB" "powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand $enc"
    if ($LASTEXITCODE -ne 0) { throw "lenh tren may B that bai (ma $LASTEXITCODE)" }
}

function HashCucBo([string]$Duong) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Duong).Hash.ToLower()
}

# --- 0. Kiem dieu kien truoc khi dung toi may B ---------------------------------
Buoc "0. Kiem tra tai cho"
if (-not (Test-Path -LiteralPath $Nguon)) { Loi "khong thay $Nguon"; exit 1 }
if (-not (Test-Path -LiteralPath $Key))   { Loi "khong thay khoa SSH $Key"; exit 1 }
Dat "nguon: $Nguon"

# Day ca .ps1 trong deploy\ vi may B can chung, NHUNG khong day chinh deploy.ps1
# (no chay tren may A, khong co viec gi o ben kia).
$TepCanDay = Get-ChildItem -LiteralPath $Nguon -Recurse -File |
    Where-Object {
        $_.FullName -notlike "*__pycache__*" -and
        $_.Name -ne "deploy.ps1" -and
        ($_.Extension -in ".py", ".json", ".md", ".ps1")
    }
if (-not $TepCanDay) { Loi "khong co tep nao de day"; exit 1 }
Dat ("$($TepCanDay.Count) tep se duoc day")

# --- 1. May B con song va dung o dung cho ---------------------------------------
Buoc "1. Kiem may B"
ChayTrenB @"
if (-not (Test-Path 'E:\AI\ComfyUI')) { Write-Error 'khong thay E:\AI\ComfyUI - sai may?'; exit 1 }
Write-Host ('  ComfyUI: co')
Write-Host ('  venv ComfyUI: ' + (Test-Path 'E:\AI\venv'))
"@

# --- 2. Tao cay thu muc rieng cho hang muc nay ----------------------------------
# !! TUYET DOI khong pip install gi vao E:\AI\venv: do la venv cua ComfyUI va cua
#    ca stack video 342 GB. Cong render dung venv RIENG.
Buoc "2. Tao thu muc tren may B"
ChayTrenB @"
foreach (`$t in @('$Dich', '$Dich\gateway', '$Dich\workflows', '$Dich\work', '$Dich\logs', '$Dich\bench', '$Dich\scripts')) {
    if (-not (Test-Path `$t)) { New-Item -ItemType Directory -Path `$t | Out-Null }
}
Write-Host '  cay thu muc: san sang'
"@

if ($ChiKiem) { Write-Host ""; Write-Host "Che do --ChiKiem: bo qua buoc chep." }

# --- 3. Chep tep ----------------------------------------------------------------
if (-not $ChiKiem) {
    Buoc "3. Chep tep sang may B"
    foreach ($t in $TepCanDay) {
        $tuong  = $t.FullName.Substring($Nguon.Length).TrimStart('\')
        $dichTep = Join-Path "$Dich\gateway" $tuong
        $dichThu = Split-Path -Parent $dichTep
        ChayTrenB "if (-not (Test-Path '$dichThu')) { New-Item -ItemType Directory -Path '$dichThu' -Force | Out-Null }"

        # !! DUONG DICH CUA SCP PHAI DUNG GACH CHEO XUOI.
        #    Shell mac dinh cua OpenSSH tren may B la cmd.exe va no dien giai dau
        #    gach nguoc trong duong dan tu xa.
        #    SU CO THAT 21/08/2026: chep den
        #        E:\AI\ltt_render\scripts\tai_model.py
        #    thi scp tra ve 0 (BAO THANH CONG) nhung KHONG CO TEP NAO duoc tao, va
        #    cung khong co tep lac o dau ca - no bien mat im lang. Thu pham la
        #    chuoi "\t" trong "\tai_model.py". Cung lenh do voi "gpu_check.py" chay
        #    tot, nen loi nay AN THEO TEN TEP: no chi hien ra voi nhung ten bat dau
        #    bang t, n, b, r...
        #    Windows chap nhan gach cheo xuoi, va scp khong dung no lam ky tu thoat.
        $dichScp = $dichTep -replace '\\', '/'
        & scp -i $Key -o StrictHostKeyChecking=accept-new -q `
            $t.FullName "${User}@${MayB}:$dichScp"
        if ($LASTEXITCODE -ne 0) { Loi "chep that bai: $tuong"; exit 1 }
    }
    Dat "da chep $($TepCanDay.Count) tep"
    # Buoc 4 (so hash) la luoi bat moi tep bi nuot am tham nhu su co tren:
    # scp bao thanh cong khong co nghia la tep da toi noi.
}

# --- 4. So hash hai ben ---------------------------------------------------------
# Muc dich khong phai bat loi duong truyen, ma bat viec SUA TAY TREN MAY B.
# Do la loi kinh dien cua du an nay: sua o may chay, quen sua o repo, lan deploy
# sau mat trang va mat am tham.
Buoc "4. So hash hai ben"
$mongDoi = @{}
foreach ($t in $TepCanDay) {
    $tuong = $t.FullName.Substring($Nguon.Length).TrimStart('\').Replace('\', '/')
    $mongDoi[$tuong] = HashCucBo $t.FullName
}
$json = ($mongDoi.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n"
$tam  = Join-Path $env:TEMP "ltt_render_hash.txt"
[IO.File]::WriteAllText($tam, $json, (New-Object Text.UTF8Encoding($false)))
$dichHash = ("$Dich\scripts\hash_mong_doi.txt") -replace '\\', '/'
& scp -i $Key -o StrictHostKeyChecking=accept-new -q $tam "${User}@${MayB}:$dichHash"

ChayTrenB @"
`$goc = '$Dich\gateway'
`$lech = @()
foreach (`$dong in [IO.File]::ReadAllLines('$Dich\scripts\hash_mong_doi.txt')) {
    if (-not `$dong) { continue }
    `$p = `$dong.Split('=', 2)
    `$tep = Join-Path `$goc (`$p[0] -replace '/', '\')
    if (-not (Test-Path -LiteralPath `$tep)) { `$lech += ('THIEU  ' + `$p[0]); continue }
    `$h = (Get-FileHash -Algorithm SHA256 -LiteralPath `$tep).Hash.ToLower()
    if (`$h -ne `$p[1]) { `$lech += ('KHAC   ' + `$p[0]) }
}
if (`$lech.Count -gt 0) {
    Write-Host '  [LOI] Lech so voi repo:' -ForegroundColor Red
    `$lech | ForEach-Object { Write-Host ('    ' + `$_) }
    exit 1
}
Write-Host '  [OK]  moi tep khop hash voi repo'
"@
Dat "hash khop - khong co tep nao bi sua tay tren may B"

# --- 5. venv rieng cho cong render ----------------------------------------------
Buoc "5. venv rieng (KHONG dung venv cua ComfyUI)"
ChayTrenB @"
`$venv = '$Dich\venv'
if (-not (Test-Path (`$venv + '\Scripts\python.exe'))) {
    Write-Host '  dang tao venv...'
    & py -3 -m venv `$venv
}
& (`$venv + '\Scripts\python.exe') -m pip install --disable-pip-version-check -q --upgrade pip
& (`$venv + '\Scripts\python.exe') -m pip install --disable-pip-version-check -q fastapi uvicorn httpx
& (`$venv + '\Scripts\python.exe') -c "import fastapi, uvicorn, httpx; print('  [OK]  fastapi', fastapi.__version__)"
"@

# --- 6. Token bearer: SINH TREN MAY B, khong sinh o day --------------------------
# Sinh tai cho roi truyen sang se de lai dau vet trong log/lich su lenh cua may A.
# Sinh tren B thi no chi di mot chieu, qua SSH, khi may A chu dong doc.
Buoc "6. Token bearer"
ChayTrenB @"
`$thu = 'C:\ProgramData\LTTRender'
if (-not (Test-Path `$thu)) { New-Item -ItemType Directory -Path `$thu | Out-Null }
`$tep = `$thu + '\gateway.env'
if (-not (Test-Path `$tep)) {
    `$b = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes(`$b)
    `$tok = [Convert]::ToBase64String(`$b).TrimEnd('=').Replace('+','-').Replace('/','_')
    `$noi = @(
        'LTT_RENDER_TOKEN=' + `$tok,
        'LTT_RENDER_HOST=127.0.0.1',
        'LTT_RENDER_PORT=8199',
        'LTT_COMFY_URL=http://127.0.0.1:8188',
        'LTT_COMFY_INPUT_DIR=E:\AI\ComfyUI\input',
        'LTT_RENDER_WORK_DIR=$Dich\work',
        'LTT_RENDER_JOB_TIMEOUT_S=900',
        'LTT_RENDER_RAM_TRONG_GB=48'
    ) -join "``r``n"
    # UTF-8 KHONG BOM - quy tac 1.
    #
    # !! NOI BANG "``r``n" TUONG MINH, KHONG dung [Environment]::NewLine.
    #    Do that 22/08: ban dung [Environment]::NewLine ghi ra CA TEP THANH MOT DONG
    #    (token 43 ky tu bien thanh mot dong 281 ky tu chua het moi bien). Dich vu
    #    doc tep do se lay sai bien moi truong, va no hong IM LANG - service van
    #    khoi dong, chi la khong co token va khong biet ComfyUI o dau.
    [IO.File]::WriteAllText(`$tep, `$noi, (New-Object Text.UTF8Encoding(`$false)))
    Write-Host '  [OK]  da sinh token moi'
} else {
    Write-Host '  [OK]  gateway.env da co - giu nguyen token cu'
}
"@

Buoc "XONG phan tu dong duoc"
Write-Host ""
Write-Host "Hai viec con lai CAN QUYEN ADMINISTRATOR TREN MAY B:" -ForegroundColor Yellow
Write-Host "  1. Cai hai dich vu NSSM (LTTComfyUI, LTTRenderGateway)"
Write-Host "  2. Mo tuong lua TCP 8199 CHI cho 192.168.2.17"
Write-Host ""
Write-Host "Mo PowerShell (Administrator) TREN MAY B roi chay:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File $Dich\gateway\deploy\cai_dat_dich_vu.ps1"
Write-Host ""
Write-Host "Sau do kiem lai bang:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File $Dich\gateway\deploy\kiem_tra.ps1"
