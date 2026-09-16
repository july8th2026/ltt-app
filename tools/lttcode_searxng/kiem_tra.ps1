# Health check for the private SearXNG behind POST /lttcode/search. ASCII only.
#   pwsh -File tools\lttcode_searxng\kiem_tra.ps1 [-Port 8888]
param([int]$Port = 8888, [string]$Query = 'python asyncio gather')
$ErrorActionPreference = 'Stop'
$report = [ordered]@{ port = $Port }

$listen = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { $_.LocalAddress } | Sort-Object -Unique)
$report.listen_addresses = $listen
$report.loopback_only = ($listen.Count -gt 0) -and -not ($listen | Where-Object { $_ -notin @('127.0.0.1', '::1') })

try {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/search?q=$([uri]::EscapeDataString($Query))&format=json" -TimeoutSec 20
  $report.http_ms = $sw.ElapsedMilliseconds
  $report.results = @($r.results).Count
  $report.engines_answered = @($r.results | ForEach-Object { $_.engine } | Sort-Object -Unique)
  $report.unresponsive = @($r.unresponsive_engines | ForEach-Object { "$($_[0]): $($_[1])" })
  $report.ok = $report.results -gt 0
} catch {
  $report.ok = $false
  $report.error = $_.Exception.Message
}
$task = Get-ScheduledTask -TaskName 'LTT SearXNG (LTTCODE search)' -ErrorAction SilentlyContinue
$report.task_state = if ($task) { "$($task.State)" } else { 'not registered' }
$report | ConvertTo-Json -Depth 4
