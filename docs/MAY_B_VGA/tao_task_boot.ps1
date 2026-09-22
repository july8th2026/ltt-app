# Tac vu SYSTEM luc khoi dong: dat offset nho qua NVML (khong can dang nhap)
$a = New-ScheduledTaskAction -Execute 'C:\Tools\ModCard\venv\Scripts\python.exe' -Argument 'C:\Tools\ModCard\dat_offset.py 1500 2000' -WorkingDirectory 'C:\Tools\ModCard'
$t = New-ScheduledTaskTrigger -AtStartup; $t.Delay = 'PT60S'
$p = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$s = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName 'LTT_ModCard_NVML_KhoiDong' -Action $a -Trigger $t -Principal $p -Settings $s -Description 'Mod card may B: 3090 nho +750, 5060 Ti nho +1000 (NVML 1500/2000). Lui: xoa tac vu + chay dat_offset.py 0 0. Chi tiet: C:\Users\Thang Tuong\.claude\ltt\mod_card_may_b\KET_QUA.md (may A)' -Force | Out-Null
Start-ScheduledTask 'LTT_ModCard_NVML_KhoiDong'; Start-Sleep 8
"ket qua tac vu: " + (Get-ScheduledTaskInfo 'LTT_ModCard_NVML_KhoiDong').LastTaskResult
Get-Content C:\Tools\ModCard\dat_offset.log -Tail 6
