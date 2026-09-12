# do_chot_co2.ps1 - hai ung vien nua, tim duoc tu tai lieu cong dong (12/09).
#
# Tra cuu PR goc cua `--reasoning-budget` (ggml-org/llama.cpp #25961) lam ro hai
# dieu ma toi da lam SAI:
#
# 1. `--reasoning-budget-message` - "should include the model's own closing tag
#    (e.g. </think>) as it is not appended automatically". Va: **de trong thi he
#    thong chi ep moi the dong**, tuc CAT CUT TRAN TRUI. Do dung la thu ta da
#    lam, va dung la ly do model nghi tiep ra ngoai `content`:
#
#        'Doc lap\n</think>\n\n2/9'        <- the dong nam trong content
#        '1. **Analyze the Request:**...'  <- transcript ro ra content
#
#    Nghien cuu ma PR dan: chen mot the dong KEM "Final Answer:" truoc cho cat
#    **tot hon han** cat cut. Nen bai D chen mot cau ket chuyen tiep tu te.
#
# 2. `-rea / --reasoning [on|off|auto]` la cong tac TAT SUY NGHI dung nghia.
#    Lan truoc toi thu `--chat-template-kwargs '{"enable_thinking":false}'` va
#    no khong nap duoc - sai CONG CU chu khong phai cai nao cung hong.
#
# Bai E do luon phuong an "khong nghi gi ca". Voi vai tro cua LTT-3.5 (viec noi
# bo: dich phu de, dich prompt anh, planner) thi suy luan co the la thu khong
# can - va bo han thi khong con LOP LOI nay nua, chu khong phai giam bot.
#
# * Qwen khuyen nghi bo tham so KHAC cho che do khong-nghi: temp 0.7, top-p 0.8,
#    top-k 20 (khac voi 0.6/0.95/20 cua che do nghi). Bai E dung dung bo do.

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Cham   = 'E:\AI\ltt_dual\bench\danh_gia_llm.py'
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\chot_co2.log"
$M      = 'H:\LTT_LLM\models'

# Cau ket duoc viet bang TIENG ANH co chu dich: Qwen3.5 luon nghi bang tieng Anh
# (QwenLM issue #35), nen mot cau tieng Viet chen vao giua dong suy nghi se la
# mot cho doi ngon ngu dot ngot. Va no noi ro "cung ngon ngu voi cau hoi" de keo
# phan TRA LOI ve dung thu tieng khach dung - chinh cho ma model hay truot.
$KET = "\n\nI have enough information now. I will stop thinking and give the final answer directly, in the same language as the user's question.\n</think>\n\n"

$DsBai = @(
    @{ n = 'D_budget512_co_loi_ket'
       them = @('--reasoning-budget', '512', '--reasoning-budget-message', ('"' + $KET + '"')) }


function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

Remove-Item -Path $Log -Force -ErrorAction SilentlyContinue
Ghi "=== CHOT CO 2D === chi chay lai D (lan truoc hong vi loi boc nhay)"

foreach ($b in $DsBai) {
    Get-Process llama-server -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 5

    $a = @('-m', "$M\Qwen3.5-9B-Q6_K-unsloth.gguf", '--mmproj', "$M\mmproj-9B-F16-unsloth.gguf",
           '--jinja', '--reasoning-format', 'deepseek',
           '-fa', '1', '-ngl', '999', '--metrics',
           '-c', '262144', '-np', '3', '-kvu',
           '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
           '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
           '--host', '127.0.0.1', '--port', '8291') + $b.them

    $env:CUDA_VISIBLE_DEVICES = $Uuid35
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\cc2_$($b.n).out.log" `
            -RedirectStandardError  "$Thu\cc2_$($b.n).err.log"
    $xanh = $false
    for ($i = 0; $i -lt 300; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { break }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:8291/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
    }
    if (-not $xanh) {
        $duoi = (Get-Content "$Thu\cc2_$($b.n).err.log" -Tail 6 -ErrorAction SilentlyContinue) -join ' | '
        Ghi "TRUOT $($b.n) | $duoi"
        continue
    }
    Ghi "---- $($b.n)"
    & $Python $Cham --thu-thap --url "http://127.0.0.1:8291" --model x --lan 5 `
        --ra "$Thu\cc2_$($b.n).json" 2>&1 | ForEach-Object { Ghi "  $_" }
    Stop-Process -Id $p.Id -Force
}

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
Ghi "=== KET THUC CHOT CO 2D ==="
