# khoi_dong.ps1 -- Task 0.4. Dang ky, chay, doi xong, roi go mot Scheduled
# Task SYSTEM chay bench.py bang pythonw (khuon docs/multijob/artifacts/m1/
# khoi_dong.ps1). ASCII thuan (quy tac 2 CLAUDE.md).
#
# Vi sao SYSTEM + pythonw thay vi chi chay python truc tiep qua SSH: mot lan
# chay c1 5 lap thi khong can, nhung kich ban "nap" (cho TTL unload roi do nap
# lanh) hay mot lo dai co the vuot thoi gian mot phien SSH tien loi giu duoc,
# va Task Scheduler song doc lap voi ket noi SSH. pythonw khong mo console
# (tranh treo ben duoi mot dich vu/tac vu nen).
#
# Dung: powershell -NoProfile -ExecutionPolicy Bypass -File khoi_dong.ps1 `
#         -KichBan c1 -Lan 5 -Ra E:\AI\ltt_dual\bench\ketqua_c1.jsonl

param(
    [string]$KichBan = 'c1',
    [int]$Lan = 5,
    [string]$Model = 'qwen38-api',
    [int]$Cong = 8280,
    [string]$Uuid = 'GPU-26623278-4fa5-82db-4306-237651b03e78',
    [string]$Ra = 'E:\AI\ltt_dual\bench\ketqua.jsonl',
    [string]$Python = 'C:\Python313\pythonw.exe',
    [string]$Script = 'E:\AI\ltt_dual\bench\bench.py',
    [string]$TenTask = 'LTT_Dual_Bench',
    [int]$HanPhut = 30
)

$ErrorActionPreference = 'Stop'

$doi = '"' + $Script + '" --kich-ban ' + $KichBan + ' --lan ' + $Lan + ' --model ' + $Model + ' --cong ' + $Cong + ' --uuid ' + $Uuid + ' --ra "' + $Ra + '"'

$act = New-ScheduledTaskAction -Execute $Python -Argument $doi -WorkingDirectory (Split-Path $Script)
$set = New-ScheduledTaskSettingsSet -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes $HanPhut)
$set.AllowHardTerminate = $false
$pri = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $TenTask -Action $act -Settings $set -Principal $pri -Force | Out-Null
Start-ScheduledTask -TaskName $TenTask
Start-Sleep -Seconds 3
$i = Get-ScheduledTaskInfo -TaskName $TenTask
'task=' + $TenTask + ' LastRunTime=' + $i.LastRunTime + ' LastTaskResult=' + $i.LastTaskResult

# Cho task chuyen khoi trang thai Running (danh dau xong hoac bi cat o han),
# roi go task khoi Task Scheduler -- khong de rac lai tren may B.
for ($n = 0; $n -lt ($HanPhut * 30); $n++) {
    $trang_thai = (Get-ScheduledTask -TaskName $TenTask).State
    if ($trang_thai -ne 'Running') { break }
    Start-Sleep -Seconds 2
}
$i2 = Get-ScheduledTaskInfo -TaskName $TenTask
'xong. State cuoi=' + $trang_thai + ' LastTaskResult=' + $i2.LastTaskResult

Unregister-ScheduledTask -TaskName $TenTask -Confirm:$false
'da go task ' + $TenTask
