# thu_unload.ps1 - CHAY TREN MAY B. Thuan ASCII (quy tac 16 CLAUDE.md).
#
# Tra loi cau [INFERRED] cua L-17: `GET /unload` nha MOT model hay nha HET?
#
# !! KHONG cham dich vu song: llama-swap thu nghe cong 8390 (song: 8280), hai ho
#    so gia nam tren 5060 Ti va CPU, khong cham 3090.
#
# Bon buoc, moi buoc doc `/running` de co BANG CHUNG chu khong doc ma tra ve:
#   1. nap ca hai
#   2. POST /api/models/unload/thu_cpu   -> con lai gi?
#   3. nap lai ca hai
#   4. GET /unload                       -> con lai gi?

$ErrorActionPreference = 'Continue'

$Cfg  = 'E:\AI\ltt_dual\thu_unload.yaml'
$Exe  = 'H:\LTT_LLM\bin\llamaswap\llama-swap.exe'
$Port = 8390
$Goc  = "http://127.0.0.1:$Port"
$Log  = 'E:\AI\ltt_dual\thu_unload.log'

function Ghi([string]$d) {
    $t = (Get-Date).ToString('HH:mm:ss')
    $dong = "$t  $d"
    Write-Output $dong
    Add-Content -Path $Log -Value $dong -Encoding ASCII
}

function Dang_Chay() {
    try {
        $r = Invoke-RestMethod -Uri "$Goc/running" -TimeoutSec 10
        # llama-swap tra {"running":[{"model":"..."},...]} - lay ten cho chac.
        $ten = @()
        foreach ($m in $r.running) {
            if ($m.model) { $ten += $m.model } elseif ($m.id) { $ten += $m.id } else { $ten += "$m" }
        }
        return ($ten -join ',')
    } catch { return "LOI: $($_.Exception.Message)" }
}

function Nap([string]$model) {
    # Mot luot that la cach chac chan nhat de bat llama-swap nap ho so.
    $than = @{ model = $model; messages = @(@{ role = 'user'; content = 'hi' }); max_tokens = 1 } | ConvertTo-Json -Depth 5
    try {
        Invoke-RestMethod -Uri "$Goc/v1/chat/completions" -Method Post -Body $than `
            -ContentType 'application/json' -TimeoutSec 300 | Out-Null
        return $true
    } catch { Ghi "    nap $model LOI: $($_.Exception.Message)"; return $false }
}

Remove-Item -Path $Log -Force -ErrorAction SilentlyContinue
Ghi "=== THU /unload - hai ho so gia, cong $Port (KHONG cham 8280) ==="

# Dung ban thu cu neu con.
Get-Process llama-swap -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*$Cfg*" } |
    ForEach-Object { Stop-Process -Id $_.Id -Force }

$p = Start-Process -FilePath $Exe -ArgumentList @('--config', $Cfg, '--listen', "127.0.0.1:$Port") `
        -PassThru -NoNewWindow -RedirectStandardOutput 'E:\AI\ltt_dual\thu_unload.out.log' `
        -RedirectStandardError 'E:\AI\ltt_dual\thu_unload.err.log'
Start-Sleep -Seconds 3
if ($p.HasExited) {
    Ghi "TRUOT: llama-swap thoat ngay. err:"
    Get-Content 'E:\AI\ltt_dual\thu_unload.err.log' -Tail 10 | ForEach-Object { Ghi "    $_" }
    exit 1
}
Ghi "llama-swap thu da chay, pid $($p.Id)"

Ghi "BUOC 1 - nap ca hai"
$null = Nap 'thu_gpu'
$null = Nap 'thu_cpu'
Ghi "  /running = [$(Dang_Chay)]"

Ghi "BUOC 2 - POST /api/models/unload/thu_cpu (duong THEO TEN MODEL)"
try {
    Invoke-RestMethod -Uri "$Goc/api/models/unload/thu_cpu" -Method Post -TimeoutSec 60 | Out-Null
    Ghi "  goi OK"
} catch { Ghi "  goi LOI: $($_.Exception.Message)" }
Start-Sleep -Seconds 3
Ghi "  /running = [$(Dang_Chay)]     <= mong doi: chi con thu_gpu"

Ghi "BUOC 3 - nap lai ca hai"
$null = Nap 'thu_gpu'
$null = Nap 'thu_cpu'
Ghi "  /running = [$(Dang_Chay)]"

Ghi "BUOC 4 - GET /unload (duong KHONG THAM SO, thu ma production dang dung)"
try {
    Invoke-RestMethod -Uri "$Goc/unload" -Method Get -TimeoutSec 60 | Out-Null
    Ghi "  goi OK"
} catch { Ghi "  goi LOI: $($_.Exception.Message)" }
Start-Sleep -Seconds 3
Ghi "  /running = [$(Dang_Chay)]     <= CAU HOI: rong (nha het) hay con mot?"

Ghi "BUOC 5 - POST /api/models/unload (khong ten) de doi chieu"
$null = Nap 'thu_gpu'
$null = Nap 'thu_cpu'
Ghi "  /running truoc = [$(Dang_Chay)]"
try {
    Invoke-RestMethod -Uri "$Goc/api/models/unload" -Method Post -TimeoutSec 60 | Out-Null
    Ghi "  goi OK"
} catch { Ghi "  goi LOI: $($_.Exception.Message)" }
Start-Sleep -Seconds 3
Ghi "  /running = [$(Dang_Chay)]"

Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Ghi "=== XONG, da dung ban thu ==="
