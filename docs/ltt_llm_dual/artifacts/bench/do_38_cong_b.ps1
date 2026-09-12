# do_38_cong_b.ps1 - LTT-3.8 o cau hinh SE TRIEN KHAI con dat cong nghiem thu B
# (>= 60,0 tok/s, ruling R18) khong?
#
# Vi sao phai do rieng: cong G4 do duoc 56,0 tok/s cho 3.8 voi cau hinh
# L-14 + L-15, tuc DUOI nguong. Nhung do la MOT luot, va phep do "gia cua bo co"
# sau do cho thay phuong sai giua cac lan chay la ~5-8% (co mot cau hinh con
# nhanh hon ban khong-co, dieu vo ly ve co che) => mot luot khong ket luan duoc.
#
# Thiet ke de khu TROI, chu khong chi tang so mau:
#   * moi cau hinh 5 luot
#   * chay XEN KE theo KHOI (X, Y, X, Y) chu khong (XXXXX, YYYYY): neu may nong
#     len hay mot tien trinh khac chen vao giua lo thi no anh huong DEU len ca
#     hai, thay vi doi tron ven mot ben.
#   * lay TRUNG VI, khong lay trung binh: mot luot bi chen ngang keo trung binh
#     di xa, trung vi thi khong.
#
#   X = L-14 (ngu canh + slot da chot), KHONG bo co L-15
#   Y = L-14 + L-15 (cau hinh se ghi vao llama-swap.yaml)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid38 = 'GPU-26623278-4fa5-82db-4306-237651b03e78'
$Python = 'C:\Python313\python.exe'
$Bench  = 'E:\AI\ltt_dual\bench\bench.py'
$Port   = 8290
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\do38.log"
$M      = 'H:\LTT_LLM\models'

$L15 = @('--temp', '0.6', '--top-p', '0.95', '--top-k', '20', '--min-p', '0',
         '--presence-penalty', '1.5', '--reasoning-budget', '512')

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

function ChayServer([string[]]$them) {
    Get-Process llama-server -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 5
    $a = @('-m', "$M\Qwen3.8-27B-UD-Q4_K_M.gguf", '--mmproj', "$M\mmproj-F16.gguf",
           '--chat-template-file', 'H:/LTT_LLM/models/chat_template.jinja',
           '--jinja', '--reasoning-format', 'deepseek',
           '-fa', '1', '-ngl', '999', '--metrics',
           '-c', '221184', '-np', '3', '-kvu',
           '--cache-type-k', 'q4_0', '--cache-type-v', 'q4_0',
           '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
           '--host', '127.0.0.1', '--port', "$Port") + $them
    $env:CUDA_VISIBLE_DEVICES = $Uuid38
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\do38.out.log" -RedirectStandardError "$Thu\do38.err.log"
    for ($i = 0; $i -lt 600; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { return $null }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { return $p } } catch { }
    }
    return $null
}

Remove-Item -Path $Log, "$Thu\do38_X.jsonl", "$Thu\do38_Y.jsonl" -Force -ErrorAction SilentlyContinue
Ghi "=== LTT-3.8 vs CONG B (60,0 tok/s) === xen ke 5 khoi"

for ($khoi = 1; $khoi -le 5; $khoi++) {
    foreach ($bai in @(@{ n = 'X'; them = @() }, @{ n = 'Y'; them = $L15 })) {
        $p = ChayServer $bai.them
        if ($null -eq $p) { Ghi "TRUOT khoi $khoi $($bai.n)"; continue }
        & $Python $Bench --cong $Port --model x --uuid $Uuid38 --kich-ban c1 `
            --lan 1 --ra "$Thu\do38_$($bai.n).jsonl" 2>&1 | Out-Null
        Ghi "khoi $khoi $($bai.n): xong"
        Stop-Process -Id $p.Id -Force
    }
}

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
Ghi "=== KET THUC DO38 ==="
