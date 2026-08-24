# kiem_tra.ps1 - nghiem thu cong VLM tu MAY A. CHAY TREN MAY A.
#
#     powershell -ExecutionPolicy Bypass -File llm_gateway\deploy\kiem_tra.ps1
#
# No chep hai tep nghiem thu sang may B roi chay chung o do. Dung ma nguon trong
# repo, khong dung ban da deploy - de "kiem tra" luon kiem CAI VUA SUA.
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! KHONG dat ten ham la `SSH`: PowerShell khong phan biet hoa thuong nen ben
#    trong ham `& ssh` se goi lai chinh no -> call depth overflow. Da dinh mot lan.

[CmdletBinding()]
param(
    [string]$MayB  = "192.168.2.66",
    [string]$User  = "lengo",
    [string]$Khoa  = "$env:USERPROFILE\.ssh\nexus_b",
    [string]$Goc   = "H:/LTT_LLM",
    [switch]$ChepMaTruoc                    # chay deploy.ps1 truoc khi nghiem thu
)

$ErrorActionPreference = "Stop"

function Buoc($s) { Write-Host ""; Write-Host "== $s" -ForegroundColor Cyan }
function Loi($s)  { Write-Host "  [LOI] $s" -ForegroundColor Red }

if ($ChepMaTruoc) {
    Buoc "Chep ma sang may B truoc"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "deploy.ps1") `
        -MayB $MayB -User $User -Khoa $Khoa -Goc $Goc -BoQuaVenv
    if ($LASTEXITCODE -ne 0) { Loi "deploy that bai"; exit 1 }
}

Buoc "Chep tep nghiem thu"
& scp.exe -i $Khoa -o BatchMode=yes -q (Join-Path $PSScriptRoot "nghiem_thu.py") `
    "${User}@${MayB}:$Goc/gateway/llm_gateway/deploy/nghiem_thu.py"
if ($LASTEXITCODE -ne 0) { Loi "scp nghiem_thu.py that bai"; exit 1 }
& scp.exe -i $Khoa -o BatchMode=yes -q (Join-Path $PSScriptRoot "chay_nghiem_thu.cmd") `
    "${User}@${MayB}:C:/Windows/Temp/chay_nghiem_thu.cmd"
if ($LASTEXITCODE -ne 0) { Loi "scp chay_nghiem_thu.cmd that bai"; exit 1 }

Buoc "Chay nghiem thu tren may B"
Write-Host "  (dung ca ba tang, chay 19 muc kiem, roi don sach - vai phut)" -ForegroundColor DarkGray
& ssh.exe -i $Khoa -o BatchMode=yes "$User@$MayB" 'C:\Windows\Temp\chay_nghiem_thu.cmd'
$rc = $LASTEXITCODE

Write-Host ""
if ($rc -eq 0) {
    Write-Host "== NGHIEM THU DAT" -ForegroundColor Green
} else {
    Write-Host "== NGHIEM THU HONG (rc=$rc) - doc muc [HONG] o tren" -ForegroundColor Red
}
exit $rc
