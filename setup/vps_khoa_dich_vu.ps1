# vps_khoa_dich_vu.ps1 - dua KHOA SSH CUA DICH VU ve secrets\ va siet quyen.
#
# KHONG CHAY TAY TEP NAY neu chua doc muc "Vi sao" ben duoi. No sua ACL cua thu
# muc bi mat va sua secrets\app.env.
#
# Goi tu lop ngoai (cung khuon voi deploy_nang_quyen.ps1, AGENTS.md 9.3):
#
#     Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
#       '-File','"D:\LTTSTUDIOSAPP\setup\vps_khoa_dich_vu.ps1"' -Verb RunAs
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# ============================================================================
# VI SAO TEP NAY TON TAI
# ============================================================================
#
# VPS co HAI duong dieu khien, va chung hong theo hai kieu khac nhau:
#
#   Proxmox (tao/xoa/console)  -> HTTP + token, bi mat nam TRONG app.env
#   Router + cong vao (DHCP,   -> SSH + TEP KHOA, app.env chi giu DUONG DAN
#   NAT, cap IP)                  toi mot tep nam NGOAI secrets\
#
# Ba dich vu chay bang LocalSystem. Khoa nam o C:\Users\<nguoi>\.ssh\, noi ACL
# thua ke cho ca tai khoan nguoi dung -> tu goc nhin cua SYSTEM do la khoa "ho",
# va OpenSSH TU CHOI dung no:
#
#     WARNING: UNPROTECTED PRIVATE KEY FILE!
#     Permissions for '...\ltt_pve' are too open.
#
# Hau qua do duoc 2026-08-27: khach tra 1.490 credit, may vao trang thai `loi`,
# `/vps` van ban binh thuong, `/health/ready` van 200. Loi im lang hoan toan.
#
# !!VA MOT THU NANG HON. `2-cai-dat.ps1` in ra:
#        Ok 'Chi SYSTEM va Administrators doc duoc secrets\'
#    Cau do KHONG con dung: ACL that cua secrets\ co them mot ACE TUONG MINH cho
#    tai khoan nguoi dung. Nghia la app.env - noi giu khoa phien, khoa ma hoa
#    token, hash mat khau admin, token Proxmox, khoa Vultr - dang nam duoi dung
#    cai ACL yeu do. Buoc 1 duoi day sua ca viec do, khong chi sua khoa SSH.
#
# ============================================================================
# NO LAM GI, THEO THU TU
# ============================================================================
#   1. Sao luu app.env
#   2. Sao chep hai khoa vao secrets\  (BAN TRONG .ssh GIU NGUYEN cho con nguoi)
#   3. Siet ACL secrets\ ve DUNG hai chu the: SYSTEM + Administrators
#   4. Tro hai bien LTT_VPS_*_SSH_KEY vao ban trong secrets\   (UTF-8 KHONG BOM)
#   5. Khoi dong lai Web + Worker de chung doc bien moi
#   6. In lai ACL de nguoi doc TU THAY ket qua, khong phai tin mot dong "Ok"
#
# Chay lai duoc nhieu lan: buoc 2 va 4 deu kiem truoc khi ghi.

[CmdletBinding()]
param(
    [string]$Secrets = 'C:\LTTPlatform\secrets',
    [string]$LogDir  = 'C:\LTTPlatform\logs'
)

$ErrorActionPreference = 'Stop'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$sum = Join-Path $LogDir "vpskhoa-$stamp.ket.txt"

function Ghi([string]$m) {
    Write-Host $m
    $m | Add-Content $sum -Encoding utf8
}

"BAT DAU=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content $sum -Encoding utf8
Ghi "ADMIN=$isAdmin"

if (-not $isAdmin) {
    Ghi 'EXITCODE=-1'
    Ghi 'LY_DO=khong co quyen Administrator - lop ngoai phai dung -Verb RunAs'
    Start-Sleep -Seconds 6
    exit 1
}

$envFile = Join-Path $Secrets 'app.env'
if (-not (Test-Path $envFile)) {
    Ghi 'EXITCODE=-2'
    Ghi "LY_DO=khong thay $envFile"
    Start-Sleep -Seconds 6
    exit 1
}

try {
    # -- 1. Sao luu ------------------------------------------------------------
    $bak = Join-Path $Secrets "app.env.bak-khoassh-$stamp"
    Copy-Item $envFile $bak -Force
    Ghi "BUOC1 sao luu -> $bak"

    # -- 2. Chep khoa ----------------------------------------------------------
    # Doc duong dan HIEN TAI tu app.env thay vi viet cung: neu chu san pham da
    # doi cho khoa thi tep nay phai theo, khong duoc doan.
    $noiDung = Get-Content $envFile -Raw
    $cap = @(
        @{ Bien = 'LTT_VPS_ROUTER_SSH_KEY';  Ten = 'ltt_pve' },
        @{ Bien = 'LTT_VPS_GATEWAY_SSH_KEY'; Ten = 'ltt_gateway' }
    )
    foreach ($c in $cap) {
        $m = [regex]::Match($noiDung, "(?m)^$($c.Bien)=(.+)$")
        if (-not $m.Success) { Ghi "BUOC2 BO QUA $($c.Bien) - khong khai trong app.env"; continue }
        $cu = $m.Groups[1].Value.Trim()
        $moi = Join-Path $Secrets $c.Ten
        if ($cu -eq $moi) { Ghi "BUOC2 $($c.Bien) da tro vao secrets\ roi"; continue }
        if (-not (Test-Path $cu)) { Ghi "BUOC2 LOI: khong thay khoa nguon $cu"; throw "thieu khoa $cu" }
        Copy-Item $cu $moi -Force
        Ghi "BUOC2 chep $($c.Ten) -> $moi  (ban trong .ssh GIU NGUYEN)"
    }

    # -- 3. Siet ACL -----------------------------------------------------------
    #
    # !!!! DAY LA CHO MA `2-cai-dat.ps1:231` LAM SAI, VA BAN DAU TEP NAY CUNG SAI.
    #
    #   icacls $p /inheritance:r /grant:r "SYSTEM:..." "Administrators:..."
    #
    # `/inheritance:r` bo cac ACE THUA KE. `/grant:r` thay quyen cua nhung chu
    # the DUOC LIET KE. Khong cai nao dung toi mot ACE TUONG MINH cua chu the
    # khac - no song sot nguyen ven.
    #
    # Do 2026-08-27: sau khi chay dong tren, secrets\ VAN co ACE tuong minh cho
    # tai khoan nguoi dung. Trinh cai dat van in 'Ok Chi SYSTEM va Administrators
    # doc duoc secrets\' - mot cau sai suot tu do toi nay.
    #
    # Cach dung: LIET KE roi XOA tung chu the ngoai danh sach cho phep.
    $chuThePhep = @('SYSTEM', 'Administrators', 'TrustedInstaller')

    icacls $Secrets /inheritance:r | Out-Null
    foreach ($ace in @((Get-Acl $Secrets).Access)) {
        $day = $ace.IdentityReference.Value
        $ten = ($day -split '\\')[-1]
        if ($chuThePhep -notcontains $ten) {
            icacls $Secrets /remove:g "$day" | Out-Null
            Ghi "BUOC3 xoa ACE thua: $day"
        }
    }
    icacls $Secrets /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" | Out-Null
    # Tep con: bo ACE tuong minh cua chung de chung THUA KE tu thu muc vua siet.
    Get-ChildItem $Secrets -File | ForEach-Object {
        icacls $_.FullName /reset | Out-Null
    }

    # !! KIEM LAI, va HONG TO neu chua dat. Lan chay dau cua tep nay in
    #    'da siet ACL' roi thoat EXITCODE=0 trong khi ACL van y nguyen - dung cai
    #    lop loi ma no sinh ra de vach. Mot buoc khong tu kiem la mot buoc se noi
    #    doi vao dung ngay no that bai.
    $con = @((Get-Acl $Secrets).Access |
        ForEach-Object { ($_.IdentityReference.Value -split '\\')[-1] } |
        Where-Object { $chuThePhep -notcontains $_ } | Select-Object -Unique)
    if ($con.Count -gt 0) {
        throw "siet ACL that bai - van con chu the: $($con -join ', ')"
    }
    Ghi 'BUOC3 da siet ACL secrets\ ve DUNG hai chu the (da kiem lai)'

    # -- 4. Tro bien vao ban moi ----------------------------------------------
    # !![IO.File]::WriteAllText voi UTF8Encoding($false) - KHONG BOM.
    #    `Out-File -Encoding utf8` cua PowerShell 5.1 chen BOM, `json.load()` vo,
    #    va `/health/ready` tra 503 trong khi dich vu van chay. Loi nay DA lam
    #    sap production o du an nay (quy tac 1 cua CLAUDE.md).
    $sau = $noiDung
    foreach ($c in $cap) {
        $moi = Join-Path $Secrets $c.Ten
        $sau = [regex]::Replace($sau, "(?m)^$($c.Bien)=.*$", "$($c.Bien)=$moi")
    }
    if ($sau -ne $noiDung) {
        [IO.File]::WriteAllText($envFile, $sau, (New-Object Text.UTF8Encoding($false)))
        Ghi 'BUOC4 da tro hai bien vao secrets\ (UTF-8 KHONG BOM)'
    } else {
        Ghi 'BUOC4 khong can doi - hai bien da dung'
    }

    # -- 5. Nap lai ENV vao dich vu (KHONG phai chi restart) --------------------
    #
    # !!!! `Restart-Service` MOT MINH LA KHONG DU, va ban dau tep nay lam sai.
    #
    # Dich vu chay qua nssm, va nssm NUONG bien moi truong vao dang ky dich vu
    # LUC CAI (`AppEnvironmentExtra`). `server\run.py` chi doc `os.environ` - no
    # KHONG tu doc secrets\app.env luc chay. Nen sua app.env roi restart la:
    #
    #     dich vu len lai voi ENV CU, khong loi nao bao
    #
    # Du an nay da tra gia cho dung cai bay do HAI lan (cong VLM may B; va
    # LTT_PUBLIC_API_TOOLS ngay 23/08), da viet han `nap_lai_env.ps1` va mot
    # doan canh bao dai o dau tep do - va lan chay dau cua tep NAY van dam vao
    # lan thu ba: no doi duong dan khoa trong app.env, restart, roi bao xong,
    # trong khi worker van dung duong dan CU. Trieu chung: may van vao `loi` voi
    # nguyen van thong bao cu, tro vao duong dan cu.
    #
    # => Goi thang script da co. Khong chep lai logic nssm o day: hai ban se lech.
    $napLai = Join-Path $PSScriptRoot 'nap_lai_env.ps1'
    if (-not (Test-Path $napLai)) { throw "khong thay $napLai" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $napLai 2>&1 |
        ForEach-Object { Ghi "   $_" }
    if ($LASTEXITCODE -ne 0) { throw "nap_lai_env.ps1 tra ma $LASTEXITCODE" }
    Ghi 'BUOC5 da NAP LAI env vao dich vu (khong chi restart)'
    foreach ($sv in 'LTTStudioWorker', 'LTTStudioWeb') {
        Ghi "BUOC5 $sv -> $((Get-Service $sv).Status)"
    }

    # -- 6. In lai de NGUOI DOC tu thay ---------------------------------------
    Ghi 'BUOC6 ACL secrets\ sau khi sua:'
    (icacls $Secrets) | ForEach-Object { Ghi "   $_" }

    Ghi 'EXITCODE=0'
    Write-Host ''
    Write-Host 'XONG (EXITCODE=0).' -ForegroundColor Green
}
catch {
    Ghi "EXITCODE=1"
    Ghi "LOI=$($_.Exception.Message)"
    Write-Host ''
    Write-Host "HONG - xem $sum" -ForegroundColor Red
}

Ghi "KET THUC=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "Ket qua: $sum"
Start-Sleep -Seconds 8
