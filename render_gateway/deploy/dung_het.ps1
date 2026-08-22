# dung_het.ps1 - CONG TAT KHAN CAP cho moi viec cua H37 tren MAY B.
#
#   powershell -ExecutionPolicy Bypass -File E:\AI\ltt_render\gateway\render_gateway\deploy\dung_het.ps1
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! VI SAO CO TEP NAY - SU CO THAT 21/08/2026:
#    Cac viec do dac cua H37 duoc phong bang Win32_Process.Create de chung SONG SOT
#    khi phien SSH dong. Dieu do dung ve ky thuat, nhung no tao ra mot hau qua khong
#    ai luong: khi chu du an NGAT mot lenh dang chay, tien trinh tren may B VAN CHAY
#    TIEP va van an GPU. Chu du an nhin thay "card dang chay job" ma khong co cach
#    nao dung no lai.
#
# !! NGUYEN TAC: tep nay CHI dung viec cua H37. No KHONG:
#    - dung ComfyUI (du an video dung chung),
#    - huy prompt nao khong phai cua H37,
#    - dung tien trinh nao khong phai cua H37.
#    Mot cong tat khan cap ma giet nham viec cua nguoi khac thi te hon khong co.

[CmdletBinding()]
param(
    [string]$Comfy = "http://127.0.0.1:8188",
    [switch]$KeCa                          # chi liet ke, khong dung gi
)

$ErrorActionPreference = "Continue"

function Buoc($s) { Write-Host ""; Write-Host "== $s" -ForegroundColor Cyan }
function Dat($s)  { Write-Host "  [OK]  $s" -ForegroundColor Green }

# --- 0. Vo CHUOI viec (neu co) ----------------------------------------------------
# !! PHAI GIET VO TRUOC TIEN TRINH CON. `chuoi_h37.ps1` chay nhieu luot noi tiep
#    nhau: giet luot dang chay ma de vo song thi vo se phong ngay luot ke tiep, va
#    cong tat "dung het" hoa ra chi la "chuyen sang viec sau".
Buoc "0. Vo chuoi viec (chuoi_h37)"
$vo = Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue |
      Where-Object { $_.CommandLine -like "*chuoi_h37*" }
if (-not $vo) { Dat "khong co vo chuoi nao dang chay" }
foreach ($v in $vo) {
    if ($KeCa) { Write-Host ("  [KE]  vo PID {0}" -f $v.ProcessId) }
    else {
        try { Stop-Process -Id $v.ProcessId -Force -ErrorAction Stop
              Dat ("da dung vo chuoi PID {0}" -f $v.ProcessId) }
        catch { Write-Host ("  [X]   khong dung duoc vo PID {0}" -f $v.ProcessId) -ForegroundColor Red }
    }
}

# --- 1. Tien trinh do dac cua H37 ------------------------------------------------
Buoc "1. Tien trinh cua H37"
$ten = @("chay_baseline", "tai_model", "gpu_check", "render_gateway.main")
$ps = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
      Where-Object { $c = $_.CommandLine; $ten | Where-Object { $c -like "*$_*" } }
if (-not $ps) { Dat "khong co tien trinh nao cua H37" }
foreach ($p in $ps) {
    $nhan = ($ten | Where-Object { $p.CommandLine -like "*$_*" }) -join ","
    if ($KeCa) { Write-Host ("  [KE]  PID {0}  {1}" -f $p.ProcessId, $nhan) }
    else {
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
              Dat ("da dung PID {0} ({1})" -f $p.ProcessId, $nhan) }
        catch { Write-Host ("  [X]   khong dung duoc PID {0}" -f $p.ProcessId) -ForegroundColor Red }
    }
}

# --- 2. Prompt cua H37 trong hang doi ComfyUI ------------------------------------
# Nhan dien theo `filename_prefix` bat dau bang 'ltt_h37/'. KHONG dung theo vi tri
# trong hang doi va KHONG xoa ca hang doi: viec video co the dang xep hang o do.
Buoc "2. Prompt cua H37 trong hang doi ComfyUI"
try {
    $q = Invoke-RestMethod "$Comfy/queue" -TimeoutSec 15
} catch {
    Write-Host "  ComfyUI khong tra loi - bo qua buoc nay" -ForegroundColor DarkYellow
    $q = $null
}

function LaCuaH37($muc) {
    # muc = [number, prompt_id, prompt, extra_data, outputs]
    $wf = $muc[2]
    if (-not $wf) { return $false }
    foreach ($n in $wf.PSObject.Properties) {
        $i = $n.Value.inputs
        if ($i -and $i.filename_prefix -and ("$($i.filename_prefix)" -like "ltt_h37/*")) { return $true }
    }
    return $false
}

if ($q) {
    $cua_ta_chay = @($q.queue_running | Where-Object { LaCuaH37 $_ })
    $cua_ta_cho  = @($q.queue_pending | Where-Object { LaCuaH37 $_ })
    $khac = @($q.queue_running).Count + @($q.queue_pending).Count - $cua_ta_chay.Count - $cua_ta_cho.Count
    Write-Host ("  cua H37: {0} dang chay, {1} dang cho | KHONG phai cua H37: {2} (giu nguyen)" -f `
        $cua_ta_chay.Count, $cua_ta_cho.Count, $khac)

    foreach ($m in ($cua_ta_chay + $cua_ta_cho)) {
        $pid_ = $m[1]
        if ($KeCa) { Write-Host "  [KE]  $pid_" ; continue }
        try {
            Invoke-RestMethod "$Comfy/interrupt" -Method Post -TimeoutSec 10 `
                -ContentType "application/json" -Body (@{ prompt_id = $pid_ } | ConvertTo-Json -Compress) | Out-Null
            Dat "da huy $pid_"
        } catch { Write-Host "  [X]   khong huy duoc $pid_" -ForegroundColor Red }
    }
    if ($khac -gt 0) {
        Write-Host "  LUU Y: van con $khac prompt KHONG phai cua H37 - co the la viec video, khong dung." -ForegroundColor Yellow
    }
}

# --- 3. Trang thai sau khi dung ---------------------------------------------------
Buoc "3. Trang thai"
Start-Sleep -Seconds 3
try {
    $r = (Invoke-RestMethod "$Comfy/prompt" -TimeoutSec 10).exec_info.queue_remaining
    Write-Host "  queue_remaining = $r"
} catch { Write-Host "  ComfyUI khong tra loi" }
& nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu --format=csv,noheader
Write-Host ""
Write-Host "ComfyUI KHONG bi dung - no dung chung voi du an video." -ForegroundColor Yellow
