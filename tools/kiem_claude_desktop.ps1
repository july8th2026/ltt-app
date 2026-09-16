param(
    [ValidateSet("ltt-llm-claude-compat", "ltt-llm-claude-compat-35")]
    [string]$Model = "ltt-llm-claude-compat",
    [string]$Prompt = "",
    [string]$Expected = "",
    [string]$ExecutablePath = "",
    [int]$TimeoutSeconds = 120,
    [string]$ReportPath = "",
    [switch]$InspectOnly,
    [switch]$RestoreOnly
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

function Find-ClaudeExecutable {
    if ($ExecutablePath -and (Test-Path -LiteralPath $ExecutablePath)) {
        return (Resolve-Path -LiteralPath $ExecutablePath).Path
    }
    $root = Join-Path $env:LOCALAPPDATA "AnthropicClaude"
    $items = Get-ChildItem -LiteralPath $root -Directory -Filter "app-*" |
        Sort-Object Name -Descending
    foreach ($item in $items) {
        $candidate = Join-Path $item.FullName "claude.exe"
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    throw "Claude Desktop executable was not found."
}

function Get-ClaudeProcesses([string]$InstallRoot) {
    return @(Get-Process -Name "claude" -ErrorAction SilentlyContinue | Where-Object {
        try { $_.Path -and $_.Path.StartsWith($InstallRoot, [StringComparison]::OrdinalIgnoreCase) }
        catch { $false }
    })
}

function Stop-ClaudeFully([string]$InstallRoot) {
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    do {
        $processes = Get-ClaudeProcesses $InstallRoot
        if ($processes.Count -eq 0) { return }
        $processes | Stop-Process -Force
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Claude Desktop processes did not stop fully."
}

function Find-All([System.Windows.Automation.AutomationElement]$Root) {
    return $Root.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition
    )
}

function Find-ByName(
    [System.Windows.Automation.AutomationElement]$Root,
    [string]$Name,
    [bool]$Contains = $false
) {
    foreach ($element in (Find-All $Root)) {
        try {
            $actual = [string]$element.Current.Name
            if (($Contains -and $actual.Contains($Name)) -or (!$Contains -and $actual -eq $Name)) {
                return $element
            }
        } catch { }
    }
    return $null
}

function Wait-Until([scriptblock]$Probe, [string]$Description, [int]$Seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        try {
            $value = & $Probe
            if ($null -ne $value -and $value -ne $false) { return $value }
        } catch { }
        Start-Sleep -Milliseconds 300
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Timed out waiting for $Description."
}

function Invoke-Element([System.Windows.Automation.AutomationElement]$Element) {
    $pattern = $null
    if ($Element.TryGetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern,
        [ref]$pattern
    )) {
        ([System.Windows.Automation.InvokePattern]$pattern).Invoke()
        return
    }
    if ($Element.TryGetCurrentPattern(
        [System.Windows.Automation.SelectionItemPattern]::Pattern,
        [ref]$pattern
    )) {
        ([System.Windows.Automation.SelectionItemPattern]$pattern).Select()
        return
    }
    if ($Element.TryGetCurrentPattern(
        [System.Windows.Automation.ExpandCollapsePattern]::Pattern,
        [ref]$pattern
    )) {
        ([System.Windows.Automation.ExpandCollapsePattern]$pattern).Expand()
        return
    }
    throw "The target UI element cannot be invoked."
}

function Find-ModelButton([System.Windows.Automation.AutomationElement]$Root) {
    foreach ($candidate in (Find-All $Root)) {
        try {
            $name = [string]$candidate.Current.Name
            if (!$name.Contains("LTT 3.8") -and !$name.Contains("LTT 3.5") -and
                !$name.Contains("ltt-llm-claude-compat")) { continue }
        } catch { continue }
        $pattern = $null
        if ($candidate.TryGetCurrentPattern(
            [System.Windows.Automation.ExpandCollapsePattern]::Pattern,
            [ref]$pattern
        )) { return $candidate }
    }
    return $null
}

function Find-ModelChoice(
    [System.Windows.Automation.AutomationElement]$Root,
    [string]$Name
) {
    $label = if ($Name -eq "ltt-llm-claude-compat") { "LTT 3.8" } else { "LTT 3.5" }
    foreach ($candidate in (Find-All $Root)) {
        try {
            $actual = [string]$candidate.Current.Name
            if (!$actual.Contains($label) -and $actual -ne $Name) { continue }
            $pattern = $null
            if ($candidate.TryGetCurrentPattern(
                [System.Windows.Automation.InvokePattern]::Pattern,
                [ref]$pattern
            ) -or $candidate.TryGetCurrentPattern(
                [System.Windows.Automation.SelectionItemPattern]::Pattern,
                [ref]$pattern
            )) { return $candidate }
        } catch { }
    }
    return $null
}

$exe = Find-ClaudeExecutable
$installRoot = Split-Path -Parent $exe
if ($RestoreOnly) {
    Stop-ClaudeFully $installRoot
    Start-Process -FilePath $exe -ArgumentList "--force-renderer-accessibility"
    Write-Output '{"restored":true}'
    exit 0
}
if (!$InspectOnly -and (!$Prompt -or !$Expected)) {
    throw "Prompt and Expected are required unless InspectOnly or RestoreOnly is used."
}
$report = [ordered]@{
    model = $Model
    inspect_only = [bool]$InspectOnly
    stopped_fully = $false
    reopened = $false
    chat_ready = $false
    models_visible = @()
    selected = $false
    sent = $false
    answered = $false
}

try {
    Stop-ClaudeFully $installRoot
    $report.stopped_fully = ((Get-ClaudeProcesses $installRoot).Count -eq 0)
    Start-Process -FilePath $exe -ArgumentList "--force-renderer-accessibility"

    $window = Wait-Until {
        $pids = @(Get-ClaudeProcesses $installRoot | ForEach-Object { $_.Id })
        $windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll(
            [System.Windows.Automation.TreeScope]::Children,
            [System.Windows.Automation.Condition]::TrueCondition
        )
        foreach ($candidate in $windows) {
            try {
                if ($pids -contains $candidate.Current.ProcessId -and
                    ([string]$candidate.Current.Name).Contains("Claude")) {
                    return $candidate
                }
            } catch { }
        }
        return $null
    } "Claude Desktop window" $TimeoutSeconds
    $report.reopened = $true

    $continue = Find-ByName $window "Continue"
    if ($continue) {
        Invoke-Element $continue
        Start-Sleep -Seconds 2
    }

    $chat = Find-ByName $window "Chat"
    if ($chat) {
        try { Invoke-Element $chat } catch { }
        Start-Sleep -Milliseconds 500
    }
    $editor = Wait-Until {
        $found = Find-ByName $window "Prompt"
        if ($found) { return $found }
        return Find-ByName $window "Write your prompt to Claude" $true
    } "Claude Chat prompt" 30
    $report.chat_ready = ($null -ne $editor)

    $newChat = Find-ByName $window "New chat"
    if (!$newChat) { $newChat = Find-ByName $window "New session" $true }
    if ($newChat) {
        try { Invoke-Element $newChat; Start-Sleep -Milliseconds 700 } catch { }
    }

    $modelButton = Wait-Until {
        Find-ModelButton $window
    } "model picker" 30
    Invoke-Element $modelButton
    Start-Sleep -Milliseconds 500

    $visible = @()
    foreach ($name in @("ltt-llm-claude-compat", "ltt-llm-claude-compat-35")) {
        if (Find-ModelChoice $window $name) { $visible += $name }
    }
    $report.models_visible = $visible
    if ($visible.Count -ne 2) { throw "Both LTT model routes are not visible in the picker." }

    $target = Find-ModelChoice $window $Model
    if (!$target) { throw "Requested model route is not visible." }
    Invoke-Element $target
    Start-Sleep -Milliseconds 600
    $modelButton = Find-ModelButton $window
    $selectedLabel = if ($Model -eq "ltt-llm-claude-compat") { "LTT 3.8" } else { "LTT 3.5" }
    $report.selected = ($null -ne $modelButton -and
        (([string]$modelButton.Current.Name).Contains($selectedLabel) -or
         ([string]$modelButton.Current.Name -eq $Model)))
    if (!$report.selected) { throw "The requested model was not selected." }

    if ($InspectOnly) {
        $report.answered = $true
    } else {
        $editor = Wait-Until {
            $found = Find-ByName $window "Prompt"
            if ($found) { return $found }
            return Find-ByName $window "Write your prompt to Claude" $true
        } "prompt editor" 30
        $valuePattern = $null
        if (!$editor.TryGetCurrentPattern(
            [System.Windows.Automation.ValuePattern]::Pattern,
            [ref]$valuePattern
        )) { throw "Prompt editor does not expose ValuePattern." }
        ([System.Windows.Automation.ValuePattern]$valuePattern).SetValue($Prompt)
        $editor.SetFocus()
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
        $report.sent = $true

        $answer = Wait-Until {
            Find-ByName $window $Expected $true
        } "expected model answer" $TimeoutSeconds
        $report.answered = ($null -ne $answer)
    }
} finally {
    $json = $report | ConvertTo-Json -Depth 4
    if ($ReportPath) {
        $full = [IO.Path]::GetFullPath($ReportPath)
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($full)) | Out-Null
        [IO.File]::WriteAllText($full, $json, (New-Object Text.UTF8Encoding($false)))
    }
    Write-Output $json
}

if (!$report.answered) { exit 1 }
