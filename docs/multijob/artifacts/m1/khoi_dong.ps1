# khoi_dong.ps1 -- THROWAWAY (spike M-1). Dang ky + chay Scheduled Task cho m1_bench.py.
# ASCII thuan (quy tac 2 CLAUDE.md). Bit console: pythonw + AllowHardTerminate=false.
$ErrorActionPreference = 'Stop'
$ten = 'LTT_Multijob_M1'
$act = New-ScheduledTaskAction -Execute 'C:\Python313\pythonw.exe' -Argument 'E:\AI\ltt_multijob_m1\m1_bench.py' -WorkingDirectory 'E:\AI\ltt_multijob_m1'
$set = New-ScheduledTaskSettingsSet -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 60)
$set.AllowHardTerminate = $false
$pri = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName $ten -Action $act -Settings $set -Principal $pri -Force | Out-Null
Start-ScheduledTask -TaskName $ten
Start-Sleep -Seconds 3
$i = Get-ScheduledTaskInfo -TaskName $ten
'task=' + $ten + ' LastRunTime=' + $i.LastRunTime + ' LastTaskResult=' + $i.LastTaskResult
