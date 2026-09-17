# cua_so_b.ps1 - cac buoc TREN MAY B cho cua so bao tri do dac. Thuan ASCII.
# Chay qua SSH:  powershell -NoProfile -ExecutionPolicy Bypass -File E:\AI\ltt_dual\bench_hang_cho\cua_so_b.ps1 -Buoc <buoc>
#
#   kiem        CHI DOC: dich vu, /running, slot dang ban tung model, VRAM/util tung card,
#               tien trinh llama-server. Lan dau ghi anh chup truoc_cua_so.json.
#   nha35       nha qwen35-api khoi llama-swap (TU CHOI neu con slot dang chay).
#   nha38       nha qwen38-api (TU CHOI neu con slot dang chay).
#   dung_comfy  Stop-Service LTTComfyUI (giai phong ngu canh CUDA ~223 MiB tren 3090).
#   don_dep     giet llama-server tren CONG THU 8290/8292/8294 (khong cham 8281/8282).
#   khoi_phuc   don_dep -> nap qwen38-api (ComfyUI con tat) -> nap qwen35-api -> kiem tran
#               -> Start-Service LTTComfyUI neu truoc cua so no chay -> mot luot chat that
#               moi model qua 8280, content khong rong -> so VRAM voi anh chup.
#
# !! unload cua llama-swap KHONG drain (llm_gateway/api.py residency_nha, fifo.go) =>
#    buoc nha* tu kiem /slots truoc; chi goi khi da dung luu luong o may A.

param([Parameter(Mandatory = $true)][ValidateSet('kiem', 'nha35', 'nha38', 'dung_comfy', 'don_dep', 'khoi_phuc')][string]$Buoc)
$ErrorActionPreference = 'Stop'
$Swap = 'http://127.0.0.1:8280'
$Goc = 'E:\AI\ltt_dual\bench_hang_cho'
$Anh = Join-Path $Goc 'truoc_cua_so.json'
New-Item -ItemType Directory -Force -Path $Goc | Out-Null

function Running { try { return (Invoke-RestMethod "$Swap/running" -TimeoutSec 10).running } catch { throw "khong doc duoc llama-swap: $_" } }
function Gpu {
    foreach ($d in (& nvidia-smi --query-gpu=uuid,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits)) {
        $c = $d -split ',\s*'
        [pscustomobject]@{ uuid = $c[0]; ten = $c[1]; used = [int]$c[2]; total = [int]$c[3]; util = [int]$c[4] }
    }
}
function SlotBan($m) {
    if (-not $m.proxy) { return @() }
    try { return @((Invoke-RestMethod ($m.proxy + '/slots') -TimeoutSec 10) | Where-Object { $_.is_processing } | ForEach-Object { $_.id }) }
    catch { return @('khong_doc_duoc') }
}
function DonDep {
    Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" |
        Where-Object { $_.CommandLine -match '--port (8290|8292|8294)(\s|$)' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force; 'da giet server thu pid ' + $_.ProcessId }
    Get-ScheduledTask -TaskName 'LTT_BenchHangCho' -ErrorAction SilentlyContinue | ForEach-Object { 'task bench State=' + $_.State }
}
function Nha([string]$ten) {
    $m = @(Running | Where-Object { $_.model -eq $ten })
    if (-not $m) { "$ten khong nap - khong can nha"; return }
    $ban = SlotBan $m[0]
    if ($ban.Count -gt 0) { throw "$ten con slot dang chay: $($ban -join ',') - KHONG nha (unload khong drain)" }
    Invoke-RestMethod -Method Post "$Swap/api/models/unload/$ten" -TimeoutSec 60 | Out-Null
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 2
        if (-not (@(Running | Where-Object { $_.model -eq $ten }))) { break }
    }
    "da nha $ten; con chay: " + ((Running | ForEach-Object { $_.model }) -join ',')
    Gpu | ForEach-Object { '  ' + $_.ten + ' used=' + $_.used + ' util=' + $_.util }
}
function Nap([string]$ten) {
    try { Invoke-WebRequest -UseBasicParsing "$Swap/upstream/$ten/health" -TimeoutSec 600 | Out-Null } catch { "  (goi health tra loi: $($_.Exception.Message))" }
    for ($i = 0; $i -lt 150; $i++) {
        if (@(Running | Where-Object { $_.model -eq $ten -and $_.state -eq 'ready' })) { "$ten ready"; return }
        Start-Sleep -Seconds 2
    }
    throw "$ten khong ready sau 300 s - doc H:\LTT_LLM\logs\llamaswap.log"
}
function Tran([string]$ten) {
    $m = @(Running | Where-Object { $_.model -eq $ten })[0]
    $port = [regex]::Match($m.proxy, ':(\d+)$').Groups[1].Value
    $p = Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" | Where-Object { $_.CommandLine -match "--port $port(\s|$)" }
    $s = (Get-Counter "\GPU Process Memory(pid_$($p.ProcessId)_*)\Shared Usage").CounterSamples | Measure-Object CookedValue -Sum
    $d = (Get-Counter "\GPU Process Memory(pid_$($p.ProcessId)_*)\Dedicated Usage").CounterSamples | Measure-Object CookedValue -Sum
    "$ten pid $($p.ProcessId) dedicated=$([math]::Round($d.Sum/1MB)) MiB shared=$([math]::Round($s.Sum/1MB)) MiB (production 17/09: shared ~674 o 3.5 la muc nen, khong phai tran)"
}
function ChatThat([string]$ten) {
    $body = @{ model = $ten; max_tokens = 2048; messages = @(@{ role = 'user'; content = 'Tinh 12 * 17 va giai thich ngan gon.' }) } | ConvertTo-Json -Depth 5
    $r = Invoke-RestMethod -Method Post "$Swap/v1/chat/completions" -Body $body -ContentType 'application/json' -TimeoutSec 600
    $c = "$($r.choices[0].message.content)"
    "$ten chat that: finish=$($r.choices[0].finish_reason) token_ra=$($r.usage.completion_tokens) content_rong=$([string]::IsNullOrWhiteSpace($c))"
    if ([string]::IsNullOrWhiteSpace($c)) { "  CANH BAO: content rong (che do nghi khong dong) - thu lai 2 lan truoc khi ket luan" }
}

switch ($Buoc) {
    'kiem' {
        $sv = Get-Service LTTComfyUI, LTTLlamaSwap, LTTLlmGateway, LTTRenderGateway | ForEach-Object { [pscustomobject]@{ ten = $_.Name; trang_thai = "$($_.Status)" } }
        $run = @(Running | ForEach-Object { [pscustomobject]@{ model = $_.model; state = $_.state; slot_ban = (SlotBan $_) -join ',' } })
        $g = @(Gpu)
        $sv | Format-Table -AutoSize | Out-String
        $run | Format-Table -AutoSize | Out-String
        $g | Format-Table -AutoSize | Out-String
        DonDep
        if (-not (Test-Path $Anh)) {
            $j = @{ luc = (Get-Date).ToString('s'); dich_vu = $sv; running = $run; gpu = $g } | ConvertTo-Json -Depth 5
            [IO.File]::WriteAllText($Anh, $j, (New-Object Text.UTF8Encoding($false)))
            'da ghi anh chup ' + $Anh
        } else { 'anh chup truoc cua so da co: ' + $Anh + ' (xoa tay neu muon chup lai)' }
    }
    'nha35' { Nha 'qwen35-api' }
    'nha38' { Nha 'qwen38-api' }
    'dung_comfy' { Stop-Service LTTComfyUI; Start-Sleep -Seconds 5; 'LTTComfyUI=' + (Get-Service LTTComfyUI).Status; Gpu | ForEach-Object { '  ' + $_.ten + ' used=' + $_.used } }
    'don_dep' { DonDep }
    'khoi_phuc' {
        DonDep
        Start-Sleep -Seconds 3
        $t = Get-ScheduledTask -TaskName 'LTT_BenchHangCho' -ErrorAction SilentlyContinue
        if ($t -and $t.State -eq 'Running') { throw 'task bench con chay - Stop-ScheduledTask LTT_BenchHangCho truoc' }
        Nap 'qwen38-api'
        Nap 'qwen35-api'
        Tran 'qwen38-api'
        Tran 'qwen35-api'
        $truoc = $null
        if (Test-Path $Anh) { $truoc = Get-Content $Anh -Raw | ConvertFrom-Json }
        $comfy_truoc = if ($truoc) { ($truoc.dich_vu | Where-Object { $_.ten -eq 'LTTComfyUI' }).trang_thai } else { 'Running' }
        if ($comfy_truoc -eq 'Running' -and (Get-Service LTTComfyUI).Status -ne 'Running') { Start-Service LTTComfyUI; Start-Sleep -Seconds 15; 'da bat lai LTTComfyUI' }
        ChatThat 'qwen38-api'
        ChatThat 'qwen35-api'
        Get-Service LTTComfyUI, LTTLlamaSwap, LTTLlmGateway, LTTRenderGateway | ForEach-Object { $_.Name + '=' + $_.Status }
        'VRAM bay gio:'
        Gpu | ForEach-Object { '  ' + $_.ten + ' used=' + $_.used + ' util=' + $_.util }
        if ($truoc) { 'VRAM truoc cua so:'; $truoc.gpu | ForEach-Object { '  ' + $_.ten + ' used=' + $_.used } }
        'running: ' + ((Running | ForEach-Object { $_.model + ':' + $_.state }) -join ', ')
    }
}
