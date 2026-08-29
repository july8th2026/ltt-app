param(
    [string]$Root = 'H:\LTT_LLM',
    [string]$Prompts = '65536,73728,81920,90112,98304,131072',
    [int]$Repetitions = 1,
    [int]$GenerationTokens = 128,
    [switch]$Combined
)

$ErrorActionPreference = 'Stop'
# PowerShell 7 can turn native stderr (llama.cpp startup diagnostics) into a
# terminating error. Those diagnostics are expected and must be captured in the
# result log; the benchmark exit code remains the source of truth.
$PSNativeCommandUseErrorActionPreference = $false
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$resultDir = Join-Path $Root ("benchmarks\qwen-context-" + $stamp)
New-Item -ItemType Directory -Force $resultDir | Out-Null

$gpuLog = Join-Path $resultDir 'gpu.csv'
$resultLog = Join-Path $resultDir 'results.jsonl'
$metaLog = Join-Path $resultDir 'metadata.txt'
$bench = Join-Path $Root 'bin\llamacpp\llama-bench.exe'
$model = Join-Path $Root 'models\Qwen3.8-27B-UD-Q4_K_M.gguf'

@(
    "started_at=$((Get-Date).ToString('o'))"
    "prompts=$Prompts"
    "repetitions=$Repetitions"
    "generation_tokens=$GenerationTokens"
    "kv=q8_0"
    "flash_attention=on"
    "model=$model"
) | Set-Content -Path $metaLog -Encoding ascii

'timestamp,temp_c,fan_pct,gpu_pct,vram_used_mib,vram_free_mib,power_w' |
    Set-Content -Path $gpuLog -Encoding ascii

$monitor = Start-Job -ArgumentList $gpuLog -ScriptBlock {
    param($Path)
    while ($true) {
        $sample = & nvidia-smi `
            --query-gpu=timestamp,temperature.gpu,fan.speed,utilization.gpu,memory.used,memory.free,power.draw `
            --format=csv,noheader,nounits
        Add-Content -Path $Path -Value $sample -Encoding ascii
        Start-Sleep -Seconds 2
    }
}

$exitCode = 1
try {
    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $args = @('-m', $model)
    if ($Combined) {
        foreach ($prompt in $Prompts.Split(',')) {
            $args += @('-pg', ("$prompt,$GenerationTokens"))
        }
    } else {
        $args += @('-p', $Prompts, '-n', $GenerationTokens)
    }
    $args += @('-r', $Repetitions, '--delay', 3, '-ctk', 'q8_0', '-ctv', 'q8_0',
        '-ngl', 999, '-fa', 'on', '--progress', '-o', 'jsonl')
    & $bench @args 2>&1 | Tee-Object -FilePath $resultLog
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousEap
}
finally {
    Stop-Job $monitor -ErrorAction SilentlyContinue
    Remove-Job $monitor -Force -ErrorAction SilentlyContinue
    @(
        "finished_at=$((Get-Date).ToString('o'))"
        "exit_code=$exitCode"
        "result_dir=$resultDir"
    ) | Add-Content -Path $metaLog -Encoding ascii
}

Write-Output "RESULT_DIR=$resultDir"
Write-Output "EXIT_CODE=$exitCode"
exit $exitCode
