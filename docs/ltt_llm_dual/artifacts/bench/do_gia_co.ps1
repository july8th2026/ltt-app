# do_gia_co.ps1 - BO CO CHONG NGHI-LAN-MAN (L-15) TON BAO NHIEU TOC DO?
#
# Cong G4 vua tra ve mot con so lam toi phai dung lai:
#
#     LTT-3.5 o C1, cau hinh L-14 + L-15  ->  58,12 tok/s
#     LTT-3.5 o C1, cau hinh L-14 (khong L-15) -> 73,00 tok/s   (do luc 01:02)
#     LTT-3.8 o C1, cau hinh L-14 + L-15  ->  56,00 tok/s
#     LTT-3.8 moc C1 CHINH THUC (R18)     ->  66,70 tok/s
#
# Tuc bo co da lam bo de len 36/36 co the dang lay di ~16-20% toc do giai ma.
# Neu dung thi LTT-3.8 TUT XUONG DUOI nguong cong nghiem thu B (60,0 tok/s) -
# va mot ban va lam truot cong nghiem thu thi phai duoc biet TRUOC khi trien
# khai, khong phai sau.
#
# !! Chua duoc ket luan: hai con so cu do o hai lan chay khac nhau, va L-14 cung
#    doi ngu canh. Bai nay tach tung co ra de biet CAI NAO tra tien:
#
#     A  khong co gi           <- moc so sanh
#     B  chi tham so lay mau   (temp/top-p/top-k/min-p/presence-penalty)
#     C  chi --reasoning-budget 512
#     D  ca hai                <- cau hinh L-15 dang de xuat
#
# Do them `spec_decode_num_accepted`: gia thuyet manh nhat la mot trong hai co
# lam hong suy doan MTP, va neu the thi con so do se sut chu khong chi tok/s.

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Bench  = 'E:\AI\ltt_dual\bench\bench.py'
$Port   = 8291
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\gia_co.log"
$M      = 'H:\LTT_LLM\models'

$MAU  = @('--temp', '0.6', '--top-p', '0.95', '--top-k', '20', '--min-p', '0',
          '--presence-penalty', '1.5')
$BUDG = @('--reasoning-budget', '512')

$DsBai = @(
    @{ nhan = 'A_khong';       them = @() }
    @{ nhan = 'B_thamso';      them = $MAU }
    @{ nhan = 'C_budget';      them = $BUDG }
    @{ nhan = 'D_ca_hai';      them = ($MAU + $BUDG) }
)

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

Remove-Item -Path $Log -Force -ErrorAction SilentlyContinue
Ghi "=== GIA CUA BO CO L-15 === model 3.5, ctx 262144, np 3, MTP n=2"

foreach ($b in $DsBai) {
    Get-Process llama-server -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 4

    $a = @('-m', "$M\Qwen3.5-9B-Q6_K-unsloth.gguf", '--mmproj', "$M\mmproj-9B-F16-unsloth.gguf",
           '--jinja', '--reasoning-format', 'deepseek',
           '-fa', '1', '-ngl', '999', '--metrics',
           '-c', '262144', '-np', '3', '-kvu',
           '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
           '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
           '--host', '127.0.0.1', '--port', "$Port") + $b.them

    $env:CUDA_VISIBLE_DEVICES = $Uuid35
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\gia_$($b.nhan).out.log" `
            -RedirectStandardError  "$Thu\gia_$($b.nhan).err.log"
    $xanh = $false
    for ($i = 0; $i -lt 300; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { break }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
    }
    if (-not $xanh) { Ghi "TRUOT   $($b.nhan)"; continue }
    Ghi "---- $($b.nhan)"

    & $Python $Bench --cong $Port --model x --uuid $Uuid35 --kich-ban c1 `
        --lan 3 --ra "$Thu\gia_$($b.nhan).jsonl" 2>&1 | ForEach-Object { Ghi "  $_" }

    try {
        $mt = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/metrics" -TimeoutSec 10
        $d = ($mt -split "`n" | Where-Object { $_ -like '*spec_decode_num_accepted_tokens_total*' -and $_ -notlike '#*' }) -join ' '
        Ghi "$($b.nhan): $d"
    } catch { Ghi "$($b.nhan): khong doc duoc /metrics" }

    Stop-Process -Id $p.Id -Force
}

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
Ghi "=== KET THUC GIA CO ==="
