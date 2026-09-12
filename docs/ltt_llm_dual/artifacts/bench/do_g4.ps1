# do_g4.ps1 - cong G4: bon con so theo TUNG model, tren DUNG cau hinh da chot.
#
# Chay ca hai model, moi cai mot lan, va do thoi gian NAP tu am (T_NAP_LLM) ngay
# trong lan nap cua chinh phep do - khong can mot lan chay rieng.
#
# Cau hinh lay tu L-14 (ngu canh + slot) va L-15 (bo co chong nghi lan man):
#   ltt-3.8  3090     -c 221184 -np 3  KV q4_0  mmproj GPU  draft-mtp n=2
#   ltt-3.5  5060 Ti  -c 262144 -np 3  KV q8_0  mmproj GPU  draft-mtp n=2
# Ca hai: --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 1.5
#         --reasoning-budget 512

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid38 = 'GPU-26623278-4fa5-82db-4306-237651b03e78'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Probe  = 'E:\AI\ltt_dual\bench\probe_g4.py'
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\g4.log"
$Ra     = "$Thu\g4.jsonl"
$M      = 'H:\LTT_LLM\models'

$CHUNG = @('--jinja', '--reasoning-format', 'deepseek',
           '-fa', '1', '-ngl', '999', '--metrics', '-kvu',
           '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
           '--temp', '0.6', '--top-p', '0.95', '--top-k', '20', '--min-p', '0',
           '--presence-penalty', '1.5', '--reasoning-budget', '512')

$DsModel = @(
    @{ nhan = 'ltt-3.8'; uuid = $Uuid38; cong = 8290
       rieng = @('-m', "$M\Qwen3.8-27B-UD-Q4_K_M.gguf", '--mmproj', "$M\mmproj-F16.gguf",
                 '--chat-template-file', 'H:/LTT_LLM/models/chat_template.jinja',
                 '-c', '221184', '-np', '3',
                 '--cache-type-k', 'q4_0', '--cache-type-v', 'q4_0') }
    @{ nhan = 'ltt-3.5'; uuid = $Uuid35; cong = 8291
       rieng = @('-m', "$M\Qwen3.5-9B-Q6_K-unsloth.gguf", '--mmproj', "$M\mmproj-9B-F16-unsloth.gguf",
                 '-c', '262144', '-np', '3',
                 '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0') }
)

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 5

Remove-Item -Path $Log, $Ra -Force -ErrorAction SilentlyContinue
Ghi "=== G4 ==="

foreach ($md in $DsModel) {
    Ghi "---- $($md.nhan)"
    $a = $md.rieng + $CHUNG + @('--host', '127.0.0.1', '--port', "$($md.cong)")
    $env:CUDA_VISIBLE_DEVICES = $md.uuid

    # T_NAP_LLM do ngay o day: tep vua duoc doc o lan chay truoc nen kho AM.
    # Con so nay thay `t_nap_llm_s = 45.0` dang gia dinh trong may trang thai
    # residency (Task 5.2) - mot con so gia dinh o do quyet dinh khi nao trong
    # tai dam doi cu tru, nen no phai la so DO.
    $t0 = Get-Date
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\g4_$($md.nhan).out.log" `
            -RedirectStandardError  "$Thu\g4_$($md.nhan).err.log"
    $xanh = $false
    for ($i = 0; $i -lt 600; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { break }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$($md.cong)/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
    }
    $giay_nap = [math]::Round(((Get-Date) - $t0).TotalSeconds, 2)
    if (-not $xanh) {
        $duoi = (Get-Content "$Thu\g4_$($md.nhan).err.log" -Tail 8 -ErrorAction SilentlyContinue) -join ' | '
        Ghi "TRUOT   $($md.nhan) khong nap duoc sau $giay_nap s | $duoi"
        if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
        continue
    }
    Ghi "NAP     $($md.nhan): $giay_nap s (kho AM)"
    Add-Content -Path $Ra -Encoding UTF8 -Value (
        (@{ nhan = $md.nhan; bai = 't_nap_llm'; giay_nap_am = $giay_nap } |
         ConvertTo-Json -Compress))

    & $Python $Probe --cong $md.cong --uuid $md.uuid --nhan $md.nhan --co-anh --ra $Ra 2>&1 |
        ForEach-Object { Ghi "  $_" }
    Stop-Process -Id $p.Id -Force
    Start-Sleep -Seconds 4
}

Ghi "=== KET THUC G4 ==="
