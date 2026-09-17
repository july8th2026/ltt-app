# khoi_dong_b.ps1 - chay do_b.py tren MAY B bang Scheduled Task SYSTEM + pythonw.
# Thuan ASCII. Chay QUA SSH tren may B:
#   powershell -NoProfile -ExecutionPolicy Bypass -File E:\AI\ltt_dual\bench_hang_cho\khoi_dong_b.ps1 -Do m1,m3_35,m5,m6 -HanPhut 90
# Tra ve ngay (khong cho). Theo doi: -XemTrangThai. Go task sau khi xong: -Go.
#
# Vi sao Task SYSTEM + pythonw: OpenSSH gom tien trinh con vao job object cua phien
# => phien dut la ca cay chet; python.exe duoi Task chet vi su kien console
# (0xC000013A). Xem memory may-b-duong-vao-va-du-phong.

param(
    [string]$Do = '',
    [double]$HanPhut = 0,
    [switch]$XemTrangThai,
    [switch]$Go,
    [string]$Goc = 'E:\AI\ltt_dual\bench_hang_cho',
    [string]$Python = 'C:\Python313\pythonw.exe',
    [string]$TenTask = 'LTT_BenchHangCho'
)
$ErrorActionPreference = 'Stop'
$Ra = Join-Path $Goc 'ket_qua'

if ($XemTrangThai) {
    $t = Get-ScheduledTask -TaskName $TenTask -ErrorAction SilentlyContinue
    if ($t) {
        $i = Get-ScheduledTaskInfo -TaskName $TenTask
        'task State=' + $t.State + ' LastTaskResult=' + $i.LastTaskResult + ' LastRunTime=' + $i.LastRunTime
    } else { 'khong co task ' + $TenTask }
    if (Test-Path "$Ra\trang_thai.json") { Get-Content "$Ra\trang_thai.json" }
    if (Test-Path "$Ra\nhat_ky.txt") { Get-Content "$Ra\nhat_ky.txt" -Tail 15 }
    Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" |
        ForEach-Object { 'llama-server pid ' + $_.ProcessId + ' port=' + ([regex]::Match($_.CommandLine, '--port (\d+)').Groups[1].Value) }
    exit 0
}

if ($Go) {
    $t = Get-ScheduledTask -TaskName $TenTask -ErrorAction SilentlyContinue
    if ($t -and $t.State -eq 'Running') { 'task dang chay - khong go. Muon dung: Stop-ScheduledTask + don_dep_b.ps1'; exit 1 }
    if ($t) { Unregister-ScheduledTask -TaskName $TenTask -Confirm:$false; 'da go ' + $TenTask }
    exit 0
}

if (-not $Do -or $HanPhut -le 0) { throw 'can -Do <m1,m3_35,...> va -HanPhut <so phut>' }
$cu = Get-ScheduledTask -TaskName $TenTask -ErrorAction SilentlyContinue
if ($cu -and $cu.State -eq 'Running') { throw 'task ' + $TenTask + ' dang chay - doi xong hoac dung truoc' }
New-Item -ItemType Directory -Force -Path $Ra | Out-Null

$doi = '"' + (Join-Path $Goc 'do_b.py') + '" --do ' + $Do + ' --han-phut ' + $HanPhut + ' --ra "' + $Ra + '"'
$act = New-ScheduledTaskAction -Execute $Python -Argument $doi -WorkingDirectory $Goc
# Tran cua Task Scheduler = ngan sach + 10 phut (do_b.py tu gac o ngan sach + 2 phut).
$set = New-ScheduledTaskSettingsSet -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes ([math]::Ceiling($HanPhut) + 10))
$set.AllowHardTerminate = $false
$pri = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName $TenTask -Action $act -Settings $set -Principal $pri -Force | Out-Null
Start-ScheduledTask -TaskName $TenTask
Start-Sleep -Seconds 5
$i = Get-ScheduledTaskInfo -TaskName $TenTask
'da khoi dong ' + $TenTask + ' Do=' + $Do + ' HanPhut=' + $HanPhut + ' State=' + (Get-ScheduledTask -TaskName $TenTask).State + ' LastTaskResult=' + $i.LastTaskResult
'ket qua: ' + $Ra + '\<phep>.jsonl ; theo doi: -XemTrangThai'
