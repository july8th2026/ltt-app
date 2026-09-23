<#
.SYNOPSIS
    Dong bo ban sao luu DU LIEU ra mot dich off-site (Q28), giu N ban moi nhat.

.DESCRIPTION
    Vi sao ton tai: ngay 23/09/2026 dien tap khoi phuc chung minh ban sao luu dung
    duoc (RTO 24,01 s, du lieu day du), NHUNG toan bo ban sao nam tren CHINH may
    production (`D:\LTTBackups`). Mot o dia hong, mot dam chay, mot lan ransomware
    trung ca C: lan D: la mat CA du lieu LAN ban sao - khi do khong con gi de khoi
    phuc. `backup.ps1` da tinh toi dieu nay (tham so -BackupDir + loi canh bao
    "Cat mot ban NGOAI may nay") nhung dong bo off-site chua bao gio duoc dung.

    CHI dong bo ban DU LIEU (`ltt_data_*.zip`). KHONG BAO GIO dong bo ban
       secrets (`ltt_secrets_*.zip`).

       Ly do la thiet ke co chu y cua `backup.ps1` (H35.9): `app.env` giu
       LTT_TOKEN_ENCRYPTION_KEY va LTT_API_KEY_PEPPER, con dump giu ban MA cua
       token lan hash khoa API cua khach. Tach ra thi MOT ban sao bi lay cap
       khong du de doc gi. Day hai thu len cung mot tai khoan dam may la go bo
       chinh lop phong thu do: mot lan mat tai khoan Google = mat ca hai.

       Script nay TU CHOI chay neu -Nguon tro vao thu muc secrets.

.PARAMETER Nguon
    Thu muc chua ban sao du lieu. Mac dinh D:\LTTBackups.

.PARAMETER Dich
    Thu muc off-site. Vi du mot thu muc Google Drive da dong bo (G:\My Drive\...).

.PARAMETER Giu
    Giu bao nhieu ban moi nhat o DICH. Mac dinh 7.

.EXAMPLE
    pwsh -File deploy\windows\dong_bo_off_site.ps1 -Dich "G:\My Drive\LTTBackups"
#>
[CmdletBinding()]
param(
    [string]$Nguon = 'D:\LTTBackups',
    [Parameter(Mandatory = $true)][string]$Dich,
    [int]$Giu = 7,
    [switch]$ChayThu
)

$ErrorActionPreference = 'Stop'
$ketQua = [ordered]@{
    nguon = $Nguon; dich = $Dich; giu = $Giu
    da_chep = @(); bo_qua = @(); da_xoa = @(); loi = @()
}

# ---- 1. Chot an toan: khong bao gio dong bo secrets --------------------------
# Kiem TEN thu muc, khong kiem noi dung: mot thu muc rong ten '-secrets' hom nay
# co the day secrets ngay mai.
if ($Nguon -match '(?i)secret') {
    throw "TU CHOI: -Nguon '$Nguon' trong nhu thu muc secrets. Ban secrets KHONG duoc dong bo off-site cung ban du lieu (xem docstring)."
}
if ($Dich -match '(?i)secret') {
    throw "TU CHOI: -Dich '$Dich' trong nhu thu muc secrets."
}
if (-not (Test-Path -LiteralPath $Nguon)) { throw "Khong thay thu muc nguon: $Nguon" }

# ---- 2. Chi nhan dung mau ten cua backup.ps1 ---------------------------------
$mauTen = 'ltt_data_*.zip'
$banNguon = @(Get-ChildItem -LiteralPath $Nguon -Filter $mauTen -File -ErrorAction Stop |
              Sort-Object LastWriteTime -Descending)
if ($banNguon.Count -eq 0) { throw "Khong co tep nao khop '$mauTen' trong $Nguon" }

if (-not (Test-Path -LiteralPath $Dich)) {
    if ($ChayThu) { $ketQua.loi += "dich chua ton tai (chay thu nen khong tao)" }
    else { New-Item -ItemType Directory -Path $Dich -Force | Out-Null }
}

# ---- 3. Chep ban chua co, roi DOI CHIEU BAM ---------------------------------
# Chep xong ma khong doi chieu thi ta chi biet "co mot tep o do", khong biet no
# con doc duoc khong. Dung thu kho phat hien nhat: ban sao im lang hong.
foreach ($tep in ($banNguon | Select-Object -First $Giu)) {
    $dichTep = Join-Path $Dich $tep.Name
    if ((Test-Path -LiteralPath $dichTep) -and
        ((Get-Item -LiteralPath $dichTep).Length -eq $tep.Length)) {
        $ketQua.bo_qua += $tep.Name
        continue
    }
    if ($ChayThu) { $ketQua.da_chep += "$($tep.Name) (chay thu)"; continue }

    Copy-Item -LiteralPath $tep.FullName -Destination $dichTep -Force
    $bamNguon = (Get-FileHash -LiteralPath $tep.FullName -Algorithm SHA256).Hash
    $bamDich = (Get-FileHash -LiteralPath $dichTep -Algorithm SHA256).Hash
    if ($bamNguon -ne $bamDich) {
        Remove-Item -LiteralPath $dichTep -Force -ErrorAction SilentlyContinue
        $ketQua.loi += "$($tep.Name): bam LECH sau khi chep - da xoa ban hong o dich"
        continue
    }
    $ketQua.da_chep += $tep.Name
}

# ---- 4. Don ban cu o DICH ----------------------------------------------------
$banDich = @(Get-ChildItem -LiteralPath $Dich -Filter $mauTen -File -ErrorAction SilentlyContinue |
             Sort-Object LastWriteTime -Descending)
foreach ($cu in ($banDich | Select-Object -Skip $Giu)) {
    if ($ChayThu) { $ketQua.da_xoa += "$($cu.Name) (chay thu)"; continue }
    Remove-Item -LiteralPath $cu.FullName -Force
    $ketQua.da_xoa += $cu.Name
}

$ketQua | ConvertTo-Json -Depth 3
if ($ketQua.loi.Count -gt 0) { exit 1 }
exit 0
