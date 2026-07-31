<#
.SYNOPSIS
    Q28 - Cai lich sao luu tu dong sang O KHAC de chong mat du lieu.

.DESCRIPTION
    Dang ky mot Scheduled Task chay backup.ps1 moi ngay. Backup ghi sang
    -BackupDir (mac dinh D:\LTTBackups) - O VAT LY KHAC voi ban chay o C:,
    nen mot o hong hoac cai lai Windows khong mat ca hai.

    Task chay bang tai khoan SYSTEM (khong can dang nhap), quyen cao nhat, va
    doc duoc secrets\ (icacls da cap cho SYSTEM). Backup GOM CA secrets\app.env
    (chua LTT_TOKEN_ENCRYPTION_KEY) va pg_dump cua CSDL.

    Chay lai duoc nhieu lan: da co task thi ghi de cau hinh moi (-Force).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\deploy\windows\5-lich-backup.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\deploy\windows\5-lich-backup.ps1 -BackupDir E:\LTTBackups -Time 03:00
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$BackupDir = 'D:\LTTBackups',
    [string]$Time = '02:30',
    [string]$TaskName = 'LTTStudioBackup',
    [string]$BackupScript = ''
)

$ErrorActionPreference = 'Stop'
function Head($m) { Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Note($m) { Write-Host "  $m" -ForegroundColor Yellow }

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw 'Can quyen Administrator. Mo PowerShell bang Run as administrator.' }

# backup.ps1 cua BAN CHAY nam trong app\ (bi thay moi lan cap nhat, dung y muon).
if (-not $BackupScript) { $BackupScript = Join-Path $Root 'app\deploy\windows\backup.ps1' }
if (-not (Test-Path $BackupScript)) {
    throw "Khong tim thay backup.ps1: $BackupScript. Da chay setup\2-cai-dat.ps1 chua?"
}

Head 'Kiem o dich backup'
$backupDrive = (Split-Path -Qualifier $BackupDir)          # vd: D:
$rootDrive   = (Split-Path -Qualifier $Root)               # vd: C:
if (-not (Test-Path "$backupDrive\")) {
    throw "O $backupDrive khong ton tai. Chon -BackupDir tren mot o co that."
}
if ($backupDrive -eq $rootDrive) {
    Note "CANH BAO: -BackupDir ($BackupDir) CUNG o voi ban chay ($Root)."
    Note 'Mot o hong se mat ca ban chay lan backup. Nen tro sang o khac.'
}
if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null }
Ok "Backup se ghi vao $BackupDir"

# Siet ACL: ban backup CHUA secrets (app.env co LTT_TOKEN_ENCRYPTION_KEY) + dump
# toan bo CSDL. Chi SYSTEM va Administrators duoc doc. Dung SID (khong dung ten
# nhom) de dung tren ca Windows tieng Viet: *S-1-5-18 = SYSTEM,
# *S-1-5-32-544 = Administrators. /inheritance:r bo thua ke tu o cha (vd D:\ mo
# cho Users), roi cap lai dung 2 nhom nay -> Users/Everyone het quyen.
& icacls $BackupDir /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -eq 0) {
    Ok 'Da siet ACL thu muc backup (chi SYSTEM + Administrators doc duoc)'
} else {
    Note 'Khong siet duoc ACL thu muc backup - kiem quyen thu cong (icacls).'
}

Head 'Dang ky Scheduled Task'
$argLine = "-NonInteractive -ExecutionPolicy Bypass -File `"$BackupScript`" " +
           "-Root `"$Root`" -IncludeSecrets -BackupDir `"$BackupDir`""
$action  = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argLine
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
# SYSTEM: chay khong can dang nhap, doc duoc secrets\ (icacls cap cho SYSTEM).
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
# StartWhenAvailable: neu may tat luc den gio thi chay bu khi bat len.
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
             -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force `
    -Description 'LTT Studio - sao luu CSDL + secrets sang o khac (Q28)' | Out-Null
Ok "Da dang ky task '$TaskName' - chay moi ngay luc $Time"

Head 'Chay thu mot lan de kiem'
Start-ScheduledTask -TaskName $TaskName
Note 'Task dang chay nen. Doi vai giay roi kiem ket qua...'
Start-Sleep -Seconds 20
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "  LastRunTime   : $($info.LastRunTime)"
Write-Host "  LastTaskResult: $($info.LastTaskResult)  (0 = thanh cong)"
$newest = Get-ChildItem -Path $BackupDir -Filter 'ltt_data_*.zip' -ErrorAction SilentlyContinue |
          Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($newest) {
    Ok "Da tao ban backup: $($newest.FullName)"
} else {
    Note 'Chua thay file backup - task co the con chay hoac loi. Kiem:'
    Note "  Get-ScheduledTaskInfo -TaskName $TaskName"
    Note "  dir $BackupDir"
}

Write-Host ""
Write-Host ("-" * 62)
Write-Host "XONG. Lich backup hang ngay da bat." -ForegroundColor Green
Write-Host "  Xem task    : Get-ScheduledTaskInfo -TaskName $TaskName" -ForegroundColor Cyan
Write-Host "  Chay ngay   : Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Cyan
Write-Host "  Ban backup  : $BackupDir (giu 14 ban gan nhat)" -ForegroundColor Cyan
Write-Host ""
Write-Host "NHAC: dinh ky khoi phuc THU tu backup de chac chan phuc hoi duoc." -ForegroundColor Yellow
Write-Host "Giai doan thuong mai: them mot ban off-site (R2/may khac)." -ForegroundColor Yellow
