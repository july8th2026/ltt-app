# do_g5.ps1 - cong G5: nap tu kho LANH ton bao lau, so voi kho AM.
#
# VI SAO CAN CA HAI CON SO: trong tai residency (Task 5.2) dung `t_nap_llm_s` de
# quyet dinh khi nao DANG doi cu tru 3090 giua model anh va LTT-3.8. G4 da do
# kho AM (16,3 s cho 3.8, 12,1 s cho 3.5) - nhung trong tai gap CA HAI truong
# hop: doi qua lai lien tuc thi am, con sau mot dem khong ai goi thi lanh.
# Mot con so duy nhat se sai o mot trong hai phia.
#
# LAM LANH THE NAO - va vi sao khong dung `Clear-StandbyList`:
#   Cong cu do (RAMMap cua Sysinternals) khong co san tren may B va cai them mot
#   binary vao may dang phuc vu khach de chay mot phep do la mot cai gia khong
#   dang. Thay vao do dung DUNG co cua llama.cpp: `--load-mode direct` doc tep
#   bang I/O truc tiep, KHONG qua page cache cua Windows. Do la dinh nghia thao
#   tac cua "lanh" ma ta can: byte phai di tu dia len.
#
#   !! KHONG dung `--no-mmap` (co cu): b10875 da thay no bang `--load-mode`, va
#      ten cu con nhan duoc nhung y nghia da khac.
#
# Moi model do BA lan moi che do, lay trung vi: thoi gian nap phu thuoc dia va
# dia thi that thuong hon GPU.

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid38 = 'GPU-26623278-4fa5-82db-4306-237651b03e78'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\g5.log"
$Ket    = "$Thu\g5.jsonl"
$M      = 'H:\LTT_LLM\models'

$L16 = @('--reasoning-budget', '512', '--temp', '0.6', '--top-p', '0.95',
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
    @{ n = 'ltt-3.8'; uuid = $Uuid38; cong = 8290
       rieng = @('-m', "$M\Qwen3.8-27B-UD-Q4_K_M.gguf", '--mmproj', "$M\mmproj-F16.gguf",
                 '--chat-template-file', 'H:/LTT_LLM/models/chat_template.jinja',
                 '-c', '221184', '-np', '3',
                 '--cache-type-k', 'q4_0', '--cache-type-v', 'q4_0') }
    @{ n = 'ltt-3.5'; uuid = $Uuid35; cong = 8291
       rieng = @('-m', "$M\Qwen3.5-9B-Q6_K-unsloth.gguf", '--mmproj', "$M\mmproj-9B-F16-unsloth.gguf",
                 '-c', '262144', '-np', '3',
                 '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0') }
)

Remove-Item -Path $Log, $Ket -Force -ErrorAction SilentlyContinue
Ghi "=== G5 === kho AM vs kho LANH (--load-mode direct), 3 lan moi che do"

foreach ($md in $DsModel) {
    foreach ($che in @('am', 'lanh')) {
        for ($lan = 1; $lan -le 3; $lan++) {
            DonDep
            $them = if ($che -eq 'lanh') { @('--load-mode', 'direct') } else { @() }
            $a = $md.rieng + @('--jinja', '--reasoning-format', 'deepseek',
                               '-fa', '1', '-ngl', '999', '--metrics', '-kvu',
                               '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
                               '--host', '127.0.0.1', '--port', "$($md.cong)") + $L16 + $them
            $env:CUDA_VISIBLE_DEVICES = $md.uuid
            $t0 = Get-Date
            $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
                    -RedirectStandardOutput "$Thu\g5_$($md.n)_$che.out.log" `
                    -RedirectStandardError  "$Thu\g5_$($md.n)_$che.err.log"
            $xanh = $false
            for ($i = 0; $i -lt 900; $i++) {
                Start-Sleep -Seconds 1
                if ($p.HasExited) { break }
                try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$($md.cong)/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
            }
            $giay = [math]::Round(((Get-Date) - $t0).TotalSeconds, 2)
            if (-not $xanh) {
                $duoi = (Get-Content "$Thu\g5_$($md.n)_$che.err.log" -Tail 5 -ErrorAction SilentlyContinue) -join ' | '
                Ghi "TRUOT $($md.n) $che lan$lan | $duoi"
                if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
                continue
            }
            Ghi "$($md.n) $che lan$($lan): $giay s"
            Add-Content -Path $Ket -Encoding UTF8 -Value (
                (@{ model = $md.n; che_do = $che; lan = $lan; giay_nap = $giay } |
                 ConvertTo-Json -Compress))
            Stop-Process -Id $p.Id -Force
        }
    }
}

DonDep
Ghi "=== KET THUC G5 ==="
