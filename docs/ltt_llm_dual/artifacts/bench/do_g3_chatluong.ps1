# do_g3_chatluong.ps1 - pha THU THAP cua cong G3: cham chat luong hai ung vien
# Q6_K cua LTT-3.5 bang `tools/danh_gia_llm.py`.
#
# Vi sao can pha nay: G3 do VRAM xong thi HAI ung vien deu vua card 16 GB (bien
# 2.780 va 2.888 MiB) va toc do lech trong khoang nhieu cua mot luot do. Tuc
# truc VRAM/toc do KHONG phan biet duoc chung. Ke hoach noi thang: chon bang
# CHAM CHAT LUONG, khong chon bang suy luan hay bang cai ten kho.
#
# `danh_gia_llm.py` tach doi co chu dich: `--thu-thap` goi model va ghi dau ra
# THO (chay o day, may B), `--cham` doc tep do va cham diem (chay o may A, vi
# cham bai lap trinh phai CHAY ma model sinh ra - khong lam viec do tren may
# dang phuc vu khach).
#
# `--lan 3` + lay trung vi: bo nay co y KHONG truyen temperature (tham so lay
# mau khong nam trong hop dong cong khai, va cache CUDA graph khoa theo chung),
# nen no doi pho voi nhieu lay mau bang cach chay nhieu luot.

param(
    [int]$Lan = 3,
    [int]$Ctx = 262144,
    [int]$Np  = 4
)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Cham   = 'E:\AI\ltt_dual\bench\danh_gia_llm.py'
$Port   = 8291
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\g3_chatluong.log"

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

function DonDep {
    Get-Process llama-server -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 4
}

$M = 'H:\LTT_LLM\models'
$DsUngVien = @(
    @{ ten = 'unsloth';  gguf = "$M\Qwen3.5-9B-Q6_K-unsloth.gguf";  mm = "$M\mmproj-9B-F16-unsloth.gguf" }
    @{ ten = 'lmstudio'; gguf = "$M\Qwen3.5-9B-Q6_K-lmstudio.gguf"; mm = "$M\mmproj-9B-BF16-lmstudio.gguf" }
)

Remove-Item -Path $Log -Force -ErrorAction SilentlyContinue
Ghi "=== G3 CHAT LUONG === lan=$Lan ctx=$Ctx np=$Np"

foreach ($uv in $DsUngVien) {
    DonDep
    Ghi "---- $($uv.ten)"

    # Cau hinh PHAI giong het nhau giua hai ung vien. Doi mot co la mat kha nang
    # so sanh: khi do ta khong con biet diem lech den tu tep GGUF hay tu co.
    $a = @('-m', $uv.gguf, '--mmproj', $uv.mm,
           '--jinja', '--reasoning-format', 'deepseek',
           '-fa', '1', '-ngl', '999', '--metrics',
           '-c', "$Ctx", '-np', "$Np", '-kvu',
           '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
           '--host', '127.0.0.1', '--port', "$Port")

    $env:CUDA_VISIBLE_DEVICES = $Uuid35
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\g3cl_$($uv.ten).out.log" `
            -RedirectStandardError  "$Thu\g3cl_$($uv.ten).err.log"

    $xanh = $false
    for ($i = 0; $i -lt 300; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { break }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
    }
    if (-not $xanh) {
        Ghi "TRUOT   $($uv.ten): khong nap duoc"
        if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
        continue
    }
    Ghi "XANH    $($uv.ten) nap sau $i s"

    $ra = "$Thu\g3_thuthap_$($uv.ten).json"
    & $Python $Cham --thu-thap --url "http://127.0.0.1:$Port" --model x --lan $Lan --ra $ra 2>&1 |
        ForEach-Object { Ghi "$($uv.ten): $_" }
    Ghi "$($uv.ten): thu thap thoat ma $LASTEXITCODE, ra $ra"

    Stop-Process -Id $p.Id -Force
}

DonDep
Ghi "=== KET THUC G3 CHAT LUONG ==="
