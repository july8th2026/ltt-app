param(
    [Parameter(Mandatory=$true)][string]$MachineBHost,
    [Parameter(Mandatory=$true)][string]$MachineBUser,
    [Parameter(Mandatory=$true)][string]$SshKeyPath,
    [Parameter(Mandatory=$true)][string]$KnownHostsPath,
    [Parameter(Mandatory=$true)][string]$Destination,
    [string]$ScpPath = "$env:SystemRoot\System32\OpenSSH\scp.exe"
)
$ErrorActionPreference = 'Stop'
$names = @(
    'runtime-inventory.json',
    'runtime-health.json',
    'runtime-capabilities.json',
    'runtime-collector-status.json'
)

foreach ($file in @($SshKeyPath, $KnownHostsPath, $ScpPath)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw 'Required Machine B transport file is unavailable'
    }
}
if ($MachineBHost -notmatch '^[A-Za-z0-9.-]{1,253}$' -or
    $MachineBUser -notmatch '^[A-Za-z0-9._-]{1,64}$') {
    throw 'Invalid Machine B SSH identity'
}

$destinationPath = [IO.Path]::GetFullPath($Destination)
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
if ($destinationPath.StartsWith($repoRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Machine B runtime must live outside the source repository'
}
$parent = Split-Path $destinationPath -Parent
if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
    New-Item -ItemType Directory -Path $parent | Out-Null
}
$stage = Join-Path $parent ('.machine-b-stage-' + [guid]::NewGuid().ToString('N'))
$previous = $destinationPath + '.previous'
New-Item -ItemType Directory -Path $stage | Out-Null

try {
    foreach ($name in $names) {
        $remote = '{0}@{1}:H:/PROXMOX/06-HIEN-TRANG/{2}' -f $MachineBUser,$MachineBHost,$name
        $scpArgs = @('-q', '-i', $SshKeyPath, '-o', 'BatchMode=yes', '-o',
            'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes')
        $defaultKnownHosts = Join-Path $env:USERPROFILE '.ssh\known_hosts'
        if ([IO.Path]::GetFullPath($KnownHostsPath) -ne
            [IO.Path]::GetFullPath($defaultKnownHosts)) {
            if ($KnownHostsPath.Contains(' ')) {
                throw 'A non-default known_hosts path cannot contain spaces'
            }
            $scpArgs += @('-o', "UserKnownHostsFile=$KnownHostsPath")
        }
        $scpArgs += @($remote, (Join-Path $stage $name))
        & $ScpPath @scpArgs
        if ($LASTEXITCODE -ne 0) { throw 'Machine B runtime transfer failed' }
    }
    $docs = @{}
    foreach ($name in $names) {
        $path = Join-Path $stage $name
        if ((Get-Item -LiteralPath $path).Length -gt 4MB) {
            throw 'Machine B runtime artifact exceeded safe size'
        }
        $docs[$name] = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    }
    $generations = @(@(
        $docs['runtime-inventory.json'].generated_at,
        $docs['runtime-health.json'].generated_at,
        $docs['runtime-capabilities.json'].generated_at,
        $docs['runtime-collector-status.json'].output_generation
    ) | Select-Object -Unique)
    $status = $docs['runtime-collector-status.json']
    if ($generations.Count -ne 1 -or $status.result -ne 'success' -or
        [int]$status.exit_code -notin @(0,1,2)) {
        throw 'Machine B runtime bundle is not one successful generation'
    }

    if (Test-Path -LiteralPath $previous) {
        $resolvedPrevious = [IO.Path]::GetFullPath($previous)
        if ($resolvedPrevious -ne ([IO.Path]::GetFullPath($destinationPath + '.previous')) -or
            (Split-Path $resolvedPrevious -Parent) -ne $parent) {
            throw 'Previous runtime path escaped destination parent'
        }
        Remove-Item -LiteralPath $resolvedPrevious -Recurse -Force
    }
    if (Test-Path -LiteralPath $destinationPath) {
        Move-Item -LiteralPath $destinationPath -Destination $previous
    }
    try {
        Move-Item -LiteralPath $stage -Destination $destinationPath
    } catch {
        if ((-not (Test-Path -LiteralPath $destinationPath)) -and
            (Test-Path -LiteralPath $previous)) {
            Move-Item -LiteralPath $previous -Destination $destinationPath
        }
        throw
    }
    Write-Output ('MACHINE_B_RUNTIME_SYNC_PASS generation={0}' -f $generations[0])
} finally {
    if (Test-Path -LiteralPath $stage) {
        $resolvedStage = [IO.Path]::GetFullPath($stage)
        if ((Split-Path $resolvedStage -Parent) -eq $parent -and
            (Split-Path $resolvedStage -Leaf) -like '.machine-b-stage-*') {
            Remove-Item -LiteralPath $resolvedStage -Recurse -Force
        }
    }
}
