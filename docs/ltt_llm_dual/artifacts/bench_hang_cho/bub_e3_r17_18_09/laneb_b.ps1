param(
    [Parameter(Mandatory=$true)][string]$Buoc,
    [string]$Nguon = "",
    [string]$Tu = "",
    [int]$Dong = 4000
)
# Lane B (b/ub, E3, R-17) helper - copy of c4_18_09/c4_b.ps1; C4 helper on machine B. ASCII only. Read-only except: backup (copy), apply (copy staged -> yaml).
$ErrorActionPreference = "Stop"
$Yaml = "H:\LTT_LLM\gateway\llama-swap.yaml"
$Log = "H:\LTT_LLM\logs\llamaswap.log"

function Sha($p) { (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower() }

switch ($Buoc) {
    "sha" { "SHA " + (Sha $Yaml) }
    "backup" {
        $ts = Get-Date -Format "yyyyMMdd-HHmmss"
        $dst = "$Yaml.laneb-$ts"
        Copy-Item -LiteralPath $Yaml -Destination $dst
        "BACKUP $dst"
        "SHA_GOC " + (Sha $Yaml)
        "SHA_BAK " + (Sha $dst)
    }
    "apply" {
        if (-not (Test-Path -LiteralPath $Nguon)) { throw "no staged file $Nguon" }
        Copy-Item -LiteralPath $Nguon -Destination $Yaml -Force
        "APPLIED " + (Sha $Yaml) + " from " + (Sha $Nguon)
    }
    "vram" {
        $ps = Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'"
        foreach ($p in $ps) {
            $cl = $p.CommandLine
            $m = "?"
            if ($cl -match "Qwen3.8") { $m = "qwen38" } elseif ($cl -match "Qwen3.5") { $m = "qwen35" }
            $np = ""; if ($cl -match "-np\s+(\d+)") { $np = $Matches[1] }
            $c = ""; if ($cl -match "\s-c\s+(\d+)") { $c = $Matches[1] }
            $b = ""; if ($cl -match "\s-b\s+(\d+)") { $b = $Matches[1] }
            $ub = ""; if ($cl -match "\s-ub\s+(\d+)") { $ub = $Matches[1] }
            $d = 0; $s = 0
            try {
                $d = ((Get-Counter "\GPU Process Memory(pid_$($p.ProcessId)_*)\Dedicated Usage").CounterSamples | Measure-Object CookedValue -Sum).Sum
                $s = ((Get-Counter "\GPU Process Memory(pid_$($p.ProcessId)_*)\Shared Usage").CounterSamples | Measure-Object CookedValue -Sum).Sum
            } catch { }
            "PROC model=$m pid=$($p.ProcessId) np=$np c=$c b=$b ub=$ub dedicated_mib=$([math]::Round($d/1MB)) shared_mib=$([math]::Round($s/1MB))"
        }
        $q = & nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits
        foreach ($l in $q) { "GPU $l" }
    }
    "log" {
        # lines of llamaswap.log after marker time string $Tu (substring match start), filtered
        $lines = Get-Content -LiteralPath $Log -Tail $Dong
        $pat = "compute buffer size|KV buffer size|RS buffer size|draft acceptance|failed|error|out of memory|n_parallel|n_ctx_seq|llama_context: n_ctx|model loaded|exiting|reloading|configuration reloaded|graph splits"
        $lines | Select-String -Pattern $pat | ForEach-Object { $_.Line }
    }
    "lograw" {
        Get-Content -LiteralPath $Log -Tail $Dong
    }
    "logsize" { "SIZE " + (Get-Item -LiteralPath $Log).Length }
    "logfrom" {
        # print filtered lines from byte offset $Tu to end
        $fs = [IO.File]::Open($Log, 'Open', 'Read', 'ReadWrite')
        try {
            [void]$fs.Seek([int64]$Tu, 'Begin')
            $sr = New-Object IO.StreamReader($fs)
            $txt = $sr.ReadToEnd()
        } finally { $fs.Close() }
        $pat = "compute buffer size|KV buffer size|RS buffer size|draft acceptance|failed|error|out of memory|n_parallel|n_ctx_seq|n_ctx  |model loaded|exiting|reloading|configuration reloaded|graph splits|n_batch|n_ubatch"
        foreach ($l in ($txt -split "`n")) { if ($l -match $pat) { $l.TrimEnd() } }
    }
    "health" {
        try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 http://127.0.0.1:8299/health).Content } catch { "HEALTH_ERR $($_.Exception.Message)" }
    }
    "svc" {
        Get-Service LTTLlamaSwap, LTTLlmGateway, LTTRenderGateway, LTTComfyUI -ErrorAction SilentlyContinue | ForEach-Object { "SVC $($_.Name) $($_.Status)" }
    }
    "ket8299" {
        $c = Get-NetTCPConnection -LocalPort 8299 -State Established -ErrorAction SilentlyContinue | Where-Object { $_.RemoteAddress -ne "127.0.0.1" -and $_.RemoteAddress -ne "::1" }
        "KET8299 " + (@($c).Count)
    }
    default { throw "unknown step $Buoc" }
}
