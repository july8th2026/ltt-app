param(
    [string]$Root = 'H:\LTT_LLM',
    [int]$TargetTokens = 89950
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
    # Unary comma keeps byte[] as one pipeline object in Windows PowerShell 5.1.
    return ,([Text.Encoding]::UTF8.GetBytes($json))
}

function Get-ExactInputTokens([array]$Messages) {
    $body = @{model = 'qwen38-api'; messages = $Messages}
    $response = Invoke-RestMethod -UseBasicParsing `
        -Uri 'http://127.0.0.1:8281/v1/chat/completions/input_tokens' `
        -Method Post -Body (To-Utf8JsonBytes $body) `
        -ContentType 'application/json; charset=utf-8' -TimeoutSec 120
    return [int]$response.input_tokens
}

function New-Messages([string]$Filler) {
    $system = @'
Read the complete context. Return only this exact ASCII line, with no explanation:
LTT-Q111-ALPHA-314159|LTT-Q111-OMEGA-271828
'@
    $user = @"
BEGIN_SENTINEL=LTT-Q111-ALPHA-314159
$Filler
END_SENTINEL=LTT-Q111-OMEGA-271828
Now return the two sentinel values in the exact format requested by the system message.
"@
    return @(
        @{role = 'system'; content = $system.Trim()}
        @{role = 'user'; content = $user}
    )
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$resultDir = Join-Path $Root ("benchmarks\q111-api-90k-" + $stamp)
New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
$gpuLog = Join-Path $resultDir 'gpu.csv'
$resultLog = Join-Path $resultDir 'result.json'
$metaLog = Join-Path $resultDir 'metadata.txt'

$builder = New-Object Text.StringBuilder
$index = 0
while ($builder.Length -lt 224000) {
    [void]$builder.AppendFormat(
        "const item_{0:D6} = calculate(value_{0:D6}, {1}); // preserve ordered context`n",
        $index, ($index % 997))
    $index++
}
$allFiller = $builder.ToString()

# Find the longest prefix whose exact tokenizer count is at or below the target.
$low = 190000
$high = [Math]::Min(224000, $allFiller.Length)
$bestLength = $low
$bestTokens = 0
while ($low -le $high) {
    $mid = [int][Math]::Floor(($low + $high) / 2)
    $messages = New-Messages $allFiller.Substring(0, $mid)
    $tokens = Get-ExactInputTokens $messages
    if ($tokens -le $TargetTokens) {
        $bestLength = $mid
        $bestTokens = $tokens
        $low = $mid + 1
    } else {
        $high = $mid - 1
    }
}

$messages = New-Messages $allFiller.Substring(0, $bestLength)
$exactTokens = Get-ExactInputTokens $messages
$estimatedTokens = 0
foreach ($message in $messages) {
    if ($message.content.Length -gt 0) {
        $estimatedTokens += [int][Math]::Floor($message.content.Length / 2.5) + 1
    }
}
if ($exactTokens -gt $TargetTokens -or $estimatedTokens -gt 90000) {
    throw "Unsafe calibrated payload: exact=$exactTokens estimated=$estimatedTokens"
}

$token = Read-GatewayToken 'C:\ProgramData\LTTLlm\gateway.env'
$headers = @{}
if ($token) {
    $headers.Authorization = "Bearer $token"
}

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
$expected = 'LTT-Q111-ALPHA-314159|LTT-Q111-OMEGA-271828'
$qualityPass = $content.Trim() -eq $expected

$samples = Import-Csv $gpuLog
$maxGpu = ($samples | Measure-Object -Property gpu_pct -Maximum).Maximum
$maxVram = ($samples | Measure-Object -Property vram_used_mib -Maximum).Maximum
$maxTemp = ($samples | Measure-Object -Property temp_c -Maximum).Maximum
$maxFan = ($samples | Measure-Object -Property fan_pct -Maximum).Maximum
$maxPower = ($samples | Measure-Object -Property power_w -Maximum).Maximum

$safeResult = [ordered]@{
    result = if ($qualityPass) {'PASS'} else {'FAIL'}
    http_status = [int]$response.StatusCode
    elapsed_seconds = [Math]::Round($watch.Elapsed.TotalSeconds, 3)
    exact_input_tokens = $exactTokens
    gateway_estimated_tokens = $estimatedTokens
    prompt_chars = ($messages | ForEach-Object {$_.content.Length} | Measure-Object -Sum).Sum
    finish_reason = [string]$parsed.choices[0].finish_reason
    content = $content
    usage_prompt_tokens = [int]$parsed.usage.prompt_tokens
    usage_completion_tokens = [int]$parsed.usage.completion_tokens
    gpu_samples = $samples.Count
    gpu_max_pct = [double]$maxGpu
    vram_max_mib = [double]$maxVram
    temp_max_c = [double]$maxTemp
    fan_max_pct = [double]$maxFan
    power_max_w = [double]$maxPower
    result_dir = $resultDir
}
$safeResult | ConvertTo-Json -Depth 5 | Set-Content -Path $resultLog -Encoding ascii
@(
    "started_at=$((Get-Date).AddSeconds(-$watch.Elapsed.TotalSeconds).ToString('o'))"
    "finished_at=$((Get-Date).ToString('o'))"
    "target_tokens=$TargetTokens"
    "exact_input_tokens=$exactTokens"
    "gateway_estimated_tokens=$estimatedTokens"
    "quality_pass=$qualityPass"
) | Set-Content -Path $metaLog -Encoding ascii

$safeResult | ConvertTo-Json -Depth 5
if (-not $qualityPass) {
    exit 2
}
