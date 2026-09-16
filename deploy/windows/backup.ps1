<#
.SYNOPSIS
    Back up runtime data, configuration and key material (P7/P9).

.DESCRIPTION
    Scope follows docs/DATA_RETENTION_POLICY.md: databases, config,
    encrypted token stores and the audit log are included; the disposable
    video cache, session locks and rotating logs are excluded.

    HAI ban sao luu RIENG, khong bao gio chung mot file zip:

      ltt_data_<stamp>.zip     -> -BackupDir   (config, *.enc, *.db, pg_dump)
      ltt_secrets_<stamp>.zip  -> -SecretsDir  (secrets\app.env)

    Vi sao tach (H35.9): app.env giu LTT_TOKEN_ENCRYPTION_KEY va
    LTT_API_KEY_PEPPER, con dump giu ban ma cua token lan hash khoa API cua
    khach. Gop chung mot zip nghia la MOT ban sao bi lay cap la du de doc token
    va tan cong khoa API ngoai tuyen. Tach ra thi mot ban sao khong con du.

    Mac dinh -SecretsDir la thu muc ANH EM cua -BackupDir (duoi '-secrets'),
    KHONG phai thu muc con: dong bo off-site tro vao -BackupDir se khong vo
    tinh keo theo bi mat.

    Ca hai ban sao van CHUA du lieu nhay cam. Bao ve chung nhu bao ve may chu.
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Stamp = (Get-Date -Format 'yyyyMMdd_HHmmss'),
    [switch]$IncludeSecrets,
    # Q28: mac dinh backup nam CUNG o voi ban chay ($Root\backups). De chong
    # mat du lieu khi mot o hong, tro sang O KHAC bang -BackupDir D:\LTTBackups.
    [string]$BackupDir = '',
    # H35.9: noi cat ban sao secrets. Mac dinh "<BackupDir>-secrets".
    [string]$SecretsDir = ''
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

$dataDir = Join-Path $Root 'data'
if ($BackupDir) { $backups = $BackupDir } else { $backups = Join-Path $Root 'backups' }
if ($SecretsDir) { $secretsOut = $SecretsDir } else { $secretsOut = "$($backups.TrimEnd('\'))-secrets" }
$staging = Join-Path $env:TEMP "ltt_backup_$Stamp"

if (-not (Test-Path $dataDir)) { throw "Data directory not found: $dataDir" }
if (-not (Test-Path $backups)) { New-Item -ItemType Directory -Path $backups -Force | Out-Null }

New-Item -ItemType Directory -Path $staging -Force | Out-Null

# Included: authoritative state. Excluded: anything regenerable.
$patterns = @('config.json', 'workers.json', '*.enc', '*.db', '*.sqlite3', 'audit_log.jsonl')
$copied = 0
foreach ($p in $patterns) {
    Get-ChildItem -Path $dataDir -Filter $p -File -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item $_.FullName -Destination $staging -Force
        $copied++
    }
}

# ---- Du lieu giong noi (W-KHO, 16/09/2026) ----------------------------------
# Hai thu muc CON cua data\ ma mau tren (chi cap dau) khong bat duoc:
#   data\voice_goc\    - clip goc ben cua giong kho chung (+ manifest.json)
#   data\files\voice\  - tep giong khi LTT_STORAGE_LOCAL_PREFIXES co 'voice/'
#                        (clip nguon, bieu dien, ban nghe thu cua MOI giong)
# Do la du lieu SINH TRAC khong dung lai duoc: bucket R2 da xoa 56/58 tep cua
# 29 ho so (do 15/09) va khong co ban sao nao khac. Bo `voice\out\` (tep ket qua
# cua job, co han luu 30 ngay, co the doc lai).
$voiceNguon = @(
    @{ Goc = (Join-Path $dataDir 'voice_goc');     Dich = 'voice_goc' },
    @{ Goc = (Join-Path $dataDir 'files\voice');   Dich = 'files_voice' }
)
foreach ($v in $voiceNguon) {
    if (-not (Test-Path $v.Goc)) { continue }
    # Get-Item().FullName, KHONG Resolve-Path: Resolve-Path giu nguyen dang 8.3
    # (THANGT~1) con FullName cua tep con la dang day du, nen Substring cat lech
    # va loc `out\` truot (do bang chay thu 16/09).
    $gocDay = (Get-Item -LiteralPath $v.Goc).FullName.TrimEnd('\')
    $tepVoice = Get-ChildItem -Path $gocDay -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notlike "$gocDay\out\*" }
    foreach ($t in $tepVoice) {
        $tuongDoi = $t.FullName.Substring($gocDay.Length + 1)
        $dichTep = Join-Path (Join-Path $staging $v.Dich) $tuongDoi
        New-Item -ItemType Directory -Path (Split-Path -Parent $dichTep) -Force | Out-Null
        Copy-Item $t.FullName -Destination $dichTep -Force
        $copied++
    }
    Write-Host "  [OK] voice: $($tepVoice.Count) tep tu $gocDay" -ForegroundColor Green
}

# -IncludeSecrets duoc xu ly O CUOI FILE, trong mot ban sao RIENG. Khong copy
# app.env vao $staging: staging la thu muc dung de nen ra ltt_data_*.zip, va
# ca hai thu do nam chung mot zip chinh la loi dang sua (H35.9).

# ---- PostgreSQL ------------------------------------------------------------
# Sao luu file KHONG bat duoc du lieu Postgres: no nam trong thu muc du lieu
# rieng cua PostgreSQL, va chep file .db cua mot CSDL dang chay cho ra ban sao
# hong. Phai dung pg_dump.
$envFile = Join-Path $Root 'secrets\app.env'
if (Test-Path $envFile) {
    $envText = Get-Content $envFile -Raw
    if ($envText -match '(?m)^LTT_DATABASE_URL=postgresql\+?\w*://([^:]+):([^@]+)@([^:/]+):(\d+)/(\S+)\s*$') {
        $dbUser = $Matches[1]; $dbPass = $Matches[2]
        $dbHost = $Matches[3]; $dbPort = $Matches[4]; $dbName = $Matches[5]

        $pgDump = $null
        foreach ($v in @('18','17','16','15','14')) {
            $c = "C:\Program Files\PostgreSQL\$v\bin\pg_dump.exe"
            if (Test-Path $c) { $pgDump = $c; break }
        }
        if (-not $pgDump) {
            $cmd = Get-Command pg_dump.exe -ErrorAction SilentlyContinue
            if ($cmd) { $pgDump = $cmd.Source }
        }

        if ($pgDump) {
            $dumpFile = Join-Path $staging "$dbName.dump"
            $env:PGPASSWORD = $dbPass
            # Dinh dang custom (-Fc): nen san va khoi phuc chon loc duoc bang
            # pg_restore, khac han mot file .sql phang.
            Invoke-Ngoai { & $pgDump -U $dbUser -h $dbHost -p $dbPort -d $dbName -Fc -f $dumpFile }
            $rc = $LASTEXITCODE
            $env:PGPASSWORD = $null
            if ($rc -ne 0 -or -not (Test-Path $dumpFile)) {
                # KHONG bo qua am tham: mot ban sao luu thieu CSDL trong giong
                # het mot ban sao luu day du, va chi lo ra dung luc can khoi phuc.
                throw "pg_dump that bai (ma $rc). Sao luu DUNG LAI de ban khong nham tuong da co ban du."
            }
            $copied++
            Write-Host "  [OK] pg_dump: $dbName" -ForegroundColor Green
        } else {
            throw 'Co LTT_DATABASE_URL nhung khong tim thay pg_dump.exe. Sao luu dung lai.'
        }
    }
}

# Nen mot thu muc staging thanh zip, MO LAI de kiem, roi don ban cu.
# Mot ban sao luu chua tung mo lai la niem tin, khong phai ban sao luu.
function Write-LttArchive {
    param(
        [Parameter(Mandatory = $true)][string]$Staging,
        [Parameter(Mandatory = $true)][string]$Archive,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [int]$Keep = 14
    )
    Compress-Archive -Path (Join-Path $Staging '*') -DestinationPath $Archive -Force
    Remove-Item $Staging -Recurse -Force

    $zip = [IO.Compression.ZipFile]::OpenRead($Archive)
    try { $entries = $zip.Entries.Count } finally { $zip.Dispose() }
    Write-Host "  [OK] Backup written: $Archive ($entries entries)" -ForegroundColor Green

    Get-ChildItem -Path (Split-Path -Parent $Archive) -Filter $Pattern |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip $Keep |
        ForEach-Object { Remove-Item $_.FullName -Force; Write-Host "  pruned $($_.Name)" }
}

if ($copied -eq 0) {
    # An empty data directory is a legitimate state (fresh install, before
    # any config or token exists) - not an error. Throwing here used to
    # abort update.ps1 entirely, because update.ps1 backs up before it
    # touches anything. Warn and succeed instead.
    Remove-Item $staging -Recurse -Force
    Write-Host '  [SKIP] Khong co du lieu de sao luu (cai moi) - bo qua.' -ForegroundColor Yellow
} else {
    Write-LttArchive -Staging $staging `
                     -Archive (Join-Path $backups "ltt_data_$Stamp.zip") `
                     -Pattern 'ltt_data_*.zip'
}

# ---- Secrets, trong mot ban sao RIENG ---------------------------------------
# H35.9. Mat LTT_API_KEY_PEPPER la mat TOAN BO khoa API cua khach, khong khoi
# phuc duoc - nen no phai duoc sao luu. Nhung sao luu no CUNG CHO voi pg_dump
# thi mot ban zip bi lay cap la du de tan cong khoa ngoai tuyen. Hai file, hai
# thu muc.
if ($IncludeSecrets) {
    $envFile = Join-Path $Root 'secrets\app.env'
    if (Test-Path $envFile) {
        if (-not (Test-Path $secretsOut)) {
            New-Item -ItemType Directory -Path $secretsOut -Force | Out-Null
        }
        if ((Resolve-Path $backups).Path -eq (Resolve-Path $secretsOut).Path) {
            Write-Host ('  [!] -SecretsDir TRUNG -BackupDir. Hai ban sao van la hai ' +
                        'file rieng, nhung nam cung mot thu muc thi khong con tach ' +
                        'that. Tro -SecretsDir sang cho khac.') -ForegroundColor Yellow
        }
        $secretStaging = Join-Path $env:TEMP "ltt_secrets_$Stamp"
        New-Item -ItemType Directory -Path $secretStaging -Force | Out-Null
        Copy-Item $envFile -Destination (Join-Path $secretStaging 'app.env') -Force

        Write-LttArchive -Staging $secretStaging `
                         -Archive (Join-Path $secretsOut "ltt_secrets_$Stamp.zip") `
                         -Pattern 'ltt_secrets_*.zip'
        Write-Host ('  [!] Ban sao secrets CHUA khoa ma hoa va pepper. Cat mot ban ' +
                    'NGOAI may nay (Q28: off-site).') -ForegroundColor Yellow
    }
}
