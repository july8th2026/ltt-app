# chay_multiproc_nang_quyen.ps1 - LOP TRONG, chay MOT buoc gate can doc secrets.
#
# Buoc `bat bien da tien trinh` (tools/check_multiproc.py) phai doc
# C:\LTTPlatform\secrets\ de lay chuoi ket noi CSDL test. Thu muc do siet ve
# SYSTEM + Administrators tu 27/08 (hang muc W1.5) - do la CO Y, dung icacls.
#
# !! VI SAO TACH HAI LOP, giong deploy_nang_quyen.ps1 (AGENTS.md 9.3):
#    `Start-Process` KHONG cho dung `-Verb RunAs` cung luc voi chuyen huong
#    stdout/stderr. Nen:
#      lop NGOAI -> nang quyen, KHONG chuyen huong
#      lop TRONG (tep nay) -> da co quyen, duoc phep ghi ket qua ra tep
#
# Ghi ket qua ra C:\LTTPlatform\logs\multiproc-*.ket.txt de lop ngoai doc.

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logDir = "C:\LTTPlatform\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force $logDir | Out-Null }
$ket = Join-Path $logDir "multiproc-$stamp.ket.txt"
$out = Join-Path $logDir "multiproc-$stamp.out.log"

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($id)
$admin = $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

"BAT DAU=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $ket -Encoding ascii
"ADMIN=$admin" | Out-File -FilePath $ket -Encoding ascii -Append
"OUT=$out" | Out-File -FilePath $ket -Encoding ascii -Append

if (-not $admin) {
    # Fail closed: khong co quyen thi NOI RA, dung chay roi bao xanh.
    "EXITCODE=126" | Out-File -FilePath $ket -Encoding ascii -Append
    "LY_DO=khong co quyen Administrator - lop ngoai phai dung -Verb RunAs" |
        Out-File -FilePath $ket -Encoding ascii -Append
    exit 126
}

Set-Location "D:\LTTSTUDIOSAPP"
& python tools\check_multiproc.py *> $out
$rc = $LASTEXITCODE

"EXITCODE=$rc" | Out-File -FilePath $ket -Encoding ascii -Append
"KET THUC=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $ket -Encoding ascii -Append
exit $rc
