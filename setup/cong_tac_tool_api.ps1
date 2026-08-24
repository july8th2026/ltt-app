# cong_tac_tool_api.ps1 - bat/tat mot tool tren API cong khai (`LTT_PUBLIC_API_TOOLS`).
#
#     powershell -ExecutionPolicy Bypass -File .\setup\cong_tac_tool_api.ps1 -Tool image.ltt -Bat
#     powershell -ExecutionPolicy Bypass -File .\setup\cong_tac_tool_api.ps1 -Tool image.ltt -Tat
#     powershell -ExecutionPolicy Bypass -File .\setup\cong_tac_tool_api.ps1            # chi xem
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! VI SAO CAN MOT SCRIPT CHO MOT DONG TEXT.
#
#    `LTT_PUBLIC_API_TOOLS` la cong tac cuoi cung cua fail-closed (Q92). Sua no
#    bang tay co ba cach hong, va ca ba deu IM LANG:
#
#      1. Trinh soan thao chen BOM  -> `json.load()` vo o cho khac, `/health/ready`
#         tra 503 trong khi dich vu van chay. Loi nay DA LAM SAP PRODUCTION.
#      2. Go de len mot dong khac   -> mat mot tool dang phuc vu, khong ai biet
#         cho toi khi co khach goi.
#      3. Sua xong roi restart      -> KHONG AN GI. nssm nuong bien moi truong vao
#         dang ky dich vu luc CAI (`AppEnvironmentExtra`); tien trinh doc
#         `os.environ`, khong doc lai app.env. Phai chay `nap_lai_env.ps1`.
#
#    Script nay lam dung mot viec, sao luu truoc, va IN RA lenh nap lai o cuoi.
#
# !! KHONG IN GIA TRI BI MAT NAO. No chi doc/ghi dung mot dong, va chi in dong do.

[CmdletBinding()]
param(
    [string]$Tool,
    [switch]$Bat,
    [switch]$Tat,
    [string]$Env = 'C:\LTTPlatform\secrets\app.env'
)

$ErrorActionPreference = 'Stop'
$KHOA = 'LTT_PUBLIC_API_TOOLS='

if (-not (Test-Path -LiteralPath $Env)) { Write-Host "Khong thay $Env"; exit 1 }

$bytes = [IO.File]::ReadAllBytes($Env)
if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    Write-Host "app.env dang co BOM - DUNG LAI. Khong tu sua tep bi mat." -ForegroundColor Red
    exit 2
}
$txt = [Text.Encoding]::UTF8.GetString($bytes)
$nl  = if ($txt -match "`r`n") { "`r`n" } else { "`n" }
$dong = $txt -split "`r?`n"

$i = -1
for ($k = 0; $k -lt $dong.Count; $k++) { if ($dong[$k].StartsWith($KHOA)) { $i = $k; break } }
if ($i -lt 0) { Write-Host "Khong thay dong $KHOA - dung lai." -ForegroundColor Red; exit 3 }

$cu = $dong[$i].Substring($KHOA.Length).Trim()
$co = @($cu -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
Write-Host "Dang mo: $(if ($co.Count) { $co -join ', ' } else { '(khong co tool nao)' })"

if (-not $Tool) { exit 0 }
if (-not ($Bat -or $Tat)) { Write-Host "Thieu -Bat hoac -Tat."; exit 4 }
if ($Bat -and $Tat)       { Write-Host "-Bat va -Tat loai tru nhau."; exit 4 }

if ($Bat) {
    if ($co -contains $Tool) { Write-Host "  $Tool da bat - khong doi gi."; exit 0 }
    $moi = @($co) + $Tool
} else {
    if (-not ($co -contains $Tool)) { Write-Host "  $Tool von da tat - khong doi gi."; exit 0 }
    $moi = @($co | Where-Object { $_ -ne $Tool })
}

$bak = "$Env.bak-congtac"
if (-not (Test-Path -LiteralPath $bak)) {
    [IO.File]::WriteAllBytes($bak, $bytes)
    Write-Host "  sao luu: $bak"
}

$dong[$i] = $KHOA + ($moi -join ',')
# !! UTF8Encoding($false) = KHONG BOM. Dung Out-File/Set-Content -Encoding utf8 la
#    PowerShell 5.1 chen BOM - quy tac 1 cua CLAUDE.md, va no da lam sap production.
[IO.File]::WriteAllText($Env, ($dong -join $nl), (New-Object Text.UTF8Encoding($false)))
Write-Host "  moi: $($moi -join ', ')" -ForegroundColor Green

Write-Host ""
Write-Host "CHUA CO TAC DUNG. nssm nuong bien moi truong luc cai, nen phai nap lai:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File .\setup\nap_lai_env.ps1"
