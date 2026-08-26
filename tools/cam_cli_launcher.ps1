param(
    [Parameter(Mandatory=$true)]
    [string]$Exe
)

# ASCII only. This script is called by cam_cli.bat inside the installer.
$ErrorActionPreference = 'Stop'
$isConsolePackage = [IO.Path]::GetFileName($Exe) -like '*-Console.exe'

function Run-Core([string[]]$CoreArgs, [switch]$NeedsKey) {
    $script:LastRunCode = 1
    $resultFile = Join-Path $env:TEMP ("ltt-cam-cli-" + [guid]::NewGuid().ToString('N') + '.txt')
    $oldOutput = $env:LTT_CAM_CLI_OUTPUT
    $oldKey = $env:LTT_API_KEY
    try {
        if ($NeedsKey) {
            $secure = Read-Host 'Paste API key (input is hidden)' -AsSecureString
            $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
            try {
                $env:LTT_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
            } finally {
                [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
            }
        }
        if ([IO.Path]::GetFileName($Exe) -like '*-Console.exe') {
            & $Exe @CoreArgs
            $script:LastRunCode = $LASTEXITCODE
        } else {
            $env:LTT_CAM_CLI_OUTPUT = $resultFile
            $p = Start-Process -FilePath $Exe -ArgumentList $CoreArgs -Wait -PassThru -WindowStyle Hidden
            $script:LastRunCode = $p.ExitCode
            if (Test-Path -LiteralPath $resultFile) {
                Get-Content -LiteralPath $resultFile | ForEach-Object { Write-Host $_ }
            } else {
                Write-Host '[ERROR] The packaged tool did not write a result.'
            }
        }
    } finally {
        $env:LTT_CAM_CLI_OUTPUT = $oldOutput
        $env:LTT_API_KEY = $oldKey
        if (Test-Path -LiteralPath $resultFile) {
            Remove-Item -LiteralPath $resultFile -Force
        }
    }
}

while ($true) {
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' LTT Studios - connect coding tools'
    Write-Host '============================================================'
    Write-Host ' 1. Show actual status'
    Write-Host ' 2. Connect selected tools'
    Write-Host ' 3. Verify with real API calls'
    Write-Host ' 4. Remove LTT configuration'
    if (-not $isConsolePackage) { Write-Host ' 5. Open graphical interface' }
    Write-Host ' Enter. Exit'
    $choice = Read-Host 'Choose'

    if ([string]::IsNullOrWhiteSpace($choice)) { exit 0 }
    if ($choice -eq '1') { Run-Core @('xem'); continue }
    if ($choice -eq '3') { Run-Core @('kiem'); continue }
    if ($choice -eq '4') { Run-Core @('go'); continue }
    if ($choice -eq '5' -and -not $isConsolePackage) { Start-Process -FilePath $Exe; continue }
    if ($choice -ne '2') { Write-Host 'Invalid choice.'; continue }

    Write-Host ''
    Write-Host 'Codex mode:'
    Write-Host ' 0. Skip Codex'
    Write-Host ' 1. CLI profile (safe default)'
    Write-Host ' 2. VS Code extension + default Codex CLI'
    $codex = Read-Host 'Choose 0-2 [1]'
    if ([string]::IsNullOrWhiteSpace($codex)) { $codex = '1' }

    $args = @('cam')
    if ($codex -eq '1') { $args += @('--muc', 'codex-cli') }
    elseif ($codex -eq '2') { $args += @('--muc', 'codex-vscode') }
    elseif ($codex -ne '0') { Write-Host 'Invalid Codex mode.'; continue }

    $claudeCli = Read-Host 'Connect Claude Code CLI? [Y]'
    if ($claudeCli -notmatch '^[Nn]') { $args += @('--muc', 'claude-cli') }
    $claudeVs = Read-Host 'Connect Claude Code in VS Code? [Y]'
    if ($claudeVs -notmatch '^[Nn]') { $args += @('--muc', 'claude-vscode') }
    $desktop = Read-Host 'Connect Claude Desktop? [Y]'
    if ($desktop -notmatch '^[Nn]') { $args += @('--muc', 'claude-desktop') }
    $global = Read-Host 'Also write ~/.claude/settings.json? [N]'
    if ($global -match '^[Yy]') { $args += '--toan-cuc' }

    if ($args.Count -eq 1) { Write-Host 'No target selected.'; continue }
    Run-Core $args -NeedsKey
}
