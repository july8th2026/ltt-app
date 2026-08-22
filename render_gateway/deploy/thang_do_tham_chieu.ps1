# thang_do_tham_chieu.ps1 - do VRAM cho che do EDIT/SUBJECT theo TUNG BAC. (H37/G5)
#
#   powershell -ExecutionPolicy Bypass -File ...\thang_do_tham_chieu.ps1
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! VI SAO CO TEP NAY - D-024: may B SAP 22/08. Cau hinh dang chay chiem 97,5% VRAM,
#    va luot ke tiep trong hang doi la `subject` voi HAI anh tham chieu 4 MP - can
#    11.412 token so voi 3.600 cua khung thuong, tuc gap 2,8 lan MOI THU tung do.
#    No nam trong mot chuoi TU DONG, KHONG NGUOI CANH.
#
# !! BA DIEU TEP NAY LAM KHAC HAN:
#    1. CHAY O TIEN CANH. Khong Win32_Process.Create, khong tach khoi phien. Ban
#       nhin thay tung buoc. Ctrl+C la dung that.
#    2. TANG DAN va DUNG NGAY khi VRAM vuot nguong an toan - khong chay tiep "de
#       xem sao".
#    3. Moi bac phai GO TRAN RA TREN DONG LENH (--tran-token). Chot ngan_sach.py
#       tu choi mac dinh; nang no la mot hanh dong co chu y, khong phai mac dinh.
#
# !! DIEU KIEN TIEN QUYET: ComfyUI phai dang chay VOI `--reserve-vram 3`.
#    Script kiem dieu do truoc, va TU CHOI chay neu VRAM dang dung da qua cao.

[CmdletBinding()]
param(
    [string]$Py    = "E:\AI\ltt_render\venv\Scripts\python.exe",
    [string]$Goc   = "E:\AI\ltt_render\gateway\render_gateway\deploy\chay_baseline.py",
    [string]$Bench = "E:\AI\ltt_render\bench",
    [string]$Comfy = "http://127.0.0.1:8188",
    # Vuot nguong nay la DUNG THANG. 21 GB tren card 24,6 GB = con ~3,6 GB cho he
    # dieu hanh va du an video. Con so nay den tu D-024, khong phai uoc chung.
    [int]$VramDungMb = 21000
)

$ErrorActionPreference = "Continue"
function Ghi($s) { Write-Host ("[{0:HH:mm:ss}] {1}" -f (Get-Date), $s) -ForegroundColor Cyan }

function VramMb {
    $r = & nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>$null
    if (-not $r) { return -1 }
    return [int]($r | Select-Object -First 1).Trim()
}

function SoPythonTrenGpu {
    # !! DEM TIEN TRINH, KHONG DOC NGUONG VRAM (D-022). ComfyUI GIU MODEL THUONG TRU
    #    giua cac lo, nen VRAM cao KHONG phan biet duoc "cache cua chinh no" voi
    #    "co ke khac dang chiem card". Ban dau cua script nay dung nguong VRAM va da
    #    BAT OAN ngay lan chay dau: 16.269 MB, toan bo la cache cua ComfyUI.
    $r = & nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader 2>$null
    if (-not $r) { return -1 }
    return @($r | Where-Object { $_ -match "python" }).Count
}

# --- 0a. KHONG CHAY HAI BAN CUNG LUC ------------------------------------------------
# !! SU CO THAT 22/08: loi goi `exec` cua Nexus het gio o PHIA GOI, nhung tien trinh
#    tu xa VAN CHAY TIEP. Moi lan thu lai la them mot ban thang do nua. Da co luc BA
#    ban chay cung luc, hang doi 2 job, VRAM 19,9 GB - va moi so do deu vo nghia vi
#    chung do lan nhau. Chot nay khien lan sau khong lam duoc dieu do nua.
$toi = $PID
$khac = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
          Where-Object { $_.CommandLine -like "*thang_do_tham_chieu*" -and $_.ProcessId -ne $toi })
if ($khac.Count -gt 0) {
    Write-Host "DUNG: da co $($khac.Count) ban thang do dang chay (PID $($khac.ProcessId -join ', '))." -ForegroundColor Red
    Write-Host "Hai ban do cung luc thi moi so do deu vo nghia. Dung ban kia truoc." -ForegroundColor Red
    exit 5
}
$cb = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*chay_baseline*" })
if ($cb.Count -gt 0) {
    Write-Host "DUNG: dang co $($cb.Count) tien trinh chay_baseline. Cho no xong da." -ForegroundColor Red
    exit 5
}

# --- 0. Kiem dieu kien truoc khi cham GPU -------------------------------------------
Ghi "kiem truoc khi bat dau"
$truoc = VramMb
$soPy = SoPythonTrenGpu
"  VRAM dang dung: $truoc MB | tien trinh python tren GPU: $soPy"
if ($truoc -lt 0) { Write-Host "  KHONG doc duoc nvidia-smi - dung" -ForegroundColor Red; exit 2 }
if ($soPy -ge 2) {
    Write-Host "  DUNG: co $($soPy - 1) tien trinh khac dang tinh tren GPU." -ForegroundColor Red
    Write-Host "  Cho card ranh roi chay lai." -ForegroundColor Red
    exit 3
}

# Bao ComfyUI nha cache truoc khi do, de con so BAC DAU TIEN la con so sach.
Ghi "bao ComfyUI nha model de lay moc sach"
try {
    Invoke-RestMethod "$Comfy/free" -Method Post -TimeoutSec 30 -ContentType "application/json" `
        -Body (@{ unload_models = $true; free_memory = $true } | ConvertTo-Json -Compress) | Out-Null
    Start-Sleep -Seconds 5
    "  VRAM sau khi nha: {0} MB" -f (VramMb)
} catch { Write-Host "  khong goi duoc /free - van chay tiep, moc dau se cao hon that" -ForegroundColor DarkYellow }

# --- Cac bac. Moi bac: nhan | so anh | MP moi anh | tran token can go ra ------------
# Token = (2560/32)*(1440/32) + so_anh * MP*1e6/1024  =  3600 + ...
# !! DUNG BO PROMPT TIENG ANH. Bo tieng Viet se sinh ra anh KHONG LIEN QUAN den
#    prompt (D-027), va do VRAM tren nhung anh vo nghia thi con so do vo dung.
$bac = @(
    @{ ten = "G5a_edit_1anh_0p4mp"; pr = "G5_edit_en.json";    mode = "edit";    ref = 0.4; tran = 4100 },
    @{ ten = "G5b_edit_1anh_1mp";   pr = "G5_edit_en.json";    mode = "edit";    ref = 1.0; tran = 4700 },
    @{ ten = "G5c_edit_1anh_2mp";   pr = "G5_edit_en.json";    mode = "edit";    ref = 2.0; tran = 5600 },
    @{ ten = "G5d_edit_1anh_4mp";   pr = "G5_edit_en.json";    mode = "edit";    ref = 4.0; tran = 7600 },
    @{ ten = "G5e_subj_2anh_1mp";   pr = "G5_hai_ref_en.json"; mode = "subject"; ref = 1.0; tran = 5700 },
    @{ ten = "G5f_subj_2anh_2mp";   pr = "G5_hai_ref_en.json"; mode = "subject"; ref = 2.0; tran = 7600 }
)

foreach ($b in $bac) {
    Ghi ("=== BAC {0}: {1} anh @ {2} MP (tran {3} token)" -f $b.ten, $(if ($b.mode -eq "subject") {2} else {1}), $b.ref, $b.tran)

    # Chi chay MOT prompt moi bac. Muc tieu la do VRAM, khong phai sinh bo anh.
    $args = @($Goc, "--ca", $b.ten, "--prompts", (Join-Path $Bench $b.pr),
              "--comfy", $Comfy, "--mode", $b.mode, "--ref-mp", $b.ref,
              "--tran-token", $b.tran, "--so-prompt", "1", "--steps", "30")
    & $Py @args 2>&1 | ForEach-Object { "    $_" }

    $sau = VramMb
    "  VRAM sau bac nay: $sau MB (nguong dung: $VramDungMb MB)"
    if ($sau -ge $VramDungMb) {
        Write-Host ""
        Write-Host "  DUNG THANG TAI DAY." -ForegroundColor Yellow
        Write-Host "  Bac '$($b.ten)' day VRAM len $sau MB, cham nguong $VramDungMb MB." -ForegroundColor Yellow
        Write-Host "  Cau hinh cao nhat DUNG DUOC la bac ngay TRUOC bac nay." -ForegroundColor Yellow
        Write-Host "  Ghi so nay vao DECISIONS.md roi moi nang TOKEN_DA_DO_TOI_DA." -ForegroundColor Yellow
        exit 0
    }
}

Ghi "DA CHAY HET THANG ma khong bac nao cham nguong"
Write-Host "Ghi so do cua tung bac vao DECISIONS.md truoc khi nang tran." -ForegroundColor Green
