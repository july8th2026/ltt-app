<#
.SYNOPSIS
    Restore a data backup produced by backup.ps1 (P7/P9).

.DESCRIPTION
    Defaults to restoring into an ISOLATED directory so a restore
    rehearsal can be verified without touching live data - this is the
    "restore rehearsal" P7 requires.

    Pass -Live to overwrite the real data directory. That path stops the
    service first and takes a safety backup of current data beforehand,
    because overwriting live publishing history is irreversible.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [string]$Root = 'C:\LTTPlatform',
    [string]$ServiceName = 'LTTStudioWeb',
    [switch]$Live
)

$ErrorActionPreference = 'Stop'
# --------------------------------------------------------------- Invoke-Ngoai
# Voi `$ErrorActionPreference = 'Stop'`, MOT EXE NGOAI ghi ra stderr se thanh
# `NativeCommandError` va KET THUC script -- ngay ca khi exe do tra ve 0.
#
# pip, python, cloudflared va pg_dump deu ghi ra stderr trong luc chay binh
# thuong (canh bao, thanh tien trinh, mot dong chan doan). Hau qua khong phai
# "bao loi sai" ma la IM LANG: dong `if ($LASTEXITCODE -ne 0)` ngay sau do
# KHONG BAO GIO CHAY, script chet giua chung, va nhat ky dung lai o dong cuoi
# in duoc. Mot loi vo hai doc len giong het mot lan treo.
#
# Bay nay da dinh BON LAN trong hai ngay (30-31/08/2026): installer sidecar,
# `Test-Py`, `tai_khoan_thu.ps1`, roi buoc lam am HF cache.
#
# Boc loi goi lai: ha xuong 'Continue' dung trong khoi, roi tra lai. Khoi la
# `scriptblock` nen bien cua ham goi van thay duoc, va `$LASTEXITCODE` giu
# nguyen tu lenh cuoi -- moi phep kiem ma san co van dung.
function Invoke-Ngoai {
    param([Parameter(Mandatory = $true)][scriptblock]$Khoi)
    $truoc = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Khoi } finally { $ErrorActionPreference = $truoc }
}

if (-not (Test-Path $Archive)) { throw "Archive not found: $Archive" }

# H35.9: backup.ps1 ghi hai loai zip. Ban secrets KHONG duoc do vao data\ va
# KHONG duoc ghi de tu dong - app.env la file cau hinh cua dich vu dang chay,
# ghi de nham no lam ca nen tang khong khoi dong lai duoc. Dien tay, co chu y.
$isSecretArchive = (Split-Path -Leaf $Archive) -like 'ltt_secrets_*'
if ($isSecretArchive -and $Live) {
    Write-Host ''
    Write-Host '  [!] Day la ban sao SECRETS, khong phai ban sao du lieu.' -ForegroundColor Red
    Write-Host '      Khoi phuc secrets phai lam bang tay, co chu y:' -ForegroundColor Yellow
    Write-Host "        1. Expand-Archive `"$Archive`" -DestinationPath <thu muc tam>" -ForegroundColor Cyan
    Write-Host "        2. So sanh voi $Root\secrets\app.env truoc khi thay" -ForegroundColor Cyan
    Write-Host '        3. Dung dich vu, thay file, khoi dong lai, kiem /health/ready' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '      Bo -Live de dien thu vao thu muc rieng.' -ForegroundColor Yellow
    exit 1
}

if (-not $Live) {
    $target = Join-Path $Root ('restore_test_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Expand-Archive -Path $Archive -DestinationPath $target -Force
    Write-Host "  [OK] Rehearsal restore into $target" -ForegroundColor Green
    Get-ChildItem $target | ForEach-Object { Write-Host "      $($_.Name)  ($($_.Length) bytes)" }
    Write-Host "`n  Live data was NOT modified. Re-run with -Live to restore for real." -ForegroundColor Cyan
    exit 0
}

Write-Host "`n  [!] LIVE RESTORE - current data will be overwritten." -ForegroundColor Red
$confirm = Read-Host '      Type RESTORE to continue'
if ($confirm -ne 'RESTORE') { Write-Host '  Aborted.' -ForegroundColor Yellow; exit 1 }

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 5
}

# Safety net: never overwrite live data without a copy of what was there.
& (Join-Path $PSScriptRoot 'backup.ps1') -Root $Root -Stamp ('pre_restore_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))

$dataDir = Join-Path $Root 'data'
Expand-Archive -Path $Archive -DestinationPath $dataDir -Force
Write-Host '  [OK] Files restored (config, tokens, audit log)' -ForegroundColor Green

# ---- PostgreSQL ------------------------------------------------------------
# Giai nen KHONG khoi phuc CSDL: du lieu that nam trong PostgreSQL, ban sao la
# file <db>.dump do pg_dump -Fc tao. Phai pg_restore no, neu khong "khoi phuc"
# chi tra lai config/token con TAT CA nguoi dung/credit/job thi mat trang.
$envFile = Join-Path $Root 'secrets\app.env'
if (Test-Path $envFile) {
    $envText = Get-Content $envFile -Raw
    if ($envText -match '(?m)^LTT_DATABASE_URL=postgresql\+?\w*://([^:]+):([^@]+)@([^:/]+):(\d+)/(\S+)\s*$') {
        $dbUser = $Matches[1]; $dbPass = $Matches[2]
        $dbHost = $Matches[3]; $dbPort = $Matches[4]; $dbName = $Matches[5]
        $dumpFile = Join-Path $dataDir "$dbName.dump"
        if (-not (Test-Path $dumpFile)) {
            throw "Khong thay $dbName.dump trong ban sao luu. Ban sao nay KHONG co CSDL - dung lai de khong tuong da khoi phuc."
        }

        $pgRestore = $null
        foreach ($v in @('18','17','16','15','14')) {
            $c = "C:\Program Files\PostgreSQL\$v\bin\pg_restore.exe"
            if (Test-Path $c) { $pgRestore = $c; break }
        }
        if (-not $pgRestore) {
            $cmd = Get-Command pg_restore.exe -ErrorAction SilentlyContinue
            if ($cmd) { $pgRestore = $cmd.Source }
        }
        if (-not $pgRestore) { throw 'Co dump nhung khong tim thay pg_restore.exe. Dung lai.' }

        $env:PGPASSWORD = $dbPass
        # --clean --if-exists: xoa doi tuong cu roi nap lai (khoi phuc that su,
        # khong chi chen them). --no-owner: bo qua chu so huu de khong ket owner
        # cu. -1: mot transaction, loi thi rollback het (khong de CSDL nua voi).
        Invoke-Ngoai { & $pgRestore -U $dbUser -h $dbHost -p $dbPort -d $dbName --clean --if-exists --no-owner -1 $dumpFile }
        $rc = $LASTEXITCODE
        $env:PGPASSWORD = $null
        if ($rc -ne 0) {
            throw "pg_restore that bai (ma $rc). CSDL co the chua khoi phuc day du - kiem tra truoc khi chay tiep."
        }
        Remove-Item $dumpFile -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] pg_restore: $dbName" -ForegroundColor Green

        # ---- Nang LUOC DO sau khi nap dump ---------------------------------
        # VI SAO BUOC NAY BAT BUOC: `pg_restore` tra lai CSDL DUNG NHU LUC CHUP,
        # ke ca bang `alembic_version`. Backup chay luc 02:30 con migration chi
        # ap luc DEPLOY, nen mot ban sao BINH THUONG van co the cu hon ma dang
        # chay - do la vong doi dung, khong phai loi cua ban sao.
        #
        # BO BUOC NAY thi dich vu khoi dong lai tren mot CSDL CU HON ma: cot moi
        # khong ton tai, va loi hien ra o cho khong ai ngo, HANG GIO sau khi da
        # bao "khoi phuc thanh cong".
        #
        # Do 23/09/2026 (dien tap D1): dump 02:30 mang alembic_version
        # `e4a19c07b5d2`, ma dang chay o `5e1a9c46b2d7` - lech dung 3 migration.
        # Nang mat 1,37 giay. Duong nay da chay that trong
        # `deploy/windows/dien_tap_khoi_phuc.ps1` va xac minh version sau = head.
        $venvPy = 'C:\LTTPlatform\venv\Scripts\python.exe'
        if (-not (Test-Path $venvPy)) { $venvPy = 'python' }
        Write-Host '  [..] alembic upgrade head' -ForegroundColor Cyan
        Push-Location $Root\app
        try {
            Invoke-Ngoai { & $venvPy -m alembic upgrade head }
            $rcAl = $LASTEXITCODE
        } finally { Pop-Location }
        if ($rcAl -ne 0) {
            throw "alembic upgrade head that bai (ma $rcAl). CSDL da nap nhung luoc do CU HON ma dang chay - DUNG khoi dong dich vu, sua roi chay lai."
        }
        Write-Host '  [OK] alembic upgrade head' -ForegroundColor Green
    }
}

Start-Service $ServiceName
Write-Host '  Service restarted. Verify: curl http://127.0.0.1:8100/health/ready' -ForegroundColor Cyan
