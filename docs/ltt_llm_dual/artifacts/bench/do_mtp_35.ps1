# do_mtp_35.ps1 - LTT-3.5 co dung duoc MTP khong, va duoc bao nhieu.
#
# GIA THUYET (12/09, tu log nap that + tai lieu cong dong):
#
#   Log nap cua ung vien unsloth in ra:
#       W model has unused tensor blk.32.nextn.eh_proj.weight -- ignoring
#       W model has unused tensor blk.32.nextn.enorm.weight   -- ignoring
#       ...
#   `nextn` CHINH LA dau MTP. Tep GGUF CO san dau do, va llama.cpp dang VUT no
#   di vi ta khong truyen `--spec-type draft-mtp`. Cong dong mo ta dung hien
#   tuong nay: "Without the flag it prints 'unused tensor, ignoring' and you
#   would never guess spec decode works."
#
#   Spec ghi "3.5 khong MTP" - nhung dong do viet TRUOC khi biet se dung tep
#   nao. Ung vien unsloth den tu kho ten "Qwen3.5-9B-MTP-GGUF".
#
# VI SAO DIEU NAY QUAN TRONG: 5060 Ti co bang thong 448 GB/s. Model ~7,3 GiB
# => tran ly thuyet cua giai ma la ~61 tok/s, va ta do duoc 53 (~87%). Tuc
# KHONG con gi de vat tu viec chinh tham so: giai ma bi chan boi bang thong,
# khong phai boi cau hinh. Thu DUY NHAT vuot qua duoc tran do la sinh nhieu
# token moi lan doc trong so - tuc suy doan. Dung co che da lam 3.8 dat 66,7
# tok/s trong khi tran bang thong cua no chi ~57.
#
# Bai do: cung mot tep, cung moi thu, chi khac co MTP.
#   0 = khong MTP (nhu hien nay)     2, 3 = --spec-draft-n-max 2 hoac 3
#
# Lam ca hai ung vien: neu chi unsloth co MTP thi do la mot ly do CHON tep,
# va no khong nam trong bang VRAM lan bang chat luong.

param(
    [int]$Lan = 3,
    [int]$Ctx = 262144,
    [int]$Np  = 3
)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Bench  = 'E:\AI\ltt_dual\bench\bench.py'
$Port   = 8291
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\mtp_35.log"
$M      = 'H:\LTT_LLM\models'

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

function DonDep {
    Get-Process llama-server -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 4
}

$DsBai = @(
    @{ uv = 'unsloth';  nmax = 0 }
    @{ uv = 'unsloth';  nmax = 2 }
    @{ uv = 'unsloth';  nmax = 3 }
    @{ uv = 'lmstudio'; nmax = 0 }
    @{ uv = 'lmstudio'; nmax = 2 }
)

Remove-Item -Path $Log -Force -ErrorAction SilentlyContinue
Ghi "=== MTP 3.5 === ctx=$Ctx np=$Np lan=$Lan"

foreach ($b in $DsBai) {
    DonDep
    if ($b.uv -eq 'unsloth') {
        $Gguf = "$M\Qwen3.5-9B-Q6_K-unsloth.gguf";  $Mm = "$M\mmproj-9B-F16-unsloth.gguf"
    } else {
        $Gguf = "$M\Qwen3.5-9B-Q6_K-lmstudio.gguf"; $Mm = "$M\mmproj-9B-BF16-lmstudio.gguf"
    }
    $nhan = "$($b.uv)_mtp$($b.nmax)"
    Ghi "---- $($nhan)"

    $a = @('-m', $Gguf, '--mmproj', $Mm,
           '--jinja', '--reasoning-format', 'deepseek',
           '-fa', '1', '-ngl', '999', '--metrics',
           '-c', "$Ctx", '-np', "$Np", '-kvu',
           '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
           '--host', '127.0.0.1', '--port', "$Port")
    if ($b.nmax -gt 0) {
        $a += @('--spec-type', 'draft-mtp', '--spec-draft-n-max', "$($b.nmax)")
    }

    $env:CUDA_VISIBLE_DEVICES = $Uuid35
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\mtp_$nhan.out.log" `
            -RedirectStandardError  "$Thu\mtp_$nhan.err.log"

    $xanh = $false
    for ($i = 0; $i -lt 300; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { break }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
    }
    if (-not $xanh) {
        $duoi = (Get-Content "$Thu\mtp_$nhan.err.log" -Tail 8 -ErrorAction SilentlyContinue) -join ' | '
        Ghi "TRUOT   $($nhan): khong nap duoc | $duoi"
        if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
        continue
    }

    # Bang chung TRUC TIEP rang dau MTP da duoc nap chu khong bi vut: dem so
    # dong "unused tensor ... nextn" trong log nap. Khong co MTP thi > 0.
    $bo_qua = (Select-String -Path "$Thu\mtp_$nhan.err.log" -Pattern 'unused tensor.*nextn' -ErrorAction SilentlyContinue | Measure-Object).Count
    $vram = (& nvidia-smi --query-gpu=uuid,memory.used --format=csv,noheader,nounits |
             Where-Object { $_ -like "$Uuid35*" }) -split ',\s*' | Select-Object -Last 1
    Ghi "NAP     $($nhan): xanh sau $i s | nextn bi bo qua = $bo_qua | VRAM $vram MiB"

    & $Python $Bench --cong $Port --model x --uuid $Uuid35 --kich-ban c1 `
        --lan $Lan --ra "$Thu\mtp_$nhan.jsonl" 2>&1 | ForEach-Object { Ghi "$($nhan): $_" }

    try {
        $mt = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/metrics" -TimeoutSec 10
        $d = ($mt -split "`n" | Where-Object { $_ -like '*spec_decode_num_accepted*' -and $_ -notlike '#*' }) -join ' ; '
        Ghi "$($nhan): metrics spec = $d"
    } catch { Ghi "$($nhan): khong doc duoc /metrics" }

    Stop-Process -Id $p.Id -Force
}

DonDep
Ghi "=== KET THUC MTP 3.5 ==="
