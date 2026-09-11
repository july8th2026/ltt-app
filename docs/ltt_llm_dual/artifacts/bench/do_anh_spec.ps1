# do_anh_spec.ps1 - chay probe_anh_spec.py tren ho so LTT-3.8 da chot (L-14).
#
# Tra loi cau "co can nang llama.cpp len b10906+ ngay khong" bang MOT CON SO
# cua chinh may nay, thay vi bang mot bao cao do tren ROCm voi bo nhap khac.
#
# `-np 1`: probe can hai bai giong het nhau tru mot bien. Voi nhieu slot thi
# luot text sau anh co the roi vao slot KHAC (slot chua tung thay anh), va khi
# do phep do khong con do dieu no dinh do.

param(
    [int]$Lan = 4,
    [int]$Ctx = 221184
)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Gguf   = 'H:\LTT_LLM\models\Qwen3.8-27B-UD-Q4_K_M.gguf'
$Mmproj = 'H:\LTT_LLM\models\mmproj-F16.gguf'
$Tmpl   = 'H:/LTT_LLM/models/chat_template.jinja'
$Uuid38 = 'GPU-26623278-4fa5-82db-4306-237651b03e78'
$Python = 'C:\Python313\python.exe'
$Probe  = 'E:\AI\ltt_dual\bench\probe_anh_spec.py'
$Port   = 8290
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\anh_spec.log"

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 4

Remove-Item -Path $Log -Force -ErrorAction SilentlyContinue
Ghi "=== ANH+SPEC (#28715) === build b10883, ctx=$Ctx np=1 lan=$Lan"

$a = @('-m', $Gguf, '--mmproj', $Mmproj,
       '--jinja', '--chat-template-file', $Tmpl,
       '--reasoning-format', 'deepseek',
       '-fa', '1', '-ngl', '999',
       '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2', '--metrics',
       '-c', "$Ctx", '-np', '1', '-kvu',
       '--cache-type-k', 'q4_0', '--cache-type-v', 'q4_0',
       '--host', '127.0.0.1', '--port', "$Port")

$env:CUDA_VISIBLE_DEVICES = $Uuid38
$p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
        -RedirectStandardOutput "$Thu\anh_spec.out.log" -RedirectStandardError "$Thu\anh_spec.err.log"

$xanh = $false
for ($i = 0; $i -lt 300; $i++) {
    Start-Sleep -Seconds 1
    if ($p.HasExited) { break }
    try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
}
if (-not $xanh) {
    Ghi "TRUOT   khong nap duoc"
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    Ghi "=== KET THUC ==="
    exit 1
}
Ghi "XANH    nap sau $i s"

& $Python $Probe --cong $Port --lan $Lan --ra "$Thu\anh_spec.jsonl" 2>&1 |
    ForEach-Object { Ghi "probe: $_" }
Ghi "probe thoat ma $LASTEXITCODE"

Stop-Process -Id $p.Id -Force
Ghi "=== KET THUC ==="
