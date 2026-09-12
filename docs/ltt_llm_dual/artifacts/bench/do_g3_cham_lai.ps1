# do_g3_cham_lai.ps1 - cham lai TOAN BO bo de voi ban va, khong chi hai bai
# tieng Viet.
#
# VI SAO PHAI CHAM LAI CA BO: `--reasoning-budget 512` sua duoc tieng Viet bang
# cach CAT NGAN khoi nghi. Thu bi cat la thu mot bai KHO co the dang can. Neu
# no keo diem lap trinh hay ngu canh dai xuong thi no khong phai ban va, no la
# mot cuoc doi chac — va doi chac thi phai thay CA HAI ben.
#
# Doi chieu: lan cham dau (khong ban va) duoc 27/36 = 75%, mat dung o hai bai
# tieng Viet (0/6) cong lap_trinh 2/3, sua_loi 2/3, sinh_dai 2/3.
#
# Tham so lay mau dat o SERVER chu khong gui theo request: `danh_gia_llm.py` co
# y khong truyen chung (cache CUDA graph khoa theo bo tham so), va production
# cung se dat o `llama-swap.yaml`. Do o dung noi no se chay.

param(
    [int]$Budget = 512,
    [int]$Lan = 3
)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Cham   = 'E:\AI\ltt_dual\bench\danh_gia_llm.py'
$Port   = 8291
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\g3_cham_lai.log"
$M      = 'H:\LTT_LLM\models'

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 4

Remove-Item -Path $Log -Force -ErrorAction SilentlyContinue
Ghi "=== CHAM LAI === budget=$Budget lan=$Lan"

$a = @('-m', "$M\Qwen3.5-9B-Q6_K-unsloth.gguf", '--mmproj', "$M\mmproj-9B-F16-unsloth.gguf",
       '--jinja', '--reasoning-format', 'deepseek',
       '-fa', '1', '-ngl', '999', '--metrics',
       '-c', '262144', '-np', '3', '-kvu',
       '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
       # Khuyen nghi chinh thuc cua Qwen cho che do thinking. Mac dinh cua
       # llama-server lech o bon cho, va `presence-penalty 0` la cho nang nhat:
       # no chinh la phanh chong lap ma che do hong nay can.
       '--temp', '0.6', '--top-p', '0.95', '--top-k', '20', '--min-p', '0',
       '--presence-penalty', '1.5',
       '--reasoning-budget', "$Budget",
       '--host', '127.0.0.1', '--port', "$Port")

$env:CUDA_VISIBLE_DEVICES = $Uuid35
$p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
        -RedirectStandardOutput "$Thu\g3_cham_lai.out.log" -RedirectStandardError "$Thu\g3_cham_lai.err.log"

$xanh = $false
for ($i = 0; $i -lt 300; $i++) {
    Start-Sleep -Seconds 1
    if ($p.HasExited) { break }
    try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
}
if (-not $xanh) {
    $duoi = (Get-Content "$Thu\g3_cham_lai.err.log" -Tail 8 -ErrorAction SilentlyContinue) -join ' | '
    Ghi "TRUOT   khong nap duoc | $duoi"
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    Ghi "=== KET THUC CHAM LAI ==="
    exit 1
}
Ghi "XANH    nap sau $i s"

& $Python $Cham --thu-thap --url "http://127.0.0.1:$Port" --model x --lan $Lan `
    --ra "$Thu\g3_thuthap_vabudget$Budget.json" 2>&1 | ForEach-Object { Ghi "  $_" }
Ghi "thu thap thoat ma $LASTEXITCODE"

Stop-Process -Id $p.Id -Force
Ghi "=== KET THUC CHAM LAI ==="
