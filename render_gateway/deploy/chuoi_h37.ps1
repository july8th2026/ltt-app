# chuoi_h37.ps1 - chay NHIEU luot do dac noi tiep nhau, de GPU khong nam khong
# giua cac buoc.
#
#   powershell -ExecutionPolicy Bypass -File E:\AI\ltt_render\gateway\render_gateway\deploy\chuoi_h37.ps1
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! DUNG LAI BANG:
#      powershell -ExecutionPolicy Bypass -File ...\dung_het.ps1
#    dung_het.ps1 giet VO NAY TRUOC roi moi giet luot dang chay - neu nguoc lai thi
#    vo se phong ngay luot ke tiep va "dung het" hoa ra chi la "chuyen viec".
#
# !! NO CHO HANG DOI TRONG TRUOC KHI BAT DAU. Du an video dung chung ComfyUI tren
#    may nay; chen vao giua luot cua ho la lam hong phep do CUA HO, khong phai cua ta.

[CmdletBinding()]
param(
    [string]$Py    = "E:\AI\ltt_render\venv\Scripts\python.exe",
    [string]$Goc   = "E:\AI\ltt_render\gateway\render_gateway\deploy\chay_baseline.py",
    [string]$Bench = "E:\AI\ltt_render\bench",
    [string]$Comfy = "http://127.0.0.1:8188",
    [int]$ChoToiDaPhut = 240,
    [switch]$KeCa
)

$ErrorActionPreference = "Continue"

# !! TU GHI LOG, KHONG NHO VO CHUYEN HUONG.
#    Chuoi nay duoc phong bang Win32_Process.Create de song sot khi phien SSH dong.
#    CreateProcess KHONG co shell, nen '*> tep.log' tren dong lenh chi la mot tham so
#    van ban - khong ai chuyen huong gi ca. Da dinh that 22/08: vo chay tot, log
#    khong bao gio xuat hien, va toi tuong chuoi da chet.
$LogChuoi = "E:\AI\ltt_render\logs\chuoi_h37.log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogChuoi) | Out-Null
try { Start-Transcript -Path $LogChuoi -Append -Force | Out-Null } catch { }

function Ghi($s) { Write-Host ("[{0:HH:mm:ss}] {1}" -f (Get-Date), $s) }

# Moi luot: nhan | tep prompt | cac tham so them.
$luot = @(
    @{ ca = "G5_edit";      pr = "G5_edit.json";        them = @("--mode", "edit") },
    @{ ca = "G5_structure"; pr = "G5_structure.json";   them = @("--mode", "edit") },
    @{ ca = "G5_subject";   pr = "G5_subject.json";     them = @("--mode", "subject") },
    @{ ca = "G4_full_s30_seed2"; pr = "prompts_30_seed2.json"; them = @("--steps", "30") },
    @{ ca = "G4_full_s90_seed2"; pr = "prompts_30_seed2.json"; them = @("--steps", "90") }
)

if ($KeCa) {
    Ghi "chi liet ke, khong chay:"
    foreach ($l in $luot) { "  {0,-22} {1,-26} {2}" -f $l.ca, $l.pr, ($l.them -join " ") }
    exit 0
}

# --- Cho luot truoc xong han ------------------------------------------------------
# !! HAI dieu kien, khong phai mot. Hang doi RONG khong co nghia la xong: giua hai
#    anh, chay_baseline tai anh ve roi moi xep hang anh sau, nen co mot khe vai giay
#    ma queue_remaining = 0. Lay mot mau trung vao khe do la chuoi chen vao chay
#    SONG SONG voi lo cu - vua doi nguy co OOM, vua lam hong ca hai phep do thoi gian.
function DangChay {
    $q = 0
    try { $q = (Invoke-RestMethod "$Comfy/prompt" -TimeoutSec 15).exec_info.queue_remaining }
    catch { return $null }
    $ps = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*chay_baseline*" })
    return ($q -gt 0) -or ($ps.Count -gt 0)
}

Ghi "cho luot truoc xong (hang doi trong VA khong con chay_baseline; toi da $ChoToiDaPhut phut)..."
$het = (Get-Date).AddMinutes($ChoToiDaPhut)
while ((Get-Date) -lt $het) {
    $c = DangChay
    if ($c -eq $null) { Ghi "ComfyUI khong tra loi - dung chuoi"; exit 2 }
    if (-not $c) { break }
    Start-Sleep -Seconds 30
}
if ((Get-Date) -ge $het) { Ghi "hang doi van ban sau $ChoToiDaPhut phut - dung chuoi"; exit 3 }
Ghi "hang doi trong, bat dau"

# --- Chay tung luot ----------------------------------------------------------------
foreach ($l in $luot) {
    $tep = Join-Path $Bench $l.pr
    if (-not (Test-Path $tep)) { Ghi ("BO QUA {0}: khong co {1}" -f $l.ca, $tep); continue }
    Ghi ("=== bat dau {0} ({1})" -f $l.ca, $l.pr)
    $args = @($Goc, "--ca", $l.ca, "--prompts", $tep, "--comfy", $Comfy) + $l.them
    & $Py @args 2>&1 | ForEach-Object { "    $_" }
    Ghi ("=== xong {0}, ma thoat {1}" -f $l.ca, $LASTEXITCODE)
}

Ghi "CHUOI DA XONG"
try { Stop-Transcript | Out-Null } catch { }
