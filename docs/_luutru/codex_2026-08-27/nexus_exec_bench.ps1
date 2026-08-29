param([Parameter(Mandatory=$true)][string]$Command, [string]$Cwd='H:\LTT_LLM', [int]$Timeout=30, [string]$Reason='benchmark 131072')
$ErrorActionPreference = 'Stop'
$token = [IO.File]::ReadAllText("$env:USERPROFILE\.nexus\claude-code.token").Trim()
$headers = @{'X-Nexus-Protocol'='1'; Authorization="Bearer $token"}
$base = 'https://192.168.2.17:9444/api/v1/nodes/f8b24d88-6e3e-4719-8143-d5e83f68ed82/proxy/api/v1/exec'
$payload = @{command=$Command; shell='powershell'; cwd=$Cwd; timeout_s=$Timeout; reason=$Reason} | ConvertTo-Json -Compress
(Invoke-WebRequest -Uri $base -Method Post -Headers $headers -Body $payload -ContentType 'application/json' -SkipCertificateCheck).Content
