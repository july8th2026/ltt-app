param(
    [int]$Port = 8113
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$fixtureRoot = Join-Path $root "tmp\qualitylab-browser"
New-Item -ItemType Directory -Path $fixtureRoot -Force | Out-Null

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Output "PORT_IN_USE PID=$($listener.OwningProcess)"
    exit 2
}

$env:LTT_QUALITYLAB_BROWSER_TEST = "1"
$env:QUALITYLAB_FIXTURE_ROOT = $fixtureRoot
$stdout = Join-Path $fixtureRoot "server.out.log"
$stderr = Join-Path $fixtureRoot "server.err.log"
$proc = Start-Process python -ArgumentList @(
    "-m", "uvicorn", "tests.fixtures.qualitylab_server:app",
    "--host", "127.0.0.1", "--port", "$Port"
) -WorkingDirectory $root -WindowStyle Hidden `
  -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

Write-Output "PID=$($proc.Id)"
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-WebRequest -UseBasicParsing `
            "http://127.0.0.1:$Port/health/live" -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # Keep polling until the bounded timeout; stderr is printed on failure.
    }
}
if (-not $ready) {
    Get-Content $stderr -ErrorAction SilentlyContinue
    exit 3
}
Write-Output "READY=1"
