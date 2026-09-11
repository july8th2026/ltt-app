# do_toc_do_B.ps1 - ung vien B co giu LTT-3.8 tren cong nghiem thu B khong?
#
# B = --reasoning-budget 512 + temp/top-p/top-k/min-p cua Qwen, BO
#     `presence-penalty`.
#
# Chat luong da do (bo de day du, lan 5): B = 59/60, tieng Viet 100% - ngang
# hang A (co presence-penalty). Con lai duy nhat cau hoi toc do, vi gia thuyet
# la gan nhu toan bo 11% mat mat den tu presence-penalty (phanh chay MOI BUOC
# giai ma) chu khong tu ba tham so kia.
#
# Moc doi chieu da do, cung kich ban c1, cung may:
#     khong co gi        63,60 tok/s   (dai 61,8-65,1)
#     chi budget 512     65,18         (dai 61,5-66,2)
#     A (co penalty)     56,61         (dai 55,2-57,1)  <- TRUOT cong B (60,0)
#
# Chay CA HAI model: 3.8 la cai suyt truot cong, con 3.5 de cap nhat so cho
# bang gia (D07) vi bo co doi thi tok/s doi theo.

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid38 = 'GPU-26623278-4fa5-82db-4306-237651b03e78'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Bench  = 'E:\AI\ltt_dual\bench\bench.py'
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\toc_do_B.log"
$M      = 'H:\LTT_LLM\models'

$B = @('--reasoning-budget', '512', '--temp', '0.6', '--top-p', '0.95',
       '--top-k', '20', '--min-p', '0')

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

function DonDep {
    Get-Process llama-server -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 5
}

$DsModel = @(
    @{ n = '38'; uuid = $Uuid38; cong = 8290
       rieng = @('-m', "$M\Qwen3.8-27B-UD-Q4_K_M.gguf", '--mmproj', "$M\mmproj-F16.gguf",
                 '--chat-template-file', 'H:/LTT_LLM/models/chat_template.jinja',
                 '-c', '221184', '-np', '3',
                 '--cache-type-k', 'q4_0', '--cache-type-v', 'q4_0') }
    @{ n = '35'; uuid = $Uuid35; cong = 8291
       rieng = @('-m', "$M\Qwen3.5-9B-Q6_K-unsloth.gguf", '--mmproj', "$M\mmproj-9B-F16-unsloth.gguf",
                 '-c', '262144', '-np', '3',
                 '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0') }
)

Remove-Item -Path $Log, "$Thu\tocB_38.jsonl", "$Thu\tocB_35.jsonl" -Force -ErrorAction SilentlyContinue
Ghi "=== TOC DO UNG VIEN B ==="

foreach ($md in $DsModel) {
    DonDep
    $a = $md.rieng + @('--jinja', '--reasoning-format', 'deepseek',
                       '-fa', '1', '-ngl', '999', '--metrics', '-kvu',
                       '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
                       '--host', '127.0.0.1', '--port', "$($md.cong)") + $B
    $env:CUDA_VISIBLE_DEVICES = $md.uuid
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\tocB_$($md.n).out.log" `
            -RedirectStandardError  "$Thu\tocB_$($md.n).err.log"
    $xanh = $false
    for ($i = 0; $i -lt 600; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { break }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$($md.cong)/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
    }
    if (-not $xanh) { Ghi "TRUOT $($md.n)"; continue }
    Ghi "---- $($md.n)"
    & $Python $Bench --cong $md.cong --model x --uuid $md.uuid --kich-ban c1 `
        --lan 5 --ra "$Thu\tocB_$($md.n).jsonl" 2>&1 | Out-Null
    Stop-Process -Id $p.Id -Force
}

DonDep
Ghi "=== KET THUC TOC DO B ==="
