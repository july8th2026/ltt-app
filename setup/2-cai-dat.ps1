<#
.SYNOPSIS
    Buoc 2 - Cai dat tai cho tu chinh folder nay. Chay lai duoc nhieu lan.

.DESCRIPTION
    Khac voi deploy\windows\install.ps1 (can file zip), script nay cai TRUC
    TIEP tu folder da copy sang. Dung khi ban chep ca thu muc sang may moi.

    Tu dong lam:
      - tao C:\LTTPlatform (data, secrets, logs, backups) va copy code
      - tao venv rieng, cai thu vien
      - TU SINH cac bi mat (session secret, khoa ma hoa token, mat khau admin)
      - tai NSSM neu chua co
      - dang ky va khoi dong dich vu Windows

    An toan khi chay lai: KHONG BAO GIO ghi de du lieu van hanh,
    secrets\app.env, hay khoa ma hoa da co.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [int]$Port = 8100,
    [string]$ServiceName = 'LTTStudioWeb',
    [string]$WorkerServiceName = 'LTTStudioWorker',
    [string]$AdminUser = 'admin'
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
function Head($m) { Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Canh($m) { Write-Host "  [!!] $m" -ForegroundColor Yellow }
function Note($m) { Write-Host "  $m" -ForegroundColor Yellow }

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw 'Can quyen Administrator. Mo PowerShell bang Run as administrator.' }

$src     = Split-Path -Parent $PSScriptRoot

# ------------------------------------------------------- Chan deploy nham cay
# May nay LA production, va buoc duoi day chep CA CAY sang C:\LTTPlatform. Tu
# 31/08 moi phien Claude co the co mot `git worktree` rieng (tools\cay_rieng.py),
# nen tren o D: co nhieu thu muc TRONG GIONG HET NHAU. Deploy nham mot trong so
# chung la loi IM LANG: script chay xong, bao thanh cong, va production chay mot
# nhanh khong ai dinh phat hanh.
#
# Phep phan biet khong can goi git (nen khong dinh bay stderr cua Invoke-Ngoai):
# cay chinh co `.git` la THU MUC, cay lien ket co `.git` la mot TEP tro toi cay
# chung. Da do tren ca ba cay that ngay 31/08.
#
# Khong co `.git` thi CHO QUA -- do la duong cai hop le tu mot ban chep thuan,
# dung nhu .DESCRIPTION o dau tep mo ta.
$gitPath = Join-Path $src '.git'
if ((Test-Path $gitPath) -and -not (Test-Path $gitPath -PathType Container)) {
    throw "Dang cai tu mot CAY RIENG (git worktree): $src`nDeploy chi duoc chay tu cay chinh. Xem: python tools\cay_rieng.py liet-ke"
}

# !! KHOA DEPLOY DAT O DAY, KHONG PHAI O DAU TEP.
#    `test_362::test_chot_dung_TRUOC_moi_thao_tac_ghi` doi chot cay rieng
#    chay TRUOC moi `New-Item`, va khoi duoi day co mot cai. Ban dau toi
#    dat no o dau tep va phep kiem do do NGAY -- dung viec: chan sau khi
#    da tao thu muc trong production la chan muon.
# ------------------------------------------------------------------ KHOA DEPLOY
# !! VI SAO CO KHOI NAY: ngay 01/09 HAI luot deploy chay CHONG NHAU vao
#    `C:\LTTPlatform\app`, cach nhau 56 giay, tu hai phien khac nhau:
#
#        pid=4172   sinh=18:49:39   cha=powershell.exe
#        pid=16056  sinh=18:50:35   cha=nexus.exe
#
#    Khong co gi noi cho ai biet. Ca hai chep cung mot cay nguon nen lan do
#    khong hong tep nao (da doi chieu SHA256 20 tep: 19 khop, 1 lech va tep do
#    la viec dang sua do cua mot phien) -- nhung do la MAY, khong phai thiet ke.
#
# ** VA THU THIEU KHONG CHI LA MOT KHOA. Mot khoa im lang chi bien "ghi de nhau"
#    thanh "treo khong ro vi sao". Nen khoa nay ghi AI GIU, TU LUC NAO, COMMIT
#    NAO -- luot thu hai in duoc cau do ra thay vi doi mu.
#
# !! FAIL-SAFE: moi loi cua chinh khoi nay chi CANH BAO roi di tiep. Mot bug o
#    day khong duoc phep chan moi lan deploy cua ca nhom.
$khoaTep = Join-Path $Root 'deploy.lock'
$daGiuKhoa = $false
try {
    if (-not (Test-Path $Root)) { New-Item -ItemType Directory -Path $Root -Force | Out-Null }
    if (Test-Path $khoaTep) {
        $cu = $null
        try { $cu = Get-Content $khoaTep -Raw | ConvertFrom-Json } catch { $cu = $null }
        $songSot = $false
        if ($cu -and $cu.pid) {
            $songSot = [bool](Get-Process -Id ([int]$cu.pid) -ErrorAction SilentlyContinue)
        }
        if ($songSot) {
            Write-Host ""
            Write-Host "  [DUNG] Mot luot deploy KHAC dang chay." -ForegroundColor Red
            Write-Host "         pid    : $($cu.pid)"
            Write-Host "         tu luc : $($cu.bat_dau)"
            Write-Host "         commit : $($cu.commit)"
            Write-Host "         boi    : $($cu.boi)"
            Write-Host ""
            Write-Host "  Doi no xong roi chay lai. Neu chac chan no da chet thi" -ForegroundColor Yellow
            Write-Host "  xoa $khoaTep roi chay lai." -ForegroundColor Yellow
            exit 2
        }
        Write-Host "  [!] Khoa deploy cu (pid $($cu.pid) khong con song) - lay lai." -ForegroundColor Yellow
        Remove-Item $khoaTep -Force -ErrorAction SilentlyContinue
    }
    $commit = 'khong-doc-duoc'
    try {
        $g = & git -C $PSScriptRoot rev-parse --short HEAD 2>$null
        if ($LASTEXITCODE -eq 0 -and $g) { $commit = $g.Trim() }
    } catch { $commit = 'khong-doc-duoc' }
    # Ghi KHONG BOM, va KHONG dung Set-Content: PowerShell 5.1 chen BOM, va
    # `test_61` chan ca hai ten lenh do trong tep nay. `Write-NoBom` dinh nghia
    # ben duoi nen chua goi duoc o day.
    $than = @{ pid = $PID
               bat_dau = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
               commit = $commit
               boi = "$env:USERNAME@$env:COMPUTERNAME"
             } | ConvertTo-Json -Compress
    [IO.File]::WriteAllText($khoaTep, $than, (New-Object Text.UTF8Encoding($false)))
    $daGiuKhoa = $true
} catch {
    Write-Host "  [!] Khong dat duoc khoa deploy ($_) - di tiep." -ForegroundColor Yellow
}
$appDir  = Join-Path $Root 'app'
$dataDir = Join-Path $Root 'data'
$secrets = Join-Path $Root 'secrets'
$logs    = Join-Path $Root 'logs'
$backups = Join-Path $Root 'backups'
$tools   = Join-Path $Root 'tools'
$venv    = Join-Path $Root 'venv'
$venvPy  = Join-Path $venv 'Scripts\python.exe'

# Ghi file KHONG BOM. PowerShell 5.1 mac dinh chen BOM, va BOM lam
# json.load() vo -> /health/ready tra 503 trong khi dich vu van chay binh
# thuong. Loi nay da that su xay ra o du an nay.
function Write-NoBom($path, $text) {
    [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
}

Head 'Tao cau truc thu muc'
foreach ($d in @($Root, $dataDir, $secrets, $logs, $backups, $tools)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}
Ok "Da tao $Root"

# Tim python SOM: khoi xuat ngay duoi can no de kiem chuoi alembic, va cong
# bien dich ben duoi dung lai cung bien. Truoc day phep tim nay nam trong cong
# bien dich; tach ra vi nay co HAI cho dung no.
$pyKiemSom = $null
foreach ($ung in @($venvPy, 'python', 'py')) {
    if ($ung -and (Get-Command $ung -ErrorAction SilentlyContinue)) { $pyKiemSom = $ung; break }
}

Head 'Nguon ban giao: xuat COMMIT ra thu muc tam'
# ---------------------------------------------------------------------------
# !! VI SAO KHONG CHEP TU CAY SONG NUA -- mot su co that, 08/09/2026 luc 10:11.
#
#    Mot phien Claude khac chay `git stash pop` GIUA cua so robocopy
#    (10:11:07-10:13:37). Production nhan `platform_core/jobs.py` o trang thai
#    TRUNG GIAN: 526 dong, trong khi commit co 478. Deploy bao EXITCODE=0,
#    /health/ready 200, va `dau_van_tay.json` khai dung commit do -- nen KHONG
#    dau hieu nao noi rang dia mang thu khac. Chi `nghiem_thu_deploy` so voi
#    commit moi lo ra, 15 phut sau.
#
# !! VA BA LOP BAO VE DEU KHONG DU. Truoc luot ay toi da: (1) danh sach trang
#    `git status`, (2) kiem `mtime` 60 giay + `compileall`, (3) hoi lai tien
#    trinh sat truoc khi bam. Ca ba deu tra loi ve MOT THOI DIEM; khong lop nao
#    giu duoc cay dung yen suot 2,5 phut robocopy chay sau do.
#
# ** Ket luan cua mot phien khac, va no dung: *cua so ghi cua `git` khong dong
#    duoc tu phia nguoi ghi -- chi dong duoc tu phia nguoi doc.* Nen nguon phai
#    BAT BIEN, khong phai duoc canh chung.
#
# !! `git archive` chu KHONG `git worktree add`: archive khong cham `.git` cua
#    cay song, con worktree thi ghi vao `.git/worktrees`. Voi bon phien chay
#    song song tren cung mot `.git`, khac biet do khong nho.
#
# !! GHI RA TEP TAR ROI GIAI NEN, KHONG NOI ONG. Ong cua PowerShell 5.1 di qua
#    tang van ban va lam HONG du lieu nhi phan. `git archive | tar -x` la mot
#    cai bay im lang.
#
# ---------------------------------------------------------------------------
# !! DANH SACH VAN CHUYEN -- va day la phan suyt lam hong production.
#
#    Do that 08/09: ban xuat commit co 3.650 tep, ban dang chay co 4.556.
#    Trong 912 tep chenh, phan lon la rac (cache cong cu 148, bench/*.png 664)
#    -- nhung MUOI tep la thu production DANG DUNG:
#
#      apps/upscalevideo/vendor/engine/realesrgan-ncnn-vulkan.exe
#      apps/upscalevideo/vendor/engine/vcomp140.dll  +  vcomp140d.dll
#      apps/upscalevideo/vendor/engine/models/*.bin  +  *.param   (6 tep)
#      yolov8n.pt
#      tools/vendor_a11y/axe.min.js
#
#    Chung gitignored CO CHU Y (`.gitignore:176 apps/*/vendor/`, `:180 *.pt`)
#    va duoc doc LUC CHAY:
#      apps/upscalevideo/engine.py:30  _EXE = _ENGINE_DIR / "realesrgan-ncnn-vulkan.exe"
#
# ** Mot ban `git archive` THUAN se lam app `upscalevideo` chet tren production,
#    va chet IM LANG: EXITCODE=0, /health/ready 200, va `nghiem_thu_deploy`
#    bao "thieu 0" vi no CHI DEM TEP .py.
#
# ** Nen danh sach duoi day khong phai mot tien ich -- no la HOP DONG. No noi
#    ra mot su that truoc nay chi dung NHO TINH CO: "nhung duong nay gitignored
#    nhung production can". Them mot vendor moi ma quen khai vao day thi
#    `tests/test_505_nguon_ban_giao.py` do, chu production khong thieu tep.
#
# !! `tools\vendor_a11y\axe.min.js` KHONG o day, du no cung gitignored va cung
#    la nhi phan. Do that (grep toan kho): nguoi doc DUY NHAT cua no la
#    `tools/check_a11y.py`, va cong cu do chay TU CAY NGUON TRUOC khi deploy --
#    production khong bao gio doc no.
#
# ** Khai them mot duong khong ai can la lam danh sach dai ra ma khong chac
#    hon, va moi dong thua se duoc doc nhu mot rang buoc THAT. Danh sach nay
#    chi dung khi no chi chua thu production DOC LUC CHAY.
$VAN_CHUYEN = @(
    'apps\*\vendor',
    'yolov8n.pt'
)

$srcChep  = $src          # duong lui: cay song, y nhu truoc 08/09
$xuatTam  = $null
$shaXuat  = ''
if (Test-Path $gitPath -PathType Container) {
    try { $shaXuat = (& git -C $src rev-parse HEAD 2>$null) } catch { $shaXuat = '' }
    if ($LASTEXITCODE -ne 0) { $shaXuat = '' }
    $global:LASTEXITCODE = 0
}
if ($shaXuat) {
    $shaXuat = $shaXuat.Trim()
    $xuatTam = Join-Path ([IO.Path]::GetTempPath()) ("ltt-xuat-" + $shaXuat.Substring(0, 12))
    if (Test-Path $xuatTam) { Remove-Item $xuatTam -Recurse -Force }
    New-Item -ItemType Directory -Path $xuatTam -Force | Out-Null
    $tarTam = Join-Path ([IO.Path]::GetTempPath()) ("ltt-xuat-" + $shaXuat.Substring(0, 12) + ".tar")
    Invoke-Ngoai { & git -C $src archive --format=tar -o $tarTam $shaXuat }
    if (-not (Test-Path $tarTam)) { throw "git archive khong tao duoc $tarTam" }
    Invoke-Ngoai { & tar -xf $tarTam -C $xuatTam }
    Remove-Item $tarTam -Force -ErrorAction SilentlyContinue
    $soXuat = (Get-ChildItem $xuatTam -Recurse -File).Count
    if ($soXuat -lt 100) { throw "Ban xuat chi co $soXuat tep - khong hop ly, DUNG deploy." }
    Ok "Xuat commit $($shaXuat.Substring(0,12)): $soXuat tep (nguon BAT BIEN)"

    # Chep cac duong DA KHAI tu cay song vao ban xuat. Chung la nhi phan vendor
    # khong ai soan, nen cua so dua o day gan bang khong -- khac han ca cay.
    foreach ($mau in $VAN_CHUYEN) {
        foreach ($m in (Get-ChildItem (Join-Path $src $mau) -ErrorAction SilentlyContinue)) {
            $tuongDoi = $m.FullName.Substring($src.Length).TrimStart('\')
            $dich = Join-Path $xuatTam $tuongDoi
            $chaDich = Split-Path -Parent $dich
            if (-not (Test-Path $chaDich)) { New-Item -ItemType Directory -Path $chaDich -Force | Out-Null }
            if ($m.PSIsContainer) {
                $rcV = robocopy $m.FullName $dich /E /NFL /NDL /NJH /NJS /NP /R:2 /W:2
                if ($LASTEXITCODE -ge 8) { throw "robocopy van chuyen '$tuongDoi' loi (ma $LASTEXITCODE)" }
                $global:LASTEXITCODE = 0
            } else {
                Copy-Item $m.FullName $dich -Force
            }
            Ok "Van chuyen: $tuongDoi"
        }
    }

    # !! CHUOI ALEMBIC PHAI GIAI DUOC TRONG BAN XUAT -- chan TRUOC Stop-Service.
    #
    #    Do that 08/09: mot migration da commit (`e7b2c94a1d38`) co cha la mot
    #    tep CHUA THEO DOI. Bo tep cha ra khoi cay thi `ScriptDirectory` nem
    #    `KeyError` NGAY khi dung -- tuc alembic khong giai duoc head NAO CA.
    #    Voi nguon la `git archive`, moi tep chua commit deu vang mat, nen mot
    #    chuoi phu thuoc vao tep untracked se chet o `alembic upgrade head` --
    #    va buoc do chay SAU `Stop-Service`.
    if ($pyKiemSom) {
        $maAl = 0
        $maNguon = @'
import sys
from alembic.config import Config
from alembic.script import ScriptDirectory
cfg = Config(); cfg.set_main_option("script_location", sys.argv[1])
try:
    print("heads:", ScriptDirectory.from_config(cfg).get_heads())
except Exception as e:
    print("LOI:", type(e).__name__, e); sys.exit(1)
'@
        $tepAl = Join-Path ([IO.Path]::GetTempPath()) 'ltt-kiem-alembic.py'
        Write-NoBom $tepAl $maNguon
        $kqAl = & $pyKiemSom $tepAl (Join-Path $xuatTam 'alembic') 2>&1 | Out-String
        $maAl = $LASTEXITCODE
        $global:LASTEXITCODE = 0
        Remove-Item $tepAl -Force -ErrorAction SilentlyContinue
        if ($maAl -ne 0) {
            Write-Host $kqAl -ForegroundColor Red
            throw ("Chuoi alembic KHONG giai duoc trong ban xuat. Gan nhu chac chan " +
                   "co mot migration CHUA COMMIT dang lam cha cho mot migration da " +
                   "commit. Commit no roi chay lai. DUNG deploy, dich vu chua bi dung.")
        }
        Ok "Chuoi alembic giai duoc trong ban xuat"
    }

    $srcChep = $xuatTam
} else {
    Canh "Khong doc duoc commit - chep TU CAY SONG (duong lui). Ban giao co the chua tep chua commit."
}

Head 'Kiem ma nguon truoc khi dong vao ban dang chay'
# ---------------------------------------------------------------------------
# VI SAO CHOT NAY O DAY, VA O TRUOC Stop-Service
#
# Deploy la robocopy + alembic. Truoc 2026-08-25 KHONG co gi chan mot tep .py
# cut: neu ai do dang ghi do mot tep luc deploy chay, ban cut duoc chep thang
# sang production va dich vu khong khoi dong lai duoc.
#
# Khong phai gia thuyet. Ngay 25/08 gate bao [FAIL] "bien dich duoc" mot nhip
# roi tu xanh lai, khong ai sua gi o giua -- no bat dung luc mot tep dang duoc
# ghi. Hai phien Claude lam song song tren cung cay nguon, va do la trang thai
# binh thuong cua du an nay.
#
# Chot chay TRUOC `Stop-Service`: hong o day thi dich vu VAN DANG CHAY va
# khong ai mat gi. Dat sau do thi ta da tu tay tao ra downtime roi moi phat
# hien khong deploy duoc.
$pyKiem = $pyKiemSom
if ($pyKiem) {
    # compileall: doc va bien dich MOI tep .py trong cay nguon. -q chi in loi.
    # /XD cua robocopy o duoi khong ap dung o day nen loai tay may thu muc lon.
    # !! KHONG DUNG ONG POWERSHELL O DAY, VA PHAI CO HAN CHO.
    #
    #    Ban cu la:
    #        & $pyKiem @bo 2>&1 | Out-String -OutVariable kqKiem | Out-Null
    #
    #    Ngay 01/09 buoc nay TREO hai lan (18:27 va 20:08), moi lan hon 20 phut.
    #
    #    CO CHE, do duoc day du bang HAI phep do cua hai phien ghep lai:
    #
    #      1. PowerShell (11408) goi python (13212), stdout NOI ONG
    #      2. python 13212 chay `compileall -j 0`, sinh 20 worker
    #         `multiprocessing` -- chung THUA KE dau ghi cua ong
    #      3. python 13212 THOAT
    #         => 11408 khong con tien trinh con python nao
    #            (do luc 20:33: `tien trinh con: KHONG CO`)
    #      4. 20 worker MO COI van song va van giu dau ghi ong mo
    #         (do luc 21:0x: 20 python, deu ppid=13212, va 13212 DA CHET)
    #      5. `Out-String` cho EOF tren ong -- EOF KHONG BAO GIO TOI
    #      6. PowerShell cho vinh vien: CPU 0,36s, thread o `ExecutionDelay`
    #
    # !! DIEU KIEN KICH HOAT KHONG PHAI `-j 0`. No la **cha chet trong khi con
    #    con song**. Ai doc den day roi bo `-j 0` de "sua" thi sua nham cho, va
    #    ai khoi phuc lai duong ong thi mo lai dung cai lo nay.
    #
    # ** VA VI SAO NO KHONG TAI HIEN DUOC: toi chay ba bien the (-j 0 co ong /
    #    -j 0 ra tep / mot luong co ong) tren TOAN cay, dung python cua venv --
    #    ca ba xong trong ~9 giay. Vi trong phep thu do tien trinh cha KHONG
    #    chet bat thuong: worker thoat sach, EOF toi, moi thu binh thuong.
    #    Mot loi chi xuat hien khi mot tien trinh chet SAI CACH thi khong tai
    #    hien theo y muon duoc -- va do khong phai ly do de khong sua no.
    #
    # ** BO ONG LA BAN VA DUNG, va dung vi mot ly do manh hon "ne mot deadlock":
    #    KHONG CO ONG THI KHONG CO EOF DE CHO, bat ke con co mo coi hay khong.
    #    Han cho 300 giay lo not moi bien the khac cua cung mot ho.
    #
    # !! VI SAO HAN CHO QUAN TRONG HON CA NGUYEN NHAN: buoc nay chay SAU khi da
    #    giu khoa deploy. Mot buoc khong co han cho ma treo thi giu khoa VO HAN
    #    -- tuc no bien mot loi "cham" thanh mot loi "chan ca nhom". Do la loi
    #    cua chinh khoa nay neu khong sua.
    # !! CHAY TREN `$srcChep` (ban xuat), KHONG tren `$src` (cay song). Hai he
    #    qua, va ca hai deu la ban va cho mot su co that:
    #
    #      1. Pham vi thu hep con DUNG thu sap giao. Truoc 08/09 no quet ca
    #         `.claude/worktrees/` -- sau checkout cua bon phien -- nen mot tep
    #         dang duoc ghi o cay NGUOI KHAC chan duoc deploy. Da xay ra luc
    #         09:43: `tac_vu.py` cua mot phien khac bi doc giua luc ghi.
    #      2. Thong diep "Co tep .py KHONG bien dich duoc" LAN DAU TIEN noi dung
    #         nghia. Truoc day no co the nghia la "co nguoi dang go phim", va
    #         nguoi doc di tim mot tep hong khong ton tai.
    #
    # ** `-j 0` giu nguyen: no la so LOI (10 tren may nay), va nay chi tren MOT
    #    cay chu khong phai sau cay. Bo `-j 0` la sua nham cho -- xem chu thich
    #    dai o duoi ve nguyen nhan that cua vu treo 01/09 (cha chet, con mo coi).
    $bo = @('-m', 'compileall', '-q', '-j', '0',
            '-x', '(node_modules|\.git|\.venv|venv|__pycache__|dist|build)',
            $srcChep)
    # !! DUNG .NET Process TRUC TIEP, KHONG DUNG `Start-Process -PassThru`.
    #
    #    Do that 01/09: voi `Start-Process -PassThru`, `$tt.ExitCode` tra ve
    #    RONG ca khi tien trinh thanh cong lan khi that bai. Va trong PowerShell
    #    `$null -ne 0` la TRUE, nen phep so sanh ngay duoi se NEM O MOI LUOT --
    #    ke ca tren mot cay hoan toan lanh.
    #
    # ** Tuc ban va chong-treo dau tien cua toi se LAM HONG MOI LUOT DEPLOY.
    #    No bi bat boi `tmp/thu_khoi_bien_dich.ps1`, va chi vi phep thu do doi
    #    exit code phai BANG 0 chu khong chi doi "khong treo". Mot phep thu chi
    #    hoi "co treo khong" se cho ban va nay di qua.
    # !! `StartInfo.ArgumentList` va `Kill($true)` CHI CO tren .NET Core.
    #    Deploy chay bang Windows PowerShell 5.1 (.NET Framework), noi
    #    `ArgumentList` la NULL. Ban dau toi dung no; hau qua la python khoi
    #    dong KHONG DOI SO, vao REPL, va treo dung 300 giay cho stdin --
    #    tuc toi vua tu tao lai chinh trieu chung dang di sua.
    #
    # ** Nen o day dung `.Arguments` (mot chuoi), va moi doi so duoc boc nhay
    #    kep de duong dan co dau cach va regex co `|` khong bi cat.
    $tt = New-Object System.Diagnostics.Process
    $tt.StartInfo.FileName = $pyKiem
    $tt.StartInfo.Arguments = (($bo | ForEach-Object { '"' + $_ + '"' }) -join ' ')
    $tt.StartInfo.UseShellExecute = $false
    $tt.StartInfo.RedirectStandardOutput = $true
    $tt.StartInfo.RedirectStandardError = $true
    $null = $tt.Start()
    # Doc CA HAI luong bang tac vu bat dong bo TRUOC khi cho: doc tuan tu mot
    # luong roi moi doc luong kia la mot deadlock kinh dien khi luong chua doc
    # day bo dem cua no.
    $tOut = $tt.StandardOutput.ReadToEndAsync()
    $tErr = $tt.StandardError.ReadToEndAsync()
    if (-not $tt.WaitForExit(300000)) {
        try { $tt.Kill() } catch { }   # `Kill($true)` la .NET Core, khong co o 5.1
        throw ("Buoc bien dich .py TREO qua 300 giay va da bi dung. " +
               "DUNG deploy, dich vu chua bi dung. Khoa deploy khong bi " +
               "xoa o day, nhung tien trinh nay chet nen luot sau se nhan " +
               "ra no la khoa CU va tu lay lai.")
    }
    $kqKiem = $tOut.Result + $tErr.Result
    $maKiem = $tt.ExitCode
    $tt.Dispose()
    if ($maKiem -ne 0) {
        Write-Host $kqKiem -ForegroundColor Red
        # !! PHAN BIET "KHONG CO PYTHON" VOI "MA HONG" -- hai thu nay sua o hai
        #    noi khac han, va thong diep cu goi ca hai la "ma hong".
        #
        #    Do that 01/09: chay voi mot -Root chua co venv, `Get-Command python`
        #    tra ve STUB cua Windows Store, stub in "No installed Python found!"
        #    roi thoat khac 0 -- va script bao "Co tep .py KHONG bien dich duoc".
        #    Nguoi doc se di tim mot tep .py hong khong ton tai.
        #
        # ** No nguy hiem nhat o LAN CAI DAU TIEN, dung luc chua co venv va dung
        #    luc nguoi cai it thong tin nhat de cai chinh.
        if ($kqKiem -match 'No installed Python found|was not found') {
            throw ("KHONG TIM THAY PYTHON dung duoc (`$pyKiem = $pyKiem). " +
                   "Tren Windows, `python` co the tro toi stub cua Microsoft Store. " +
                   "Cai Python that roi chay lai. DAY KHONG PHAI loi ma nguon.")
        }
        throw "Co tep .py KHONG bien dich duoc. DUNG deploy, dich vu chua bi dung."
    }
    Ok "Toan bo .py bien dich duoc"
    $global:LASTEXITCODE = 0
} else {
    Canh "Khong tim thay python de kiem ma nguon - BO QUA chot bien dich"
}

Head 'WhisperX sidecar rieng'
# Sidecar nay chi phuc vu autosubvideo.
#
# !! CHUYEN LEN DAY 2026-08-30, TRUOC MOI `Stop-Service`.
#
#    Chu thich cu ngay tai cho nay da ghi: *"script da dung dich vu o tren,
#    nen mot loi o day de production nam im"* - tuc no BIET minh nam trong cua
#    so downtime, va chi ne bang try/catch. Ne mot loi thi production van nam
#    trong suot thoi gian no tai ve (torch ~3,5 GB). Chuyen di thi khong.
#
#    Cung ngay do, khoi cai `vieneu-venv` mac dung loi ay va lam production
#    nam 19 phut. `test_45::test_viec_dai_khong_nam_trong_cua_so_ngung_dich_vu`
#    gio chan ca hai.
#
#    Ngay 2026-08-05 buoc nay nem loi (xem `Test-Py` trong chinh tep sidecar)
#    va bi bo qua -> `whisperx-venv` rong toi tan 30/08, va `autosubvideo` chay
#    nhanh du phong `faster-whisper`, MAT can chinh theo tu. No co ghi nhan
#    (`alignment_status: fallback_unaligned`) nhung khong ai doc nhan do.
#
#    Goi tu `$src` chu khong `$appDir`: `$appDir` chi co noi dung moi sau
#    robocopy, ma robocopy thi sau Stop-Service.
# Khi may DA co LTT_WHISPERX_PYTHON thi bo qua duoc: chi autosubvideo giam
# chuc nang. Khi CHUA co (cai moi) thi van phai dung, neu khong auto-sub hong
# am tham.
$whisperPy = $null
try {
    $whisperOut = @(& (Join-Path $src 'deploy\windows\install-whisperx-sidecar.ps1') `
        -Root $Root -ReleaseDir $src -PythonExe 'python')
    $whisperPy = $whisperOut[-1]
} catch {
    Note "WhisperX sidecar loi: $($_.Exception.Message)"
}
if (-not $whisperPy) {
    $envProbe = Join-Path $secrets 'app.env'
    $hasWhisper = (Test-Path $envProbe) -and
        ((Get-Content $envProbe -Raw) -match '(?m)^LTT_WHISPERX_PYTHON=')
    if (-not $hasWhisper) { throw 'Khong cai duoc WhisperX sidecar va app.env chua co LTT_WHISPERX_PYTHON' }
    Note 'BO QUA WhisperX sidecar - app.env da co LTT_WHISPERX_PYTHON cu.'
    Note 'autosubvideo co the giam chuc nang. Chay lai sidecar rieng khi ranh.'
} else {
    Ok 'WhisperX CUDA sidecar da san sang'
}

Head 'Venv giong noi (LTT VOICE) - CAI TRUOC KHI DUNG DICH VU'
# !! VI SAO KHOI NAY O DAY - TRUOC CA `Head 'Copy ma nguon'`.
#
#    Ngay 2026-08-30 no nam o duoi, SAU `Stop-Service`. Mot lan tai ve ~6 GB
#    (torch cu128) do dai bang dung mot khoang production sap. Tien trinh nang
#    quyen chet trong luc tai => production nam 19 phut, `EXITCODE` rong.
#
#    Chu thich o `Head 'Copy ma nguon'` da canh bao san dieu nay: tac gia loai
#    700 MB node_modules chi de RUT NGAN cua so do, va ghi rang mot lan treo
#    robocopy da lam production ngung 20 phut ngay 2026-08-05. Toi tha 6 GB vao
#    dung cua so ay.
#
#    Chay tu `$src` chu khong `$appDir`: `$appDir` chi co noi dung moi SAU
#    robocopy, ma robocopy thi sau Stop-Service. Ban cai trong cay nguon giong
#    het, va no cai mot venv NGOAI `app\` nen khong quan trong ban nao goi.
#
# !! BAI HOC, va no rong hon LTT VOICE: **khong dat mot viec DAI va CO THE HONG
#    vao giua cua so ngung dich vu.** Cai venv khong can dich vu nao dung ca; no
#    o duoi chi vi no "thuoc ve" app do trong dau nguoi viet. Su gan gui ve mat
#    khai niem khong phai ly do de xep thu tu thi hanh.
#
#    Cai o day thi cung mot lan tai ve 6 GB do KHONG lam ai mat mot giay dich vu,
#    va neu no hong thi buoc dang ky dich vu ben duoi tu bo qua (`$voicePy` rong).
#
# LTT VOICE chay VieNeu-TTS v3 Turbo tren GPU may nay (Q117/Q118). Khac ba dich vu
# kia, no chay tu MOT VENV CACH LY: vieneu ghim transformers==4.57.6 va
# torch==2.8.0+cu128; cai de len venv nen tang se ha cap torch Blackwell va lam
# hong moi app GPU khac. Cung ly do da sinh ra whisperx-venv.
#
# LTT_VOICE_VENV_ROOT: venv nay ~8 GB. Bo trong thi dung $Root.
$VoiceServiceName = 'LTTStudioVoice'
$voiceVenvRoot = $env:LTT_VOICE_VENV_ROOT
if (-not $voiceVenvRoot) { $voiceVenvRoot = $Root }
$voicePy = ''
try {
    $out = @(& (Join-Path $src 'deploy\windows\install-vieneu-sidecar.ps1') `
             -Root $Root -ReleaseDir $src -VenvRoot $voiceVenvRoot -PythonExe 'python')
    $voicePy = ($out | Where-Object { $_ -like '*python.exe' } | Select-Object -Last 1)
} catch {
    # Khong chan ca ban cai vi mot app: nen tang van chay duoc khong co giong noi,
    # va the app se tu hien "can thiet lap". Nhung PHAI in ro, khong nuot.
    Write-Host "  [BO QUA] Khong cai duoc vieneu-venv: $($_.Exception.Message)" -ForegroundColor Yellow
}

Head 'Copy ma nguon'
# Dung dich vu truoc khi dong vao app\. Khi chay LAI tren may dang phuc vu that,
# python.exe cua service khoa file trong app\ -> Move-Item/robocopy that bai
# (loi "being used by another process"). Script se cai lai + khoi dong o cuoi.
# !! MOI dich vu co AppDirectory = app\ deu PHAI co trong danh sach nay.
#
#    `Move-Item` khong xoay duoc mot thu muc dang bi mot tien trinh mo. Bo sot
#    MOT dich vu la du: no giu app\, Move-Item nem IOException, va script chet
#    NGAY SAU khi da dung ba dich vu kia -> trang cong khai tra 502 cho toi khi
#    co nguoi bat lai bang tay.
#
#    Da xay ra that 31/08/2026: `LTTStudioVoice` duoc them (Q117) nhung khong
#    duoc them vao day. Deploy chay toi 09:36:46 roi dung; production 502 khoang
#    ba phut. Trieu chung nhin nhu mot loi quyen han, khong nhu mot dich vu bi
#    bo sot.
#
#    Nen danh sach o day duoc DAN XUAT tu chinh cac bien ten dich vu, va
#    `tests/test_45_deploy_scripts.py` chot rang moi dich vu duoc nssm dang ky
#    trong tep nay deu co mat. Them dich vu moi ma quen -> gate do, khong phai
#    production do.
$DichVuGiuAppDir = @($WorkerServiceName, $ServiceName, 'LTTStudioCodex',
                     $VoiceServiceName)
foreach ($svc in $DichVuGiuAppDir) {
    Stop-Service $svc -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
# Giu ban truoc de rollback duoc.
if (Test-Path $appDir) {
    $prev = Join-Path $Root 'app.previous'
    if (Test-Path $prev) { Remove-Item $prev -Recurse -Force }
    Move-Item $appDir $prev
    Ok "Ban cu chuyen sang app.previous (dung de rollback)"
}
New-Item -ItemType Directory -Path $appDir -Force | Out-Null
# /XD: khong copy du lieu van hanh, bi mat, cache. Chung song o ngoai app\
# (ADR-009) de cap nhat code khong dong vao du lieu. Them ca thu muc chi
# phuc vu phat trien: production khong chay Node/Vite/Playwright/pytest, va
# node_modules + .playwright-cli + tmp la ~700 MB rac keo dai cua so downtime.
# /R:2 /W:2 la BAT BUOC. Mac dinh robocopy la /R:1000000 /W:30 - mot file bi
# khoa hay ACL hong se treo VO HAN, trong khi dich vu DA bi dung o tren. Loi
# do da that su lam production ngung 20 phut ngay 2026-08-05.
$rc = robocopy $srcChep $appDir /E /NFL /NDL /NJH /NJS /NP /R:2 /W:2 `
      /XD data secrets logs .venv venv __pycache__ .pytest_cache .git dist build temp_videos `
         node_modules .playwright-cli .playwright-mcp .claude test-results tmp `
      /XF *.pyc *.log
if ($LASTEXITCODE -ge 8) { throw "robocopy loi (ma $LASTEXITCODE)" }
$global:LASTEXITCODE = 0
$n = (Get-ChildItem $appDir -Recurse -File).Count
Ok "Da copy $n file vao $appDir"

# ---- Dau van tay: BAN NAO dang chay ----------------------------------------
#
# .git bi loai khoi robocopy o tren (co y: ~1 GB lich su ma production khong
# dung). Nen ban deploy KHONG tra loi duoc "toi la commit nao" bang git, va
# ngay 05/09/2026 dieu do ton gan tron mot buoi: kho ghi 100.000, web hien
# 1.500, va cach duy nhat de biet vi sao la so md5 cua /static/voice.js giua
# hai thu muc. Ben deploy GHI ra; server/routes/health.py chi doc.
#
# !! Write-NoBom, KHONG Out-File. Quy tac 1 cua CLAUDE.md: PowerShell 5.1 chen
#    BOM, json.load() vo, va /health/ready tra 503 trong khi dich vu van chay.
#    Loi do da that su lam production sap o du an nay.
$vanTay = Join-Path $appDir "dau_van_tay.json"
$sha = ""
try { $sha = (& git -C $src rev-parse HEAD 2>$null) } catch { $sha = "" }
if ($LASTEXITCODE -ne 0) { $sha = "" }
$global:LASTEXITCODE = 0
if ($sha) {
    # !! GHI CA NOI DUNG DA GIAO, KHONG CHI COMMIT DINH GIAO.
    #
    #    Su co 08/09 10:11: marker khai `c795ebc7` trong khi dia mang mot ban
    #    `jobs.py` 526 dong (commit co 478). Marker KHONG SAI theo luat cu cua
    #    no -- no ghi commit ma deploy DINH giao. Nhung nguoi doc hieu no la
    #    "dia dang mang commit nay", va rollback sau do se khoi phuc mot ban
    #    ban ma /health/version bao la hop le. Sai so day ve phia YEN TAM.
    #
    # ** `noi_dung` = sha256 cua danh sach (duong dan + kich thuoc) da chep. No
    #    khong doi hoi doc noi dung tep nen re, va no DU de phat hien mot ban
    #    giao khac voi ban giao khac. Voi nguon `git archive` + danh sach van
    #    chuyen, hai lan deploy cung commit se cho cung `noi_dung`.
    #
    # ** `nguon` noi ban giao nay den TU DAU. `xuat` = bat bien; `cay-song` =
    #    duong lui, va khi do `commit` chi la mot LOI KHAI, khong phai bang chung.
    $dsTep = Get-ChildItem $appDir -Recurse -File | Sort-Object FullName
    $chuoi = ($dsTep | ForEach-Object {
        $_.FullName.Substring($appDir.Length).TrimStart('') + '|' + $_.Length
    }) -join "`n"
    $sha256 = [Security.Cryptography.SHA256]::Create()
    $bam = ($sha256.ComputeHash([Text.Encoding]::UTF8.GetBytes($chuoi)) |
            ForEach-Object { $_.ToString('x2') }) -join ''
    $sha256.Dispose()
    $obj = [ordered]@{ commit   = $sha.Trim()
                       nguon    = $(if ($xuatTam) { 'xuat' } else { 'cay-song' })
                       so_tep   = $dsTep.Count
                       noi_dung = $bam
                       luc      = (Get-Date).ToString("s") }
    Write-NoBom $vanTay ($obj | ConvertTo-Json -Compress)
    Ok "Dau van tay: $($sha.Substring(0,12)) nguon=$($obj.nguon) noi_dung=$($bam.Substring(0,12))"
} else {
    # Khong doc duoc git thi XOA marker cu. Mot marker cu la mot cau tra loi
    # SAI ma trong nhu that - te hon han khong co cau tra loi nao.
    if (Test-Path $vanTay) { Remove-Item $vanTay -Force }
    Canh "Khong doc duoc commit tu cay nguon - /health/version bao khong-ro"
}

# Canvas is prebuilt in the release with pinned Node 22.12.0. Production does
# not run Node/Vite and must never depend on a development server.
$canvasManifest = Join-Path $appDir 'server\static\agent-canvas\.vite\manifest.json'
$canvasMeta = Join-Path $appDir 'server\static\agent-canvas\build-meta.json'
if (-not (Test-Path $canvasManifest) -or -not (Test-Path $canvasMeta)) {
    throw 'Release thieu Agent Canvas production bundle'
}
Ok 'Agent Canvas production bundle da co (khong can Node tren server)'
$autosubManifest = Join-Path $appDir 'server\static\autosub-studio\.vite\manifest.json'
$autosubMeta = Join-Path $appDir 'server\static\autosub-studio\build-meta.json'
if (-not (Test-Path $autosubManifest) -or -not (Test-Path $autosubMeta)) {
    throw 'Release thieu Auto Sub Studio production bundle'
}
Ok 'Auto Sub Studio production bundle da co (khong can Node tren server)'

# Don ban xuat: no da lam xong viec. Giu lai chi ton dia, va mot thu muc tam
# mang ten commit rat de bi doc nham la "ban dang chay".
if ($xuatTam -and (Test-Path $xuatTam)) {
    Remove-Item $xuatTam -Recurse -Force -ErrorAction SilentlyContinue
}

Head 'Tai nguyen nguon di kem code'
# data\translations va data\assets la TAI NGUYEN NGUON (ban dich giao dien,
# logo TikTok cho audit), khong phai du lieu van hanh - phai di theo code.
foreach ($sub in @('translations', 'assets')) {
    $s = Join-Path $src "data\$sub"
    if (Test-Path $s) {
        $d = Join-Path $dataDir $sub
        robocopy $s $d /E /NFL /NDL /NJH /NJS /NP | Out-Null
        $global:LASTEXITCODE = 0
        Ok "data\$sub"
    }
}

Head 'Moi truong Python'
if (-not (Test-Path $venvPy)) {
    & python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Tao venv that bai' }
    Ok 'Da tao venv'
} else { Ok 'venv da co' }
Invoke-Ngoai { & $venvPy -m pip install --upgrade pip --quiet }
if ($LASTEXITCODE -ne 0) { throw "Loi khi chay: & $venvPy -m pip install --upgrade pip --quiet" }
Invoke-Ngoai { & $venvPy -m pip install -r (Join-Path $appDir 'requirements.txt') --quiet }
if ($LASTEXITCODE -ne 0) { throw "Loi khi chay: & $venvPy -m pip install -r (Join-Path $appDir 'requirements" }
Invoke-Ngoai { & $venvPy -m pip install -r (Join-Path $appDir 'requirements-server.txt') --quiet }
if ($LASTEXITCODE -ne 0) { throw "Loi khi chay: & $venvPy -m pip install -r (Join-Path $appDir 'requirements" }
Ok 'Da cai thu vien'

# TAO CLIP NGAN (engine cutclipshort) can torch GPU. KHONG de trong requirements vi
# pip keo ban CPU tu PyPI; card Blackwell (RTX 50xx) BAT BUOC torch cu128. Chi cai khi
# torch chua co / chua thay CUDA (tranh tai lai ~2.5GB moi lan deploy).
Invoke-Ngoai { & $venvPy -c "import importlib.util,sys; sys.exit(0) if importlib.util.find_spec('torch') else sys.exit(1)" 2>$null | Out-Null; $hasTorch = ($LASTEXITCODE -eq 0) }
$cudaOk = $false
if ($hasTorch) { & $venvPy -c "import torch,sys; sys.exit(0) if torch.cuda.is_available() else sys.exit(1)" 2>$null; $cudaOk = ($LASTEXITCODE -eq 0) }
if ($cudaOk) {
    Ok 'torch CUDA da san sang - GIU NGUYEN'
} else {
    Note 'Cai torch cu128 (Blackwell) - lan dau ~2.5GB, cho chut'
    Invoke-Ngoai { & $venvPy -m pip install "torch>=2.7" "torchaudio>=2.7" "torchvision>=0.22" --index-url https://download.pytorch.org/whl/cu128 --quiet }
    Invoke-Ngoai { & $venvPy -c "import torch,sys; sys.exit(0) if torch.cuda.is_available() else sys.exit(1)" 2>$null }
    if ($LASTEXITCODE -eq 0) { Ok 'Da cai torch cu128 (CUDA OK)' }
    else { Note 'CANH BAO: torch chua thay CUDA - Tao Clip ngan se chay CPU rat cham (kiem tra driver NVIDIA / dung card Blackwell can cu128)' }
}

Head 'Cau hinh van hanh'
# BUOC TAO data\config.json DA BO 2026-08-25 (Q108).
#
# Tep do la cau hinh cua app socialbot (Meta App ID, Sheet ID, ten cot, chong
# spam) va app do da bi go han. Nen tang KHONG doc tep cau hinh nao luc khoi
# dong nua: ho so moi truong suy ra tu LTT_ENV, moi thu con lai nam trong
# secrets\app.env.
#
# Tep cu con nam lai trong data\ tren may da cai thi khong sao - khong tien
# trinh nao mo no. Xoa la viec cua chu san pham, khong phai cua bo cai.
Ok 'Khong con buoc cau hinh - nen tang doc bien moi truong, khong doc tep'

Head 'Siet quyen thu muc bi mat'
# !!!! DONG NAY TRUOC 2026-08-27 KHONG LAM DUOC DIEU NO IN RA.
#
#   icacls $secrets /inheritance:r /grant:r "SYSTEM:..." "Administrators:..."
#
# `/inheritance:r` bo cac ACE THUA KE. `/grant:r` thay quyen cua nhung chu the
# DUOC LIET KE. Khong cai nao dung toi mot ACE TUONG MINH cua chu the khac -
# no song sot nguyen ven, va bo cai van in 'Ok'.
#
# Do duoc 27/08 tren may dang chay: secrets\ co ACE tuong minh cho tai khoan
# nguoi dung, tuc app.env - noi giu khoa phien, khoa ma hoa token, hash mat khau
# admin, token Proxmox, khoa Vultr - nam duoi mot ACL yeu hon cau ta vua in ra.
#
# Cach dung: LIET KE roi XOA tung chu the ngoai danh sach, roi KIEM LAI. Mot
# buoc bao mat khong tu kiem la mot buoc se noi doi vao dung ngay no that bai.
$chuThePhep = @('SYSTEM', 'Administrators', 'TrustedInstaller')
icacls $secrets /inheritance:r | Out-Null
foreach ($ace in @((Get-Acl $secrets).Access)) {
    $day = $ace.IdentityReference.Value
    if ($chuThePhep -notcontains ($day -split '\\')[-1]) {
        icacls $secrets /remove:g "$day" | Out-Null
    }
}
icacls $secrets /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" | Out-Null
Get-ChildItem $secrets -File | ForEach-Object { icacls $_.FullName /reset | Out-Null }
$conThua = @((Get-Acl $secrets).Access |
    ForEach-Object { ($_.IdentityReference.Value -split '\\')[-1] } |
    Where-Object { $chuThePhep -notcontains $_ } | Select-Object -Unique)
if ($conThua.Count -gt 0) {
    throw "Khong siet duoc secrets\ - van con chu the: $($conThua -join ', ')"
}
Ok 'Chi SYSTEM va Administrators doc duoc secrets\ (da kiem lai)'

Head 'Sinh bi mat'
$envFile = Join-Path $secrets 'app.env'
$newPassword = $null
if (Test-Path $envFile) {
    Ok 'app.env da co - GIU NGUYEN'
    Note 'Neu mat mat khau admin: xoa dong LTT_ADMIN_PASSWORD_HASH roi chay lai script nay.'
} else {
    # Sinh ngau nhien bang thu vien mat ma cua Python, khong dung Get-Random.
    $sessionSecret = & $venvPy -c "import secrets;print(secrets.token_urlsafe(32))"
    $tokenKey      = & $venvPy -c "import secrets;print(secrets.token_urlsafe(32))"
    $newPassword   = & $venvPy -c "import secrets,string;a=string.ascii_letters+string.digits;print(''.join(secrets.choice(a) for _ in range(20)))"
    $hash = & $venvPy -c "import sys;sys.path.insert(0,r'$appDir');from server.auth.password_hashing import hash_password;print(hash_password(sys.argv[1]))" $newPassword
    if (-not $hash) { throw 'Khong tao duoc hash mat khau' }

    $lines = @(
        '# LTT AI Studio - bi mat production. KHONG BAO GIO commit file nay.',
        'LTT_ENV=production',
        "LTT_ADMIN_USERNAME=$AdminUser",
        "LTT_ADMIN_PASSWORD_HASH=$hash",
        "LTT_SESSION_SECRET=$sessionSecret",
        "LTT_TOKEN_ENCRYPTION_KEY=$tokenKey",
        "LTT_DATA_DIR=$dataDir",
        "LTT_SECRETS_DIR=$secrets",
        "LTT_LOGS_DIR=$logs"
    )
    Write-NoBom $envFile ($lines -join "`r`n")
    Ok 'Da sinh app.env voi bi mat ngau nhien'
}

# Khoi sinh LTT_CODEX_SIDECAR_TOKEN da GO 09/09/2026 (pha 07): khong con dich vu
# nao doc no.
#
# CANH BAO: Go khoi SINH khong xoa token DA CO trong `app.env` cua may chu. Do la mot bi
#    mat cua mot dich vu da chet, va viec don no thuoc pha 09 (provider config /
#    secret clean) - ghi ra day de no khong bien mat khoi tam mat.

$envTxt = Get-Content $envFile -Raw
if ($envTxt -notmatch '(?m)^LTT_WHISPERX_PYTHON=') {
    [IO.File]::AppendAllText($envFile, "`r`nLTT_WHISPERX_PYTHON=$whisperPy`r`n", (New-Object Text.UTF8Encoding($false)))
    Ok 'Da them LTT_WHISPERX_PYTHON vao app.env'
} else {
    Ok 'LTT_WHISPERX_PYTHON da co - GIU NGUYEN'
}
$envTxt = [IO.File]::ReadAllText($envFile)
if ($envTxt -notmatch '(?m)^LTT_HF_TOKEN=') {
    [IO.File]::AppendAllText($envFile, "`r`nLTT_HF_TOKEN=`r`n", (New-Object Text.UTF8Encoding($false)))
    Ok 'Da them placeholder LTT_HF_TOKEN (Pyannote chi bat khi operator dien token)'
}

Head 'PostgreSQL'
# CSDL cua nen tang (quyet dinh Q2). Cai dat va tao database + role rieng.
# Chay lai duoc nhieu lan: da co thi dung lai, KHONG BAO GIO ghi de mat khau
# hay du lieu dang co.
$pgBin = $null
foreach ($v in @('18','17','16','15','14')) {
    $p = "C:\Program Files\PostgreSQL\$v\bin"
    if (Test-Path (Join-Path $p 'psql.exe')) { $pgBin = $p; break }
}
if (-not $pgBin) {
    $cmd = Get-Command psql.exe -ErrorAction SilentlyContinue
    if ($cmd) { $pgBin = Split-Path $cmd.Source }
}

if ($pgBin) {
    Ok "PostgreSQL da co: $pgBin"
} else {
    Note 'Chua co PostgreSQL - dang cai bang winget...'
    $wg = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wg) {
        throw 'Khong co winget va cung khong co PostgreSQL. Cai PostgreSQL thu cong roi chay lai script nay.'
    }
    # Mat khau superuser sinh ngau nhien va CHI dung luc cai. Ung dung khong
    # dung tai khoan nay - no chay bang role rieng tao o duoi.
    $pgSuper = & $venvPy -c "import secrets,string;a=string.ascii_letters+string.digits;print(''.join(secrets.choice(a) for _ in range(24)))"
    winget install --id PostgreSQL.PostgreSQL.17 --silent --accept-package-agreements --accept-source-agreements --override "--mode unattended --unattendedmodeui none --superpassword $pgSuper --serverport 5432" 2>&1 | Out-Null
    foreach ($v in @('18','17','16','15','14')) {
        $p = "C:\Program Files\PostgreSQL\$v\bin"
        if (Test-Path (Join-Path $p 'psql.exe')) { $pgBin = $p; break }
    }
    if (-not $pgBin) { throw 'Cai PostgreSQL that bai - khong tim thay psql.exe' }
    # Ghi lai mat khau superuser vao secrets\ de con vao bao tri CSDL sau nay.
    Write-NoBom (Join-Path $secrets 'postgres-superuser.txt') $pgSuper
    Ok 'Da cai PostgreSQL. Mat khau superuser luu o secrets\postgres-superuser.txt'
}

Head 'CSDL cua ung dung'
# Tao database + role RIENG cho ung dung. Ung dung khong bao gio chay bang
# tai khoan superuser: mot lo hong SQL injection voi quyen superuser doc duoc
# moi database tren may, con voi role rieng thi chi trong pham vi cua no.
$envText = if (Test-Path $envFile) { Get-Content $envFile -Raw } else { '' }
if ($envText -match '(?m)^LTT_DATABASE_URL=') {
    Ok 'LTT_DATABASE_URL da co trong app.env - GIU NGUYEN'
} else {
    $superFile = Join-Path $secrets 'postgres-superuser.txt'
    if (-not (Test-Path $superFile)) {
        Note 'Khong co mat khau superuser PostgreSQL (CSDL nay da co truoc khi cai).'
        Note 'CAN LAM THU CONG - chay 2 lenh sau bang tai khoan postgres:'
        Note '  CREATE ROLE ltt_app LOGIN PASSWORD ''<dat-mat-khau>'';'
        Note '  CREATE DATABASE lttplatform OWNER ltt_app;'
        Note 'Roi them dong nay vao secrets\app.env:'
        Note '  LTT_DATABASE_URL=postgresql+psycopg://ltt_app:<mat-khau>@127.0.0.1:5432/lttplatform'
    } else {
        $superPw = (Get-Content $superFile -Raw).Trim()
        $appPw   = & $venvPy -c "import secrets,string;a=string.ascii_letters+string.digits;print(''.join(secrets.choice(a) for _ in range(24)))"
        $psql    = Join-Path $pgBin 'psql.exe'
        $env:PGPASSWORD = $superPw

        # Tao role neu chua co. DO_ block de chay lai duoc nhieu lan.
        $sqlRole = "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='ltt_app') THEN CREATE ROLE ltt_app LOGIN PASSWORD '$appPw'; END IF; END `$`$;"
        & $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -v ON_ERROR_STOP=1 -c $sqlRole | Out-Null
        if ($LASTEXITCODE -ne 0) { $env:PGPASSWORD=$null; throw 'Tao role ltt_app that bai' }

        # CREATE DATABASE khong chay duoc trong DO block -> kiem tra roi tao.
        $coDb = & $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='lttplatform'"
        if ($coDb -ne '1') {
            & $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -v ON_ERROR_STOP=1 -c 'CREATE DATABASE lttplatform OWNER ltt_app;' | Out-Null
            if ($LASTEXITCODE -ne 0) { $env:PGPASSWORD=$null; throw 'Tao database lttplatform that bai' }
            Ok 'Da tao database lttplatform'
        } else {
            Ok 'Database lttplatform da co'
            # Da co database nhung chua co dong trong app.env -> mat khau cu
            # khong con biet. Dat lai de hai ben khop nhau.
            & $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -v ON_ERROR_STOP=1 -c "ALTER ROLE ltt_app PASSWORD '$appPw';" | Out-Null
        }
        $env:PGPASSWORD = $null

        $url = "postgresql+psycopg://ltt_app:$appPw@127.0.0.1:5432/lttplatform"
        Write-NoBom $envFile ($envText.TrimEnd() + "`r`n" + "LTT_DATABASE_URL=$url" + "`r`n")
        Ok 'Da tao role + database va ghi LTT_DATABASE_URL vao app.env'
    }
}

Head 'Di tru luoc do CSDL'
# Chay migration TRUOC khi khoi dong dich vu: dich vu khoi dong voi luoc do cu
# se loi o request dau tien chu khong loi luc khoi dong - kho truy hon nhieu.
$envText = if (Test-Path $envFile) { Get-Content $envFile -Raw } else { '' }
if ($envText -match '(?m)^LTT_DATABASE_URL=(.+)$') {
    $env:LTT_DATABASE_URL = $Matches[1].Trim()
    Push-Location $appDir
    Invoke-Ngoai { & $venvPy -m alembic upgrade head }
    $rc = $LASTEXITCODE
    Pop-Location
    $env:LTT_DATABASE_URL = $null
    if ($rc -ne 0) { throw 'alembic upgrade head that bai - xem thong bao o tren' }
    Ok 'Luoc do CSDL da o ban moi nhat'
} else {
    Note 'Bo qua migration - chua co LTT_DATABASE_URL'
}

Head 'NSSM (trinh quan ly dich vu)'
$nssmExe = Join-Path $tools 'nssm.exe'
if (-not (Test-Path $nssmExe)) {
    $cmd = Get-Command nssm.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        Copy-Item $cmd.Source $nssmExe -Force
        Ok 'Lay nssm.exe tu PATH'
    } else {
        Note 'Dang tai NSSM...'
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $zip = Join-Path $env:TEMP 'nssm.zip'
        $ex  = Join-Path $env:TEMP 'nssm-extract'
        Invoke-WebRequest 'https://nssm.cc/release/nssm-2.24.zip' -OutFile $zip -UseBasicParsing
        if (Test-Path $ex) { Remove-Item $ex -Recurse -Force }
        Expand-Archive $zip $ex -Force
        $found = Get-ChildItem $ex -Recurse -Filter nssm.exe |
                 Where-Object { $_.FullName -match 'win64' } | Select-Object -First 1
        if (-not $found) { throw 'Khong tim thay nssm.exe trong file tai ve' }
        Copy-Item $found.FullName $nssmExe -Force
        Remove-Item $zip, $ex -Recurse -Force -ErrorAction SilentlyContinue
        Ok 'Da tai va cai NSSM'
    }
} else { Ok 'nssm.exe da co' }

Head 'Dang ky dich vu Windows'
$existing = Get-Service $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.Status -eq 'Running') { Stop-Service $ServiceName -Force; Start-Sleep -Seconds 2 }
    Ok "Dich vu $ServiceName da co - cap nhat cau hinh"
} else {
    & $nssmExe install $ServiceName $venvPy "-m uvicorn server.run:app --host 127.0.0.1 --port $Port" | Out-Null
    Ok "Da tao dich vu $ServiceName"
}
# AppDirectory PHAI la app\ - mot so duong dan trong code tinh theo thu muc
# lam viec. Sai cho nay thi dich vu chay nhung moi trang tra 500.
& $nssmExe set $ServiceName AppDirectory   $appDir | Out-Null
& $nssmExe set $ServiceName AppStdout      (Join-Path $logs 'service-out.log') | Out-Null
& $nssmExe set $ServiceName AppStderr      (Join-Path $logs 'service-err.log') | Out-Null
& $nssmExe set $ServiceName AppRotateFiles 1 | Out-Null
# Xoay log theo KICH THUOC, khong chi khi restart (AppRotateFiles mot minh de log
# phong to vo han giua hai lan restart). AppRotateOnline 1 = xoay khi dang chay;
# AppRotateBytes 10MB = moi file toi 10MB roi xoay.
& $nssmExe set $ServiceName AppRotateOnline 1 | Out-Null
& $nssmExe set $ServiceName AppRotateBytes 10485760 | Out-Null
& $nssmExe set $ServiceName Start          SERVICE_AUTO_START | Out-Null
& $nssmExe set $ServiceName AppExit Default Restart | Out-Null
& $nssmExe set $ServiceName AppRestartDelay 10000 | Out-Null

# Nap bi mat vao moi truong cua dich vu. Doc lai tu app.env moi lan chay de
# lan chay lai cung cap nhat duoc thay doi.
$envPairs = @()
foreach ($line in (Get-Content $envFile)) {
    $t = $line.Trim()
    if ($t -and -not $t.StartsWith('#') -and $t.Contains('=')) { $envPairs += $t }
}
& $nssmExe set $ServiceName AppEnvironmentExtra ($envPairs -join "`r`n") | Out-Null
Ok 'Da nap bi mat vao moi truong dich vu'

Head 'Dich vu Worker (hang doi job)'
# Worker chay TIEN TRINH RIENG voi web (Q6): job nang khong lam cham web, va
# cap nhat web khong giet job dang chay. Cung AppDirectory, cung bi mat.
$existingW = Get-Service $WorkerServiceName -ErrorAction SilentlyContinue
if ($existingW) {
    if ($existingW.Status -eq 'Running') { Stop-Service $WorkerServiceName -Force; Start-Sleep -Seconds 2 }
    Ok "Dich vu $WorkerServiceName da co - cap nhat cau hinh"
} else {
    & $nssmExe install $WorkerServiceName $venvPy 'job_worker.py' | Out-Null
    Ok "Da tao dich vu $WorkerServiceName"
}
& $nssmExe set $WorkerServiceName AppDirectory   $appDir | Out-Null
& $nssmExe set $WorkerServiceName AppStdout      (Join-Path $logs 'worker-out.log') | Out-Null
& $nssmExe set $WorkerServiceName AppStderr      (Join-Path $logs 'worker-err.log') | Out-Null
& $nssmExe set $WorkerServiceName AppRotateFiles 1 | Out-Null
& $nssmExe set $WorkerServiceName AppRotateOnline 1 | Out-Null
& $nssmExe set $WorkerServiceName AppRotateBytes 10485760 | Out-Null
& $nssmExe set $WorkerServiceName Start          SERVICE_AUTO_START | Out-Null
& $nssmExe set $WorkerServiceName AppExit Default Restart | Out-Null
& $nssmExe set $WorkerServiceName AppRestartDelay 10000 | Out-Null
& $nssmExe set $WorkerServiceName AppEnvironmentExtra ($envPairs -join "`r`n") | Out-Null
Ok 'Da nap bi mat vao moi truong worker'

Head 'Go dich vu Sidecar Codex (da ngung 09/09/2026)'
# AI CLEAN REBUILD V2 pha 07: app CHAT AI STUDIO va toan bo `codex_sidecar/` da
# bi xoa khoi ma nguon. Nhung XOA MA KHONG GO MOT DICH VU WINDOWS: dich vu
# LTTStudioCodex van dang chay tren may chu, van tro vao `app\` (nen no giu thu
# muc ay khi cap nhat), va van tu khoi dong lai sau moi lan reboot.
#
# CAM: Khoi nay phai la GO, khong phai "khong lam gi". Bo khoi cai di ma khong go
#    thi lan cap nhat sau se co mot dich vu tro toi mot tep khong con ton tai:
#    no fail lien tuc, ghi day log, va khong ai biet vi sao.
$CodexServiceName = 'LTTStudioCodex'
$existingC = Get-Service $CodexServiceName -ErrorAction SilentlyContinue
if ($existingC) {
    if ($existingC.Status -eq 'Running') { Stop-Service $CodexServiceName -Force; Start-Sleep -Seconds 2 }
    & $nssmExe remove $CodexServiceName confirm | Out-Null
    Ok "Da go dich vu $CodexServiceName (ma nguon da xoa o pha 07)"
} else {
    Ok "Dich vu $CodexServiceName khong con - khong phai lam gi"
}

Head 'Dich vu Giong noi (LTT VOICE)'
# Phan CAI DAT da chay o tren, TRUOC khi dung dich vu nao. Khoi nay chi con viec
# dang ky dich vu -- vai giay.
if ($voicePy -and (Test-Path $voicePy)) {
    $hfCache = Join-Path $voiceVenvRoot 'hf-cache'
    $envTxt2 = Get-Content $envFile -Raw -ErrorAction SilentlyContinue
    if ($envTxt2 -notmatch 'LTT_VOICE_SIDECAR_TOKEN=') {
        $voiceTok = & $venvPy -c "import secrets;print(secrets.token_urlsafe(32))"
        $add2 = "LTT_VOICE_SIDECAR_TOKEN=$voiceTok`r`nLTT_VOICE_SIDECAR_PORT=8120`r`nLTT_VIENEU_PYTHON=$voicePy`r`nHF_HOME=$hfCache"
        [IO.File]::AppendAllText($envFile, "`r`n$add2`r`n", (New-Object Text.UTF8Encoding($false)))
        Ok 'Da them LTT_VOICE_SIDECAR_TOKEN + port + HF_HOME vao app.env'
    } else {
        Ok 'LTT_VOICE_SIDECAR_TOKEN da co - GIU NGUYEN'
    }
    # Doc lai app.env de dich vu giong nhan duoc cac bien vua them.
    $envPairs2 = @()
    foreach ($line in (Get-Content $envFile -ErrorAction SilentlyContinue)) {
        $l = $line.Trim()
        if ($l -and -not $l.StartsWith('#') -and $l.Contains('=')) { $envPairs2 += $l }
    }

    $existingV = Get-Service $VoiceServiceName -ErrorAction SilentlyContinue
    if ($existingV) {
        if ($existingV.Status -eq 'Running') { Stop-Service $VoiceServiceName -Force; Start-Sleep -Seconds 2 }
        Ok "Dich vu $VoiceServiceName da co - cap nhat cau hinh"
    } else {
        & $nssmExe install $VoiceServiceName $voicePy 'voice_sidecar_main.py' | Out-Null
        Ok "Da tao dich vu $VoiceServiceName"
    }
    & $nssmExe set $VoiceServiceName Application    $voicePy | Out-Null
    & $nssmExe set $VoiceServiceName AppDirectory   $appDir | Out-Null
    & $nssmExe set $VoiceServiceName AppStdout      (Join-Path $logs 'voice-out.log') | Out-Null
    & $nssmExe set $VoiceServiceName AppStderr      (Join-Path $logs 'voice-err.log') | Out-Null
    & $nssmExe set $VoiceServiceName AppRotateFiles 1 | Out-Null
    & $nssmExe set $VoiceServiceName AppRotateOnline 1 | Out-Null
    & $nssmExe set $VoiceServiceName AppRotateBytes 10485760 | Out-Null
    & $nssmExe set $VoiceServiceName Start          SERVICE_AUTO_START | Out-Null
    & $nssmExe set $VoiceServiceName AppExit Default Restart | Out-Null
    & $nssmExe set $VoiceServiceName AppRestartDelay 10000 | Out-Null
    & $nssmExe set $VoiceServiceName AppEnvironmentExtra ($envPairs2 -join "`r`n") | Out-Null
    Ok 'Da nap bi mat vao moi truong dich vu giong noi'
} else {
    Write-Host '  [BO QUA] Chua cai duoc dich vu giong noi - app LTT VOICE se hien "can thiet lap".' -ForegroundColor Yellow
}

Head 'Khoi dong'
Start-Service $ServiceName
Start-Service $CodexServiceName -ErrorAction SilentlyContinue

# Sau cung: nap ~320 MB trong so len GPU, mat khoang 20 giay moi san sang.

Start-Service $VoiceServiceName -ErrorAction SilentlyContinue

Start-Sleep -Seconds 6
$svc = Get-Service $ServiceName
if ($svc.Status -ne 'Running') {
    Write-Host "  [LOI] Dich vu web khong chay. Xem log:" -ForegroundColor Red
    Get-Content (Join-Path $logs 'service-err.log') -Tail 25 -ErrorAction SilentlyContinue
    throw 'Dich vu web khoi dong that bai'
}
Ok "Dich vu $ServiceName dang chay"

Start-Service $WorkerServiceName
Start-Sleep -Seconds 3
$svcW = Get-Service $WorkerServiceName
if ($svcW.Status -ne 'Running') {
    Write-Host "  [LOI] Dich vu worker khong chay. Xem log:" -ForegroundColor Red
    Get-Content (Join-Path $logs 'worker-err.log') -Tail 25 -ErrorAction SilentlyContinue
    throw 'Dich vu worker khoi dong that bai'
}
Ok "Dich vu $WorkerServiceName dang chay"

Head 'Kiem tra suc khoe'
$okHealth = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $r = Invoke-RestMethod "http://127.0.0.1:$Port/health/ready" -TimeoutSec 5
        Write-Host "  status=$($r.status) environment=$($r.environment)"
        $okHealth = ($r.status -eq 'ready'); break
    } catch { Start-Sleep -Seconds 2 }
}
if ($okHealth) { Ok 'Ung dung san sang' }
else { Note 'Chua ready - thuong do CSDL chua noi duoc. Xem logs\service-err.log' }

Write-Host ""
Write-Host ("-" * 62)
if ($newPassword) {
    Write-Host "MAT KHAU ADMIN (chi hien MOT LAN, luu lai ngay):" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    Tai khoan : $AdminUser"
    Write-Host "    Mat khau  : $newPassword"
    Write-Host ""
    Write-Host "Mat khau khong luu o dau ca - chi luu dang hash." -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "Buoc tiep theo:" -ForegroundColor Cyan
Write-Host "  2. Chay: .\setup\3-cloudflare.ps1   (can ban dang nhap Cloudflare)"
Write-Host "  3. Chay: .\setup\4-nghiem-thu.ps1"
Write-Host ""
Write-Host "QUAN TRONG: sao luu $secrets\app.env ra cho an toan." -ForegroundColor Yellow
Write-Host "Mat LTT_TOKEN_ENCRYPTION_KEY la mat toan bo token Facebook/TikTok da luu." -ForegroundColor Yellow

# Nha khoa deploy. Loi o day chi canh bao: mot khoa sot lai se duoc luot
# sau nhan ra la CU (pid khong con song) va lay lai.
if ($daGiuKhoa) {
    try { Remove-Item $khoaTep -Force -ErrorAction Stop }
    catch { Write-Host "  [!] Khong xoa duoc $khoaTep - luot sau se tu lay lai." -ForegroundColor Yellow }
}
