# do_voice_co_bi_mat.ps1 - chay MOT cong cu do cua LTT VOICE voi bi mat da nap.
#
# Vi sao co tep nay:
#   Cong cu do cua LTT VOICE can LTT_VOICE_SIDECAR_TOKEN (goi sidecar 8120) hoac
#   LTT_DATABASE_URL (doc kho giong). Hai chuoi ay nam trong
#   C:\LTTPlatform\secrets\app.env. Phien Claude bi chan doc tep bi mat - dung,
#   va khong nen go. Nen doi thao tac ay ra mot vo boc:
#
#     - nap DUNG hai bien, khong nap ca tep;
#     - KHONG BAO GIO in gia tri ra man hinh hay log;
#     - chi cho chay cong cu nam trong danh sach CHI DOC duoi day;
#     - moi thu khac bi tu choi, ke ca khi go dung duong dan.
#
# Dung:
#     powershell -ExecutionPolicy Bypass -File .\tools\do_voice_co_bi_mat.ps1 soat-giong
#     powershell -ExecutionPolicy Bypass -File .\tools\do_voice_co_bi_mat.ps1 ho-so-giong
#     powershell -ExecutionPolicy Bypass -File .\tools\do_voice_co_bi_mat.ps1 ho-so-giong -Luot 3 -Giong "Adam"
#
# CANH BAO ve tai: `ho-so-giong` chay 120 luot sinh (~15 phut GPU) va
# `voice_sidecar` KHONG dat torch.set_num_threads, nen torch lay tron 10 loi vat
# ly cho phan CPU. Chay khi may ranh. Kiem truoc:
#     python tools\cua_so_yen.py trang-thai

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('soat-giong', 'ho-so-giong', 'gia-von', 'chat-luong')]
    [string]$Viec,

    [int]$Luot = 3,
    [string]$Giong = '',

    # `ho-so-giong` co rao tu ve: thay tien trinh nao co cmdline chua
    # `gate.py|test_nhanh|pytest` thi TU CHOI chay. Rao ay khop theo TEN, khong
    # theo TAI THAT, nen mot phien khac dang mo mot tep test cung chan duoc lo do.
    #
    # [!] Chi bat co nay khi DA DO tai that va tai that THAP, va phai ghi so do
    #     KEM con so do duoc. Ly do rao ton tai la that: do luc may ban lam
    #     `do_lech_chuan` phong len, va con so ay di THANG vao phep giu cho
    #     credit -- tuc mot phep do ban se lam khach bi giu thua tien.
    [switch]$BoQuaKiemMay
)

$ErrorActionPreference = 'Stop'

$goc = Split-Path -Parent $PSScriptRoot
$envTep = 'C:\LTTPlatform\secrets\app.env'

if (-not (Test-Path $envTep)) {
    Write-Error "Khong thay $envTep. Chay tren may chu, hoac dat hai bien bang tay."
    exit 2
}

# Chi nap HAI bien. Khong doc dong nao khac vao bien moi truong.
$canNap = @('LTT_DATABASE_URL', 'LTT_VOICE_SIDECAR_TOKEN')
$soNap = 0
foreach ($dong in [IO.File]::ReadAllLines($envTep)) {
    $d = $dong.Trim()
    if ($d.Length -eq 0 -or $d.StartsWith('#')) { continue }
    $vt = $d.IndexOf('=')
    if ($vt -lt 1) { continue }
    $ten = $d.Substring(0, $vt).Trim()
    if ($canNap -notcontains $ten) { continue }
    # Set-Item tren Env: - gia tri KHONG di qua stdout.
    Set-Item -Path ("Env:" + $ten) -Value $d.Substring($vt + 1).Trim()
    $soNap++
}

# In SO LUONG, khong in gia tri. Do la toan bo diem cua vo boc nay.
Write-Host "Da nap $soNap/2 bien vao tien trinh nay (gia tri khong in ra)."
if ($soNap -eq 0) {
    Write-Error "Khong lay duoc bien nao - kiem lai ten khoa trong app.env."
    exit 2
}

$env:PYTHONPATH = $goc
$py = 'python'

switch ($Viec) {
    'soat-giong' {
        # CHI DOC. Khong truyen tham so nao khac - `xem` la subcommand chi doc,
        # con `duyet`/`tu-choi` thi GHI va co chu y KHONG mo o day.
        & $py (Join-Path $goc 'tools\soat_giong.py') xem
    }
    'ho-so-giong' {
        $doiSo = @((Join-Path $goc 'tools\do_ho_so_giong.py'), '--luot', $Luot)
        if ($Giong -ne '') { $doiSo += @('--giong', $Giong) }
        if ($BoQuaKiemMay) { $doiSo += '--bo-qua-kiem-may' }
        & $py $doiSo
    }
    'gia-von'    { & $py (Join-Path $goc 'tools\do_gia_von_voice.py') }
    'chat-luong' { & $py (Join-Path $goc 'tools\cong_chat_luong_voice.py') }
}

exit $LASTEXITCODE
