param(
    [string]$Root = 'H:\LTT_LLM',
    [int]$TargetTokens = 65536,
    [int]$Seed = 1
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

function Read-GatewayToken([string]$Path) {
    foreach ($line in [IO.File]::ReadAllLines($Path)) {
        if ($line.StartsWith('LTT_LLM_TOKEN=')) {
            return $line.Substring('LTT_LLM_TOKEN='.Length).Trim()
        }
    }
    return ''
}

function To-Utf8JsonBytes($Value) {
    $json = $Value | ConvertTo-Json -Depth 12 -Compress
    return ,([Text.Encoding]::UTF8.GetBytes($json))
}

function New-Messages([int]$Target, [int]$RunSeed) {
    $system = 'Read the complete context. Return only the two sentinel values.'
    $prefix = 'BEGIN_SENTINEL=LTT-Q4-ALPHA-314159`n'
    $suffix = '`nEND_SENTINEL=LTT-Q4-OMEGA-271828`nReturn the two sentinel values.'
    # Use varied identifiers so the Qwen tokenizer does not collapse a
    # repeated line. The measured density matches the gateway's 2.5 estimate.
    $targetChars = [Math]::Max(1000, [int][Math]::Floor($Target * 2.5) - 200)
    $builder = New-Object Text.StringBuilder
    $index = 0
    while ($builder.Length -lt $targetChars) {
        [void]$builder.AppendFormat(
            'const item_{0:D6}_{2:D6} = calculate(value_{0:D6}, {1}); // preserve ordered context`n',
            $index, (($index + $RunSeed) % 997), $RunSeed)
        $index++
    }
    $filler = $builder.ToString().Substring(0, $targetChars)
    return @(
        @{role = 'system'; content = $system}
        @{role = 'user'; content = ($prefix + $filler + $suffix)}
    )
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$resultDir = Join-Path $Root ("benchmarks\q4-api-canary-" + $stamp)
New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
$gpuLog = Join-Path $resultDir 'gpu.csv'
$resultLog = Join-Path $resultDir 'result.json'
$metaLog = Join-Path $resultDir 'metadata.txt'
$messages = New-Messages $TargetTokens $Seed
$token = Read-GatewayToken 'C:\ProgramData\LTTLlm\gateway.env'
$headers = @{}
if ($token) { $headers.Authorization = "Bearer $token" }
$request = @{
    model = 'qwen38-api'
    messages = $messages
    max_tokens = 256
    reasoning_effort = 'low'
    temperature = 0
    stream = $false
}

'timestamp,temp_c,fan_pct,gpu_pct,vram_used_mib,vram_free_mib,power_w' |
    Set-Content -Path $gpuLog -Encoding ascii
$monitor = Start-Job -ArgumentList $gpuLog -ScriptBlock {
    param($Path)
    while ($true) {
        $sample = & nvidia-smi `
            --query-gpu=timestamp,temperature.gpu,fan.speed,utilization.gpu,memory.used,memory.free,power.draw `
            --format=csv,noheader,nounits
        Add-Content -Path $Path -Value $sample -Encoding ascii
        Start-Sleep -Seconds 1
    }
}

$watch = [Diagnostics.Stopwatch]::StartNew()
$response = $null
try {
    $response = Invoke-WebRequest -UseBasicParsing `
        -Uri 'http://127.0.0.1:8299/v1/chat/completions' `
        -Method Post -Headers $headers -Body (To-Utf8JsonBytes $request) `
        -ContentType 'application/json; charset=utf-8' -TimeoutSec 360
    $watch.Stop()
}
finally {
    Stop-Job $monitor -ErrorAction SilentlyContinue
    Remove-Job $monitor -Force -ErrorAction SilentlyContinue
}

$parsed = $response.Content | ConvertFrom-Json
$content = [string]$parsed.choices[0].message.content
$qualityPass = $content -match 'LTT-Q4-ALPHA-314159' -and $content -match 'LTT-Q4-OMEGA-271828'
$samples = Import-Csv $gpuLog
$safeResult = [ordered]@{
    result = if ($qualityPass) {'PASS'} else {'FAIL'}
    http_status = [int]$response.StatusCode
    elapsed_seconds = [Math]::Round($watch.Elapsed.TotalSeconds, 3)
    target_estimated_input_tokens = $TargetTokens
    seed = $Seed
    prompt_chars = ($messages | ForEach-Object {$_.content.Length} | Measure-Object -Sum).Sum
    finish_reason = [string]$parsed.choices[0].finish_reason
    usage_prompt_tokens = [int]$parsed.usage.prompt_tokens
    usage_completion_tokens = [int]$parsed.usage.completion_tokens
    gpu_samples = $samples.Count
    gpu_max_pct = [double](($samples | Measure-Object -Property gpu_pct -Maximum).Maximum)
    vram_max_mib = [double](($samples | Measure-Object -Property vram_used_mib -Maximum).Maximum)
    temp_max_c = [double](($samples | Measure-Object -Property temp_c -Maximum).Maximum)
    fan_max_pct = [double](($samples | Measure-Object -Property fan_pct -Maximum).Maximum)
    power_max_w = [double](($samples | Measure-Object -Property power_w -Maximum).Maximum)
    result_dir = $resultDir
}
$safeResult | ConvertTo-Json -Depth 5 | Set-Content -Path $resultLog -Encoding ascii
@(
    "target_estimated_input_tokens=$TargetTokens"
    "seed=$Seed"
    "usage_prompt_tokens=$($safeResult.usage_prompt_tokens)"
    "quality_pass=$qualityPass"
) | Set-Content -Path $metaLog -Encoding ascii
$safeResult | ConvertTo-Json -Depth 5
if (-not $qualityPass) { exit 2 }
