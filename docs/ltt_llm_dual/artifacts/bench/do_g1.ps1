# do_g1.ps1 - cong do G1: `qwen38-api` cau hinh DAY DU co vua RTX 3090 khong.
#
# Cau hoi G1 (Task 3.2): -c 262144 -np 4 -kvu + mmproj + draft-mtp + KV q4_0
# co NAP duoc tren card 24 GB khong, va con lai bao nhieu bien.
#
# Chay tren cong THU 8290, KHONG dung toi llama-swap (8280) va khong dung toi
# dich vu nao. llama-swap phai dang rong (`/running` = []) truoc khi goi.
#
# Khong chay thang qua ssh: phien ssh dut thi llama-server bi giet giua chung.
# Dang ky Scheduled Task roi `schtasks /run`.

param(
    [int]$Ctx      = 262144,
    [int]$Np       = 4,
    [string]$Nhan  = 'g1_262144_np4',
    [switch]$KhongMmproj
)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Gguf   = 'H:\LTT_LLM\models\Qwen3.8-27B-UD-Q4_K_M.gguf'
$Mmproj = 'H:\LTT_LLM\models\mmproj-F16.gguf'
$Tmpl   = 'H:/LTT_LLM/models/chat_template.jinja'
$Uuid38 = 'GPU-26623278-4fa5-82db-4306-237651b03e78'
$Port   = 8290
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\$Nhan.log"
$LogSrv = "$Thu\$Nhan.server.log"
$Ket    = "$Thu\$Nhan.json"

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

# VRAM cua RIENG card 3090, doc theo UUID chu khong theo chi so: thu tu liet ke
# CUDA doi duoc khi lap them card, UUID thi khong.
function Vram38 {
    $d = & nvidia-smi --query-gpu=uuid,memory.used,memory.total --format=csv,noheader,nounits
    foreach ($dong in $d) {
        $c = $dong -split ',\s*'
        if ($c[0] -eq $Uuid38) { return [int]$c[1] }
    }
    return -1
}

# WDDM "Shared Usage" = trong so da TRAN sang RAM chu qua PCIe. `nvidia-smi`
# KHONG thay thu nay, va llama.cpp khong bao loi khi no xay ra - chi cham di
# mot phan tu (do 22/08: 63,3 -> 18,2 tok/s). Nen phai doc rieng.
function ChiaSeMiB([int]$pid_) {
    try {
        $m = Get-Counter "\GPU Process Memory(pid_$pid_*)\Shared Usage" -ErrorAction Stop
        $t = ($m.CounterSamples | Measure-Object -Property CookedValue -Sum).Sum
        return [math]::Round($t / 1MB, 1)
    } catch { return -1 }
}

New-Item -ItemType Directory -Force -Path $Thu | Out-Null
Remove-Item -Path $Log, $LogSrv, $Ket -Force -ErrorAction SilentlyContinue

Ghi "=== G1 === ctx=$Ctx np=$Np mmproj=$(-not $KhongMmproj) cong=$Port"

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object {
        Ghi "DON     giet llama-server con sot pid $($_.Id)"
        Stop-Process -Id $_.Id -Force
    }
Start-Sleep -Seconds 3

$truoc = Vram38
Ghi "TRUOC   VRAM 3090 = $truoc MiB"

$args_ = @(
    '-m', $Gguf,
    '--jinja', '--chat-template-file', $Tmpl,
    '--reasoning-format', 'deepseek',
    '-fa', '1', '-ngl', '999',
    '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
    '--metrics',
    '-c', "$Ctx", '-np', "$Np", '-kvu',
    '--cache-type-k', 'q4_0', '--cache-type-v', 'q4_0',
    '--host', '127.0.0.1', '--port', "$Port"
)
if (-not $KhongMmproj) { $args_ += @('--mmproj', $Mmproj) }

$env:CUDA_VISIBLE_DEVICES = $Uuid38
Ghi "CHAY    $Bin $($args_ -join ' ')"
$t0 = Get-Date
$p = Start-Process -FilePath $Bin -ArgumentList $args_ -PassThru -NoNewWindow `
        -RedirectStandardOutput $LogSrv -RedirectStandardError "$LogSrv.err"
Ghi "PID     $($p.Id)"

$xanh = $false
for ($i = 0; $i -lt 600; $i++) {
    Start-Sleep -Seconds 1
    if ($p.HasExited) { Ghi "CHET    llama-server thoat ma $($p.ExitCode) sau $i s"; break }
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
        if ($h.status -eq 'ok') { $xanh = $true; break }
    } catch { }
}
$giay_nap = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)

$kq = [ordered]@{
    nhan = $Nhan; ctx = $Ctx; np = $Np; mmproj = (-not $KhongMmproj)
    nap_duoc = $xanh; giay_nap = $giay_nap
    vram_truoc_mib = $truoc
}

if (-not $xanh) {
    Ghi "TRUOT   khong nap duoc sau $giay_nap s"
    $kq.ly_do = 'khong nap duoc'
    if (Test-Path "$LogSrv.err") { $kq.duoi_log = (Get-Content "$LogSrv.err" -Tail 25) -join "`n" }
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
} else {
    Ghi "XANH    nap $giay_nap s"
    $sau = Vram38
    $chia = ChiaSeMiB $p.Id
    Ghi "SAUNAP  VRAM 3090 = $sau MiB | Shared Usage = $chia MiB"
    $kq.vram_sau_nap_mib = $sau
    $kq.shared_usage_mib = $chia
    $kq.bien_mib = 24576 - $sau

    # Mot luot that de chac chan no TRA LOI duoc, khong chi /health xanh.
    try {
        $body = @{ model = 'x'; messages = @(@{ role = 'user'; content = 'Noi dung ngan: 2+2=?' })
                   max_tokens = 32; stream = $false } | ConvertTo-Json -Depth 5
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/v1/chat/completions" `
                -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 180
        $kq.tra_loi = $r.choices[0].message.content
        $kq.tra_loi_rong = [string]::IsNullOrWhiteSpace($r.choices[0].message.content)
        Ghi "LUOT    tra loi: $($kq.tra_loi)"
    } catch {
        $kq.tra_loi_loi = $_.Exception.Message
        Ghi "LUOT    LOI: $($_.Exception.Message)"
    }

    $dinh = Vram38
    $kq.vram_dinh_mib = $dinh
    Ghi "DINH    VRAM 3090 = $dinh MiB"
    Stop-Process -Id $p.Id -Force
}

$kq | ConvertTo-Json -Depth 5 | Set-Content -Path $Ket -Encoding UTF8
Ghi "=== KET THUC === ket qua $Ket"
