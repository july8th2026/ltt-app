<#
.SYNOPSIS
    Restore REHEARSAL for LTT Studios backups. NEVER touches production.

.DESCRIPTION
    Verifies that a backup produced by backup.ps1 can actually be restored:
    copies the zip into a TEMP directory (never C:\LTTPlatform), unpacks it,
    creates a throwaway database lttplatform_dienthu_<stamp>, pg_restore the
    dump INTO THAT DATABASE ONLY, runs reconciliation checks on it, prints a
    JSON report with per-step RTO, then DROPS the database and deletes the
    temp directory in a finally block - even when a step fails.

    Exit code: 0 = every check green, 1 = one or more checks red (or the
    rehearsal failed). The production database lttplatform is NEVER opened
    for restore, NEVER written, and its data is only READ by count queries
    on the throwaway database.

    Connection settings are read from C:\LTTPlatform\secrets\app.env with the
    exact same method as restore.ps1 (LTT_DATABASE_URL regex). The password
    goes to pg_restore / psql through the PGPASSWORD environment variable and
    is never printed.

    Parameters:
      -Archive       (mandatory) path to ltt_data_<stamp>.zip
      -SecretsArchive optional path to ltt_secrets_<stamp>.zip - integrity +
                     entry NAMES are checked only; it is never expanded.
      -Dam           optional path to a dump file used INSTEAD of the dump in
                     the archive. Exists only for the negative control: pass a
                     deliberately truncated copy of the dump and verify the
                     rehearsal goes red and exits non-zero.
      -EnvFile       optional override of the app.env path (default C:\LTTPlatform\secrets\app.env)
      -SuperFile     optional override of the superuser password file
                     (default C:\LTTPlatform\secrets\postgres-superuser.txt).
                     Read ONLY to get the CREATE/DROP rights for the throwaway
                     database, using the exact same file setup/2-cai-dat.ps1
                     reads (line 864). The app role ltt_app has rolcreatedb=f,
                     so CREATE/DROP DATABASE cannot be done as ltt_app at all.
                     pg_restore itself still runs AS the app role, into a DB
                     the app role OWNS (CREATE DATABASE ... OWNER ltt_app) -
                     the same ownership split as production.
      -Stamp        optional rehearsal stamp (default now).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [string]$SecretsArchive = '',
    [string]$Dam = '',
    [string]$EnvFile = 'C:\LTTPlatform\secrets\app.env',
    [string]$SuperFile = 'C:\LTTPlatform\secrets\postgres-superuser.txt',
    [string]$Stamp = (Get-Date -Format 'yyyyMMdd_HHmmss')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# --------------------------------------------------------------- Chay-Process
# Launch a native process with ALL THREE stdio streams redirected:
#  - stdout/stderr are drained by ASYNC readers (a synchronous ReadToEnd
#    deadlocks when the child does not exit on its own);
#  - stdin is REDIRECTED and CLOSED immediately. This is the critical one:
#    psql, with an inherited open stdin, enters its read-eval loop AFTER
#    processing -c and blocks on a line that never comes - the process then
#    never exits and every WaitForExit hangs forever (observed: the previous
#    rehearsal's finally block froze on exactly this).
#  - a hard timeout (GiayToiDa): on expiry the process is KILLED and the
#    result carries ma = -1 so the caller reports and moves on instead of
#    retrying against a possibly-restarted PostgreSQL in an infinite loop.
function Chay-Process {
    param(
        [Parameter(Mandatory = $true)][string]$TienTrinh,
        [string]$ThuMuc = '',
        [Parameter(Mandatory = $true)][string]$ThamSo,
        [int]$GiayToiDa = 60
    )
    $kq = @{ ma = -1; stdout = ''; stderr = ''; het_gioi_han = $false }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $TienTrinh
    if ($ThuMuc) { $psi.WorkingDirectory = $ThuMuc }
    $psi.Arguments = $ThamSo
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardInput = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $p = [System.Diagnostics.Process]::Start($psi)
    $p.StandardInput.Close()   # never let the child sit on an open stdin
    $rdOut = $p.StandardOutput.ReadToEndAsync()
    $rdErr = $p.StandardError.ReadToEndAsync()
    $xong = $p.WaitForExit([TimeSpan]::FromSeconds($GiayToiDa))
    if (-not $xong) {
        $kq.het_gioi_han = $true
        try { $p.Kill() } catch { }
        $p.WaitForExit(5000) | Out-Null
        return $kq
    }
    $kq.ma = $p.ExitCode
    # Bounded read: the streams are already fully drained for a finished,
    # killed-or-exited process; a short cap still keeps the path total.
    if (-not $rdOut.Wait(5000)) { try { $kq.stdout = $p.StandardOutput.ReadToEnd() } catch { } } else { $kq.stdout = $rdOut.Result }
    if (-not $rdErr.Wait(5000)) { try { $kq.stderr = $p.StandardError.ReadToEnd() } catch { } } else { $kq.stderr = $rdErr.Result }
    return $kq
}

# --------------------------------------------------------------- Chay-PSQL-QuanTri
# Same launcher, but for the SUPERUSER role (CREATE/DROP DATABASE). The
# password comes from the file, goes to the child through PGPASSWORD and is
# never printed; it is set only for the duration of the child.
function Chay-PSQL-QuanTri {
    param(
        [Parameter(Mandatory = $true)][string]$ThamSo,
        [int]$GiayToiDa = 60
    )
    $truoc = $env:PGPASSWORD
    $env:PGPASSWORD = $superPass
    try {
        return (Chay-Process -TienTrinh $psql -ThamSo $ThamSo -GiayToiDa $GiayToiDa)
    } finally {
        if ($null -eq $truoc) { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue } else { $env:PGPASSWORD = $truoc }
    }
}

# --------------------------------------------------------------- Chay-Alembic
# Launcher for alembic, with ONE safety device that matters more than the
# command itself: platform_core.db.database_url() reads LTT_DATABASE_URL from
# the CHILD environment. The env file's URL points at the LIVE database - if
# it leaked into the upgrade child, 'alembic upgrade head' would migrate the
# production database. So this function pins LTT_DATABASE_URL to the TEMP
# database (same user/host/port, db = $dbName) around the call, and removes
# it in finally. The child can only ever see the rehearsal database.
function Chay-Alembic {
    param(
        [Parameter(Mandatory = $true)][string]$ThamSo,
        [string]$ThuMuc = 'C:\LTTPlatform\app',
        [int]$GiayToiDa = 600
    )
    $venvPyLocal = 'C:\LTTPlatform\venv\Scripts\python.exe'
    if (-not (Test-Path $venvPyLocal)) { $venvPyLocal = 'python' }
    $urlTam = "postgresql+psycopg://${dbUser}:${pgPass}@${dbHost}:${dbPort}/${dbName}"
    $truoc = $null
    if ($env:LTT_DATABASE_URL) { $truoc = $env:LTT_DATABASE_URL }
    $env:LTT_DATABASE_URL = $urlTam
    try {
        return (Chay-Process -TienTrinh $venvPyLocal -ThuMuc $ThuMuc -ThamSo ("-m alembic $ThamSo") -GiayToiDa $GiayToiDa)
    } finally {
        if ($null -eq $truoc) { Remove-Item Env:LTT_DATABASE_URL -ErrorAction SilentlyContinue } else { $env:LTT_DATABASE_URL = $truoc }
    }
}

# --------------------------------------------------------------- Report
function Write-BaoCao {
    param([hashtable]$BaoCao, [switch]$Xanh)
    $json = $BaoCao | ConvertTo-Json -Depth 8
    Write-Host "=== BAO CAO DIEN TAP KHOI PHUC ==="
    Write-Host $json
    if ($Xanh) { Write-Host "KET LUA: XANH - ban sao khong co van de theo cac phap do." -ForegroundColor Green }
    else      { Write-Host "KET LUA: DO - xem chi tiet trong bao cao JSON." -ForegroundColor Red }
}

$tbTemp = Join-Path $env:TEMP "ltt_dienthu_$Stamp"
$staging = Join-Path $tbTemp 'giai_nen'
$dbName = "lttplatform_dienthu_$Stamp"
# Init BEFORE try: finally must clean up even if the failure lands at any
# step, and Set-StrictMode forbids reading unassigned variables (losing the
# temp DB name = cannot drop it).
$pgPass = $null
$pgRestore = $null
$psql = $null
$dbUser = ''
$dbHost = ''
$dbPort = ''
$dbLive = ''
$superUser = 'postgres'
$superPass = $null
$baoCao = @{
    bien = 'dien_tap_khoi_phuc'
    stamp = $Stamp
    archive = $Archive
    db_tam = $dbName
    steps = @{}
    kiem = @()
    ket_qua = 'CHAY'
}
$toanBoDo = [System.Diagnostics.Stopwatch]::StartNew()

function DoiThoiGian {
    param([System.Diagnostics.Stopwatch]$Sw)
    [math]::Round($Sw.Elapsed.TotalSeconds, 2)
}

try {
    # ---- 0. Locate PostgreSQL binaries --------------------------------
    $pgRestore = $null; $psql = $null
    foreach ($v in @('18','17','16','15','14')) {
        $c = "C:\Program Files\PostgreSQL\$v\bin\pg_restore.exe"
        if (Test-Path $c) {
            $pgRestore = $c
            $psql = (Join-Path (Split-Path $c -Parent) 'psql.exe')
            break
        }
    }
    if (-not $pgRestore) { $cmd = Get-Command pg_restore.exe -ErrorAction SilentlyContinue; if ($cmd) { $pgRestore = $cmd.Source; $psql = (Join-Path (Split-Path $cmd.Source -Parent) 'psql.exe') } }
    if (-not $pgRestore -or -not (Test-Path $psql)) {
        throw 'Khong tim thay pg_restore.exe / psql.exe. Dien tap khong thuc hien duoc.'
    }
    $baoCao.steps['tim_pg'] = "PostgreSQL: $pgRestore"

    # ---- 1. Integrity of the archive (open as zip, count entries) -----
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    if (-not (Test-Path $Archive)) { throw "Archive not found: $Archive" }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        $soTepZip = $zip.Entries.Count
        $coDumpTrongZip = $false
        foreach ($e in $zip.Entries) {
            if ($e.Name -like '*.dump') { $coDumpTrongZip = $true; $tenDumpTrongZip = $e.Name; $kichThuocDumpZip = $e.Length }
        }
    } finally { $zip.Dispose() }
    $baoCao.steps['kiem_toan_zip'] = @{
        rto_giay = (DoiThoiGian $sw)
        so_tep = $soTepZip
        co_dump = $coDumpTrongZip
        ten_dump = $(if ($coDumpTrongZip) { $tenDumpTrongZip } else { $null })
    }
    Write-Host "[OK] toan vien: zip mo duoc, $soTepZip entries, dump trong zip: $coDumpTrongZip"
    if (-not $coDumpTrongZip) {
        $baoCao.kiem += @{ ten = 'zip_co_dump'; xanh = $false; thong_tin = 'ban sao KHONG chua file *.dump - CSDL khong co trong ban sao nay' }
    } else {
        $baoCao.kiem += @{ ten = 'zip_co_dump'; xanh = $true; thong_tin = "$tenDumpTrongZip ($kichThuocDumpZip bytes)" }
    }

    # ---- 2. Copy + extract into TEMP (never C:\LTTPlatform) ----------
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    Copy-Item -LiteralPath $Archive -Destination (Join-Path $tbTemp 'ban_chep.zip') -Force
    Expand-Archive -Path $Archive -DestinationPath $staging -Force
    $baoCao.steps['chep_giai_nen'] = @{ rto_giay = (DoiThoiGian $sw); thu_muc = $staging }
    Write-Host "[OK] da chep + giai nen vao $staging"

    # ---- 3. Read connection from app.env (restore.ps1 method) --------
    if (-not (Test-Path $EnvFile)) { throw "Khong doc duoc cau hinh: $EnvFile" }
    $envText = Get-Content $EnvFile -Raw
    if ($envText -match '(?m)^LTT_DATABASE_URL=postgresql\+?\w*://([^:]+):([^@]+)@([^:/]+):(\d+)/(\S+)\s*$') {
        $dbUser = $Matches[1]; $pgPass = $Matches[2]
        $dbHost = $Matches[3]; $dbPort = $Matches[4]; $dbLive = $Matches[5]
    } else {
        throw 'LTT_DATABASE_URL khong nam trong cau hinh - dien tap khong ket noi duoc'
    }
    $baoCao.steps['ket_noi'] = @{ host = $dbHost; port = $dbPort; db_sap_nap = $dbName; db_live = $dbLive }
    Write-Host "[OK] cau hinh ket noi da doc (host $dbHost, port $dbPort, db live $dbLive - nap vao CSDL TAM $dbName)"

    # CREATE/DROP DATABASE need superuser: the app role has rolcreatedb=f
    # (verified on this server). Same file 2-cai-dat.ps1 uses - the
    # sanctioned superuser credential. Never printed.
    if (-not (Test-Path $SuperFile)) { throw "Khong co file mat khau superuser: $SuperFile - khong tao duoc CSDL tam" }
    $superPass = (Get-Content $SuperFile -Raw).Trim()
    if (-not $superPass) { throw "File superuser rong: $SuperFile" }
    Write-Host "[OK] superuser cho CSDL tam: role $superUser (mat khau tu $SuperFile, khong in ra)"

    # ---- 4. Locate the dump (in the extracted tree, or -Dam override) -
    if ($Dam) {
        if (-not (Test-Path $Dam)) { throw "Dam (-Dam) not found: $Dam" }
        $dumpFile = Get-Item -LiteralPath $Dam   # FileInfo: step 6 uses .FullName
        $baoCao.dam_override = $Dam
        Write-Host "[!] dung dam override: $Dam (doi chung am)" -ForegroundColor Yellow
    } else {
        $dumpFile = Get-ChildItem -Path $staging -Filter '*.dump' -File -Recurse | Select-Object -First 1
        if (-not $dumpFile) {
            $baoCao.kiem += @{ ten = 'unzip_co_dump'; xanh = $false; thong_tin = 'giai nen xong ma khong thay *.dump' }
            throw 'Ban sao khong chua dump - khong co gi de khoi phuc. DUNG LAI.'
        }
        $baoCao.kiem += @{ ten = 'unzip_co_dump'; xanh = $true; thong_tin = "$($dumpFile.Name) ($($dumpFile.Length) bytes)" }
    }

    # ---- 5. Create throwaway database ----------------------------------
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $env:PGPASSWORD = $pgPass
    # CREATE DATABASE runs as the SUPERUSER (the app role cannot create DBs),
    # but the new database is owned by the app role - same split as
    # production (2-cai-dat.ps1: CREATE DATABASE lttplatform OWNER ltt_app).
    # Ownership matters on PG15+: the public schema belongs to the DB owner,
    # so a DB owned by postgres would reject every CREATE from pg_restore.
    # Quoting note: ONE literal quote pair around the SQL (see header comment
    # of step 5v1) - a doubled pair splits the command into bare keywords.
    $sqlTao = "CREATE DATABASE $dbName OWNER $dbUser"
    $kq = Chay-PSQL-QuanTri -ThamSo ("-U `"$superUser`" -h $dbHost -p $dbPort -d postgres -t -A -c `"$sqlTao`"") -GiayToiDa 60
    $rc = $kq.ma; $lo = $kq.stdout; $le = $kq.stderr
    if ($rc -ne 0 -and $le -match 'already exists') {
        # A stale throwaway DB from an earlier aborted rehearsal blocks CREATE:
        # drop EXACTLY that name, then retry once. Never anything else.
        Write-Host "[!] CSDL tam con ton tai tu luot truoc - DROP roi tao lai" -ForegroundColor Yellow
        $sqlDrop = "DROP DATABASE IF EXISTS $dbName WITH (FORCE)"
        $kqD = Chay-PSQL-QuanTri -ThamSo ("-U `"$superUser`" -h $dbHost -p $dbPort -d postgres -t -A -c `"$sqlDrop`"") -GiayToiDa 60
        if ($kqD.ma -ne 0) { Write-Host "[!] DROP CSDL cu that bai (ma $($kqD.ma)): $($kqD.stderr.Substring(0, [math]::Min(200, $kqD.stderr.Length)))" -ForegroundColor Yellow }
        $kq = Chay-PSQL-QuanTri -ThamSo ("-U `"$superUser`" -h $dbHost -p $dbPort -d postgres -t -A -c `"$sqlTao`"") -GiayToiDa 60
        $rc = $kq.ma; $lo = $kq.stdout; $le = $kq.stderr
    }
    if ($rc -eq -1 -and $kq.het_gioi_han) { throw "CREATE DATABASE $dbName het gioi han thoi gian (60s) - Postgres co the dang khong khoi dong. DUNG LAI." }
    if ($rc -ne 0) { throw "CREATE DATABASE $dbName that bai (ma $rc): $($le.Substring(0, [math]::Min(300, $le.Length)))" }
    $baoCao.steps['tao_csd'] = @{ rto_giay = (DoiThoiGian $sw); db = $dbName }
    Write-Host "[OK] CSDL tam $dbName da tao (owner: $dbUser, tao bang $superUser)"

    # ---- 6. pg_restore the dump INTO THE THROWAWAY DB ------------------
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $logRestore = Join-Path $tbTemp 'pg_restore.log'
    # -1: one transaction, rollback all on error (no half-restored database).
    # --no-owner: do not try to become the original owner. No --clean needed:
    # the database is brand new and empty.
    # Hard cap: a 99 MB dump restores in well under 2 minutes; 20 minutes is
    # the absolute bound, after which the child is killed and the rehearsal
    # reports a timeout instead of retrying forever.
    $kq3 = Chay-Process -TienTrinh $pgRestore -ThamSo ("-U `"$dbUser`" -h $dbHost -p $dbPort -d $dbName --no-owner -1 -F c `"$($dumpFile.FullName)`"") -GiayToiDa 1200
    $rc = $kq3.ma
    $err3 = $kq3.stderr
    Set-Content -LiteralPath $logRestore -Value ($kq3.stdout + "`n" + $err3) -Encoding UTF8
    # Count BOTH psql-style (ERROR/WARNING at line start) and pg_restore-style
    # (lowercase, "pg_restore: error:" / "pg_restore: warning:") lines. The old
    # counter only matched the psql form, so a truncated custom-format dump
    # (pg_restore: error: ... end of file) reported "0 canh bao" - a silent
    # green at this step even though the dump did not fully load.
    $coCanhBao = ($err3 -split "`n" | Where-Object { $_ -match '^(WARNING|ERROR)' -or $_ -match 'pg_restore: (warning|error):' } | Measure-Object).Count
    $soERROR = ($err3 -split "`n" | Where-Object { $_ -match '^ERROR' -or $_ -match 'pg_restore: error:' } | Measure-Object).Count
    # A truncated custom-format dump makes pg_restore exit 1 ("completed with
    # warnings") - NOT the fatal 2. So exit code ALONE is a silent-green trap;
    # a restore into a brand-new DB with -1 must return 0 to be clean. rc>=1
    # here means the dump did not fully load, so this step is red on its own
    # (the reconciliation layer is the second, independent net).
    $catDam = ($err3 -match 'end of file')
    if ($kq3.het_gioi_han) {
        $baoCao.kiem += @{ ten = 'pg_restore'; xanh = $false; thong_tin = "pg_restore het gioi han 1200s - da kill, CSDL tam co the chan muon (log: $logRestore)" }
        # Do not throw: let the report be written, then finally cleans up.
    } elseif ($rc -ge 1) {
        $tt = "pg_restore ma $rc, $soERROR loi, $coCanhBao canh bao (log: $logRestore)"
        if ($catDam) { $tt = "pg_restore ma $rc - 'end of file' trong stderr: dump co the bi CAT ho (log: $logRestore)" }
        $baoCao.kiem += @{ ten = 'pg_restore'; xanh = $false; thong_tin = $tt }
        # Do not throw: let the report be written, then finally cleans up.
    } else {
        $baoCao.kiem += @{ ten = 'pg_restore'; xanh = $true; thong_tin = "ma $rc, $coCanhBao canh bao (log: $logRestore)" }
    }
    $baoCao.steps['pg_restore'] = @{ rto_giay = (DoiThoiGian $sw); ma_xuat = $rc; so_error = $soERROR; dam_cothe_cat = $catDam }
    if ($rc -ge 1) { Write-Host "[DO] pg_restore ma $rc, $soERROR loi (log: $logRestore)" -ForegroundColor Red } else { Write-Host "[OK] pg_restore xong (ma $rc, $coCanhBao canh bao)" }

    # ---- 7. Reconciliation checks (python sidecar) --------------------
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $kiemPy = Join-Path $PSScriptRoot 'dien_tap_kiem.py'
    if (-not (Test-Path $kiemPy)) { throw "Thieu dien_tap_kiem.py gan dien_tap_khoi_phuc.ps1: $kiemPy" }
    $venvPy = 'C:\LTTPlatform\venv\Scripts\python.exe'
    if (-not (Test-Path $venvPy)) { $venvPy = 'python' }
    $kq4 = Chay-Process -TienTrinh $venvPy -ThamSo ("`"$kiemPy`" --env-file `"$EnvFile`" --db-name $dbName") -GiayToiDa 300
    $rc4 = $kq4.ma
    $out4 = $kq4.stdout
    $err4 = $kq4.stderr
    $duLieu = @{}
    $kiemPyKetQua = @()
    if ($out4 -match '\{.*\}') {
        try {
            $jsonKiem = ($Matches[0]) | ConvertFrom-Json
            # Normalize to a hashtable: ConvertFrom-Json yields a PSCustomObject
            # (property access) on the green path and an empty object on the
            # failed path. A hashtable makes $duLieu['key'] + ContainsKey work
            # identically in BOTH cases.
            $duLieu = @{}
            $jsonKiem.du_lieu.PSObject.Properties | ForEach-Object { $duLieu[$_.Name] = $_.Value }
            $kiemPyKetQua = @($jsonKiem.kiem)
        } catch { }
    }
    foreach ($k in $kiemPyKetQua) {
        $baoCao.kiem += @{ ten = $k.ten; xanh = $k.xanh; thong_tin = $k.thong_tin }
    }
    if ($kq4.het_gioi_han) {
        $baoCao.kiem += @{ ten = 'phap_doi_chieu'; xanh = $false; thong_tin = 'checker het gioi han 300s - da kill' }
    } elseif ($rc4 -eq 2) {
        $baoCao.kiem += @{ ten = 'phap_doi_chieu'; xanh = $false; thong_tin = "checker loi moi truong: $(($err4 + $out4).Substring(0, [math]::Min(300, ($err4 + $out4).Length)))" }
    }
    # ---- 7b. Schema upgrade after restore (THE restore path) ----------
    # What this check MEASURES (and nothing else): after loading a dump whose
    # alembic_version is BEHIND the code head, does the runbook step
    # 'alembic upgrade head' bring the restored database up to head?
    #
    # Why NOT a version-equality test: a nightly dump taken before a deploy is
    # legitimately behind head (deploy runs the migrations, the dump does not).
    # Equality turns a healthy backup RED and, worse, the equality test GREEN
    # says nothing about the upgrade path at all. The dump is only restorable
    # when (a) its version is at or before head in the chain, AND (b) the
    # upgrade to head actually RUNS on the restored schema. So the check RUNS
    # the upgrade on the throwaway database - the same command the runbook
    # tells an operator to run - and then re-reads alembic_version.
    #
    # RED means the restore path is broken: the upgrade failed, or the dump's
    # version is not an ancestor of head (branch divergence - a restore would
    # need manual schema work).
    #
    # SAFETY: Chay-Alembic pins LTT_DATABASE_URL to the TEMP database inside
    # the child process. The upgrade cannot reach the live database even if
    # the parent environment already carries a LTT_DATABASE_URL.
    #
    # WHICH HEAD: a restored machine runs the DEPLOYED code (C:\LTTPlatform\app,
    # the exact tree the live DB was migrated with - same alembic head).
    # Comparing the dump against a dev tree's head would be measuring the wrong
    # thing: dev may be ahead of (or diverged from) what production actually runs.
    $treeMay = 'C:\LTTPlatform\app'
    $alembicHead = $null
    try {
        $kqA = Chay-Process -TienTrinh $venvPy -ThuMuc $treeMay -ThamSo '-m alembic heads' -GiayToiDa 120
        $alembicOut = $kqA.stdout
        if ($alembicOut -match '([0-9a-f]{12})\s*\(head\)') { $alembicHead = $Matches[1] }
    } catch { }
    if ($alembicHead) {
        # $duLieu is a normalized hashtable (see step 7): ContainsKey is safe
        # under Set-StrictMode, and a failed pg_restore leaves the checker
        # without alembic_dump (the temp DB is empty). Missing = 0 versions.
        if ($duLieu.ContainsKey('alembic_dump')) { $verDump = @($duLieu['alembic_dump']) } else { $verDump = @() }
        if ($verDump.Count -ne 1) {
            $baoCao.kiem += @{
                ten = 'alembic_khop_head'
                xanh = $false
                thong_tin = "alembic_version trong CSDL tam: $($verDump.Count) version ($($verDump -join ', ')) - mong dung 1; doi khi nap dump that bai hoac dump co nhieu version"
            }
        } elseif ($verDump[0] -eq $alembicHead) {
            # Dump already at head: nothing to upgrade, path is trivially fine.
            $baoCao.kiem += @{
                ten = 'alembic_khop_head'
                xanh = $true
                thong_tin = "dump da o head ($alembicHead) - khong can upgrade"
            }
        } else {
            $swUp = [System.Diagnostics.Stopwatch]::StartNew()
            $kqUp = Chay-Alembic -ThamSo 'upgrade head' -GiayToiDa 600
            $rtoUp = DoiThoiGian $swUp
            $thongTin = "dump o $($verDump[0]), head ma = $alembicHead"
            if ($kqUp.het_gioi_han) {
                $baoCao.kiem += @{ ten = 'alembic_khop_head'; xanh = $false; thong_tin = "$thongTin; upgrade head HET GIOI HAN 600s" }
            } else {
                # Verify by re-reading alembic_version from the TEMP DB.
                $kqCur = Chay-PSQL-QuanTri -ThamSo ("-U `"$superUser`" -h $dbHost -p $dbPort -d $dbName -t -A -c `"SELECT version_num FROM alembic_version`"") -GiayToiDa 60
                $verSau = ($kqCur.stdout.Trim())
                $lenL = [math]::Min(300, ($kqUp.stderr.Length))
                if ($kqUp.ma -ne 0) {
                    $baoCao.kiem += @{ ten = 'alembic_khop_head'; xanh = $false; thong_tin = "$thongTin; upgrade THAT BAI (ma $($kqUp.ma)): $($kqUp.stderr.Substring(0, $lenL))" }
                } elseif ($verSau -ne $alembicHead) {
                    $baoCao.kiem += @{ ten = 'alembic_khop_head'; xanh = $false; thong_tin = "$thongTin; upgrade tra ve 0 nhung version sau = '$verSau' (mong $alembicHead)" }
                } else {
                    $baoCao.kiem += @{ ten = 'alembic_khop_head'; xanh = $true; thong_tin = "$thongTin; upgrade head OK sau $rtoUp s, version sau = $verSau" }
                }
            }
            $baoCao.steps['alembic_upgrade'] = @{ rto_giay = $rtoUp; tu = $verDump[0]; den = $alembicHead }
        }
        $baoCao.du_lieu = @{
            alembic_head_ma = $alembicHead
        }
    } else {
        $baoCao.kiem += @{ ten = 'alembic_khop_head'; xanh = $false; thong_tin = 'khong lay duoc alembic head tu ma (venv D:\LTTSTUDIOSAPP) - xem tay' }
    }

    $baoCao.steps['doi_chieu'] = @{ rto_giay = (DoiThoiGian $sw) }

    # ---- 8. Secrets archive: integrity + names only --------------------
    if ($SecretsArchive) {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        if (-not (Test-Path $SecretsArchive)) {
            $baoCao.kiem += @{ ten = 'secrets_zip'; xanh = $false; thong_tin = "khong thay $SecretsArchive" }
        } else {
            $z2 = [IO.Compression.ZipFile]::OpenRead($SecretsArchive)
            try {
                $tenSecrets = @(); $bytesSecrets = 0
                foreach ($e in $z2.Entries) { $tenSecrets += $e.Name; $bytesSecrets += $e.Length }
                $baoCao.kiem += @{
                    ten = 'secrets_zip'
                    xanh = $true
                    thong_tin = "mo duoc, $bytesSecrets bytes, entries: $($tenSecrets -join ', ') (CHIT liet ke TEN, khong giai nen)"
                }
            } finally { $z2.Dispose() }
            $baoCao.steps['secrets'] = @{ rto_giay = (DoiThoiGian $sw) }
        }
    }

    # ---- 9. Verdict -----------------------------------------------------
    $doTatCa = @($baoCao.kiem | Where-Object { -not $_.xanh })
    $baoCao.so_hang = $duLieu
    $toanBoDo.Stop()
    $baoCao.rto_tong_giay = (DoiThoiGian $toanBoDo)
    if ($doTatCa.Count -eq 0) {
        $baoCao.ket_qua = 'XANH'
        Write-BaoCao $baoCao -Xanh
        exit 0
    } else {
        $baoCao.ket_qua = 'DO'
        Write-Host "Cac phap DO:" -ForegroundColor Red
        foreach ($d in $doTatCa) { Write-Host "  - $($d.ten): $($d.thong_tin)" -ForegroundColor Red }
        Write-BaoCao $baoCao
        exit 1
    }
}
catch {
    $baoCao.ket_qua = 'DO_LOI'
    $baoCao.loi = $_.Exception.Message
    $baoCao.rto_tong_giay = (DoiThoiGian $toanBoDo)
    Write-Host "LOI DIEN TAP: $($_.Exception.Message)" -ForegroundColor Red
    Write-BaoCao $baoCao
    exit 1
}
finally {
    # ---- Cleanup: ALWAYS drop the throwaway DB and delete TEMP --------
    # The password may have been set; the DB may exist even when CREATE or
    # restore failed midway. Clean both, swallow errors (best effort), never
    # leave the rehearsal database behind.
    if ($psql -and (Test-Path $psql) -and $dbUser -and $superPass) {
        try {
            # DROP runs as the superuser (the app role cannot drop a DB it
            # does not own, e.g. when the restore left it in a broken state).
            # 30s cap: if Postgres itself is mid-restart, do NOT sit here
            # forever - the DB name is deterministic, a rerun clears it.
            $sqlDropF = "DROP DATABASE IF EXISTS $dbName WITH (FORCE)"
            $kqF = Chay-PSQL-QuanTri -ThamSo ("-U `"$superUser`" -h $dbHost -p $dbPort -d postgres -t -A -c `"$sqlDropF`"") -GiayToiDa 30
            if ($kqF.het_gioi_han) {
                Write-Host "[!] DROP CSDL tam het gioi han 30s (Postgres co the dang restart) - CSDL tam $dbName co the van ton tai, chay lai dien tap se DROP nno" -ForegroundColor Red
            } elseif ($kqF.ma -eq 0) {
                Write-Host "[OK] DROP CSDL tam: $dbName" -ForegroundColor Cyan
            } else {
                Write-Host "[!] DROP CSDL tam that bai (ma $($kqF.ma)) - CSDL tam $dbName co the van ton tai" -ForegroundColor Red
            }
        } catch { Write-Host "[!] khong DROP duoc CSDL tam $dbName - XOA TAY. Loi: $($_.Exception.Message)" -ForegroundColor Red }
    }
    Remove-Item 'Env:PGPASSWORD' -ErrorAction SilentlyContinue
    if (Test-Path $tbTemp) {
        Remove-Item $tbTemp -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] da xoa thu muc tam: $tbTemp" -ForegroundColor Cyan
    }
}
