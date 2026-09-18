# deploy.ps1 - chep cong VLM tu MAY A sang MAY B. CHAY TREN MAY A.
#
#     powershell -ExecutionPolicy Bypass -File llm_gateway\deploy\deploy.ps1
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md). Da dinh mot lan trong phien nay:
# mot dau gach dai trong mot .ps1 lam vo ca script va bao loi o dong khac.
#
# BA DIEU KHONG BAO GIO DUOC DOI:
#   1. Ma nguon viet o MAY A, trong repo. Deploy bang script. KHONG BAO GIO sua tay
#      tren may B - lan deploy sau la mat trang, mat am tham (Q102).
#   2. May B KHONG giu bi mat nao cua nen tang: khong mat khau CSDL, khong khoa R2,
#      khong LTT_TOKEN_ENCRYPTION_KEY. No chi biet mot bearer token cua chinh no.
#   3. llama-server va llama-swap CHI nghe 127.0.0.1. Chi cong VLM nghe LAN.

[CmdletBinding()]
param(
    [string]$MayB    = "192.168.2.66",
    [string]$User    = "lengo",
    [string]$Khoa    = "$env:USERPROFILE\.ssh\nexus_b",
    [string]$Goc     = "H:/LTT_LLM",
    [switch]$BoQuaVenv,                     # chi chep ma, khong dung venv lai
    # Cho phep ghi de llama-swap.yaml tren may B khi no LECH ban trong kho
    # (vd co sua tay chua dua vao kho). Mac dinh: DUNG LAI va noi ro.
    [switch]$GhiDeYamlLech,
    # Chi deploy MA cong, KHONG cham llama-swap.yaml tren may B (phuong an C buoc 3:
    # yaml khong doi so; cong doc tep DANG co tren B). Bo qua ca buoc 1c.
    [switch]$BoQuaYaml
)

$ErrorActionPreference = "Stop"
$RepoGoc = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Buoc($s) { Write-Host ""; Write-Host "== $s" -ForegroundColor Cyan }
function Dat($s)  { Write-Host "  [OK]  $s" -ForegroundColor Green }
function Loi($s)  { Write-Host "  [LOI] $s" -ForegroundColor Red }
# !! `Canh` KHAC `Loi`: canh bao la "deploy xong nhung co dieu ban can biet",
#    con `Loi` la "deploy that bai". Gop hai cai lam mot thi hoac ta bao dong
#    gia, hoac ta nuot mat mot dieu can noi.
#
# !! Hai ham nay TUNG THIEU, va khoi canh bao cau hinh o buoc 3 goi chung nen
#    deploy CHET NGAY O DO - moi lan, khong tru lan nao. No qua duoc vong kiem
#    truoc day vi kiem do chi chay `[Parser]::ParseFile`, ma cu phap KHONG bat
#    duoc mot lenh khong ton tai. Bai hoc: mot script deploy chi duoc coi la da
#    kiem khi no CHAY HET, khong phai khi no PHAN TICH DUOC.
function Canh($s) { Write-Host "  [!]   $s" -ForegroundColor Yellow }
function Note($s) { Write-Host "$s" -ForegroundColor DarkGray }

# !! KHONG dat ten ham la `SSH`: PowerShell KHONG phan biet hoa thuong, nen ben
#    trong ham `& ssh` se phan giai ve CHINH HAM DO -> de quy vo han -> "call depth
#    overflow". Da dinh mot lan. Ten khac + goi `ssh.exe` tuong minh.
function ChayTrenB($lenh) {
    # !! `$ErrorActionPreference = "Stop"` bien MOI dong stderr cua mot .exe
    #    thanh NativeCommandError va lam ca script chet. OpenSSH nay in mot
    #    CANH BAO VO HAI ra stderr moi lan ket noi:
    #
    #      ** WARNING: connection is not using a post-quantum key exchange...
    #
    #    Ket qua: script CHET NGAY O BUOC 0, du ssh chay binh thuong. Da dinh
    #    24/08, va no chi cach nhau mot ban cap nhat OpenSSH.
    #
    #    Nen ha `ErrorActionPreference` quanh dung loi goi, va van chot bang
    #    `$LASTEXITCODE` - do moi la thu noi ssh thanh cong hay khong.
    $cu = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $r = & ssh.exe -i $Khoa -o BatchMode=yes "$User@$MayB" $lenh 2>&1
    } finally {
        $ErrorActionPreference = $cu
    }
    if ($LASTEXITCODE -ne 0) { Loi "ssh that bai: $lenh"; $r | Write-Host; exit 1 }
    # Bo dong canh bao cua ssh khoi ket qua tra ve, neu khong ben goi se coi
    # no la mot phan cua output tu may B.
    return ($r | Where-Object { $_ -notmatch 'post-quantum|store now|openssh' })
}

# --- 0. Kiem lien lac ----------------------------------------------------------
Buoc "0. Lien lac voi may B"
if (-not (Test-Path $Khoa)) { Loi "khong thay khoa SSH $Khoa"; exit 1 }
ChayTrenB "echo ok" | Out-Null
Dat "ssh $User@$MayB chay duoc"

# --- 1. Thu muc ----------------------------------------------------------------
Buoc "1. Thu muc tren may B"
$g = $Goc -replace "/", "\"
ChayTrenB "if not exist $g\gateway mkdir $g\gateway" | Out-Null
ChayTrenB "if not exist $g\logs mkdir $g\logs"       | Out-Null
ChayTrenB "if not exist $g\work mkdir $g\work"       | Out-Null
Dat "$Goc/gateway, /logs, /work"

# --- 1b. Chup ban dang chay TRUOC khi de len ----------------------------------
#
# ! Ra soat F22-F27 ngay 01/09: `H:\LTT_LLM\releases` chi co HAI ban, ca hai tu
#    27/08. Bon lan deploy trong ngay 31/08-01/09 khong chup ban nao. Tuc duong
#    rollback ton tai TREN GIAY nhung khong duoc nuoi: neu mot lan deploy lam
#    hong thi khong co "ban truoc" de quay ve, va cach duy nhat con lai la
#    `git revert` + deploy lai -- doi may A song VA sshd bat duoc.
#
#    May A da co `app.previous/` cho dung viec nay. May B thi khong. Hai may le
#    ra phai cung mot chuan.
#
# ! Chup bang `xcopy` TREN MAY B chu khong keo ve may A: nhanh hon nhieu lan, va
#    quan trong hon la no khong phu thuoc duong mang -- mot ban chup that bai
#    giua chung con te hon khong chup, vi no trong nhu mot ban chup.
$dauThoiGian = (Get-Date).ToString("yyyyMMdd-HHmmss")
$banChup = "$Goc/releases/auto-$dauThoiGian"
Buoc "1b. Chup ban dang chay -> releases/auto-$dauThoiGian"
$gW = $Goc.Replace("/", "\")
$bcW = $banChup.Replace("/", "\")
$coBan = ChayTrenB "if exist $gW\gateway\llm_gateway (echo CO) else (echo KHONG)"
if (($coBan -join "") -match "CO") {
    ChayTrenB "mkdir $bcW 2>nul & xcopy /E /I /Q /Y $gW\gateway $bcW\gateway" | Out-Null
    $kiem = ChayTrenB "if exist $bcW\gateway\llm_gateway\main.py (echo CO) else (echo KHONG)"
    if (($kiem -join "") -match "CO") {
        Dat "da chup ban dang chay (rollback: xcopy nguoc lai roi Restart-Service)"
    } else {
        # Khong `exit 1`: deploy van nen di tiep. Nhung PHAI noi to, vi tu day
        # tro di ta dang deploy MA KHONG CO duong lui.
        Canh "CHUP THAT BAI - deploy tiep nhung KHONG CO ban de rollback."
    }
} else {
    Dat "chua co ban nao tren may B - khong can chup"
}

# --- 1c. llama-swap.yaml tren may B co LECH kho khong (TRUOC khi chep gi) -----
#
# !! YAML TREN MAY B LECH KHO = DUNG LAI (phuong an C, R-8 / O-19).
#
#    17/09: `/running` may B co `--no-cache-idle-slots` ma yaml trong kho KHONG co.
#    Chep de len la XOA co do tren dia AM THAM - co hieu luc o lan restart
#    LTTLlamaSwap ke tiep, khong ai noi voi lan deploy nay. Va tu buoc 3 cong LLM
#    DOC tep nay luc khoi dong (`llm_gateway/vat_ly.py`), nen tep tren dia la ca
#    rao vat ly cua cong. Lech thi phai co nguoi quyet: dua thay doi vao kho
#    (buoc 4) hoac chay lai voi -GhiDeYamlLech.
#
# ! Dat TRUOC buoc 2 co chu y: dung lai o day thi chua tep nao tren B bi doi.
$yamlKho = Join-Path $PSScriptRoot "llama-swap.yaml"
$hashYamlKho = (Get-FileHash -Algorithm SHA256 -LiteralPath $yamlKho).Hash.ToLower()
$yamlB = "$gW\gateway\llama-swap.yaml"
if ($BoQuaYaml) {
    Buoc "1c. llama-swap.yaml - BO QUA (-BoQuaYaml): khong doi chieu, khong chep"
    $coYamlB = @("BO_QUA")
} else {
    Buoc "1c. Doi chieu llama-swap.yaml tren may B voi kho"
    $coYamlB = ChayTrenB "if exist $yamlB (echo CO) else (echo KHONG)"
}
if ($BoQuaYaml) {
    $kiemYamlB = ChayTrenB "if exist $yamlB (echo CO) else (echo KHONG)"
    if (-not (($kiemYamlB -join "") -match "CO")) {
        # Cong doc tep nay luc khoi dong; khong co thi cong TU CHOI KHOI DONG.
        Loi "-BoQuaYaml nhung may B KHONG co $yamlB - cong se khong khoi dong duoc"; exit 1
    }
    Dat "may B co $yamlB - cong se doc tep nay"
} elseif (($coYamlB -join "") -match "CO") {
    $raHash = ChayTrenB "certutil -hashfile $yamlB SHA256"
    $hashYamlB = ""
    foreach ($d in $raHash) {
        $s = ($d -replace '\s', '').ToLower()
        if ($s -match '^[0-9a-f]{64}$') { $hashYamlB = $s }
    }
    if (-not $hashYamlB) {
        Loi "khong doc duoc hash llama-swap.yaml tren may B"; exit 1
    }
    if ($hashYamlB -ne $hashYamlKho) {
        if ($GhiDeYamlLech) {
            Canh "llama-swap.yaml tren may B LECH kho - GHI DE theo -GhiDeYamlLech (ban cu nam trong ban chup 1b)."
        } else {
            Loi "llama-swap.yaml tren may B LECH kho (B $hashYamlB, kho $hashYamlKho)."
            Note "    Co the co sua tay tren may B chua dua vao kho (vd --no-cache-idle-slots, O-19)."
            Note "    So: ssh ... type $yamlB  voi  llm_gateway\deploy\llama-swap.yaml"
            Note "    Dua thay doi vao kho, hoac chay lai voi -GhiDeYamlLech neu chu y ghi de."
            exit 1
        }
    } else {
        Dat "llama-swap.yaml tren may B khop kho"
    }
} else {
    Dat "chua co llama-swap.yaml tren may B"
}

# --- 2. Chep ma nguon ----------------------------------------------------------
# `llm_gateway` can `render_gateway.busy` (D-013/D-022 - khong chep lai 275 dong do).
# Hai goi nay deploy CUNG NHAU, do la giao uoc.
Buoc "2. Chep ma nguon"
foreach ($goi in @("llm_gateway", "render_gateway")) {
    $nguon = Join-Path $RepoGoc $goi
    if (-not (Test-Path $nguon)) { Loi "khong thay $nguon"; exit 1 }
    # Xoa __pycache__ o dich de khong con .pyc cu cua ban truoc.
    ChayTrenB "if exist $g\gateway\$goi\__pycache__ rd /s /q $g\gateway\$goi\__pycache__" | Out-Null
    & scp.exe -i $Khoa -o BatchMode=yes -q -r $nguon "${User}@${MayB}:$Goc/gateway/"
    if ($LASTEXITCODE -ne 0) { Loi "scp $goi that bai"; exit 1 }
    Dat "$goi"
}

# --- 2b. So hash hai ben -------------------------------------------------------
#
# Muc dich KHONG phai bat loi duong truyen. La bat viec SUA TAY TREN MAY B -- loi
# kinh dien cua du an nay va la thu quy tac 1 o dau tep nay cam: sua o may chay,
# quen sua o repo, lan deploy sau mat trang va mat AM THAM.
#
# ! Ra soat chuoi cung ung 01/09: `render_gateway/deploy/deploy.ps1` co 15 dong
#    doi chieu hash; tep NAY co 0. Hai cong tren CUNG MOT MAY, hai script deploy,
#    mot cai kiem va mot cai khong. Buoc 6 ("import OK") chi chung minh module
#    NAP DUOC, khong chung minh moi tep chep dung -- mot tep .py cu con sot lai
#    van cho `import` thanh cong.
Buoc "2b. So hash hai ben"
$mongDoi = @{}
foreach ($goi in @("llm_gateway", "render_gateway")) {
    foreach ($t in (Get-ChildItem (Join-Path $RepoGoc $goi) -Recurse -File -Filter *.py |
                    Where-Object { $_.FullName -notmatch '__pycache__' })) {
        $tuong = $t.FullName.Substring($RepoGoc.Length).TrimStart('\').Replace('\', '/')
        $mongDoi[$tuong] = (Get-FileHash -Algorithm SHA256 -LiteralPath $t.FullName).Hash.ToLower()
    }
}
$noiDungHash = ($mongDoi.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n"
$tamHash = Join-Path $env:TEMP "ltt_llm_hash.txt"
[IO.File]::WriteAllText($tamHash, $noiDungHash, (New-Object Text.UTF8Encoding($false)))
& scp.exe -i $Khoa -o BatchMode=yes -q $tamHash "${User}@${MayB}:$Goc/work/hash_mong_doi.txt"
if ($LASTEXITCODE -ne 0) { Loi "scp bang hash that bai"; exit 1 }
Remove-Item $tamHash -Force

# !! PHAI dung `-EncodedCommand`. Mot khoi PowerShell NHIEU DONG khong song sot
#    qua duong `ssh -> cmd.exe tren may B`: ssh truyen ca khoi nhu MOT doi so,
#    cmd.exe thay xuong dong va cat no thanh nhieu lenh roi. Da dinh 01/09, va
#    trieu chung la mot dong "[LOI] ssh that bai" kem ca doan script in ra man
#    hinh -- trong nhu loi cu phap, thuc ra la loi VAN CHUYEN.
#
#    Base64 khong co ky tu nao ma cmd.exe hay PowerShell muon dien giai, nen no
#    qua duoc ca hai tang khong suy suyen. Cung ly do voi `bput` dung base64.
$gW2 = $Goc.Replace("/", "\")
$maKiem = @"
`$goc = '$gW2\gateway'
`$lech = @()
foreach (`$dong in [IO.File]::ReadAllLines('$gW2\work\hash_mong_doi.txt')) {
    if (-not `$dong) { continue }
    `$p = `$dong.Split('=', 2)
    `$tep = Join-Path `$goc (`$p[0] -replace '/', '\')
    if (-not (Test-Path -LiteralPath `$tep)) { `$lech += ('THIEU  ' + `$p[0]); continue }
    `$h = (Get-FileHash -Algorithm SHA256 -LiteralPath `$tep).Hash.ToLower()
    if (`$h -ne `$p[1]) { `$lech += ('KHAC   ' + `$p[0]) }
}
if (`$lech.Count -gt 0) { `$lech | ForEach-Object { Write-Host `$_ }; 'CO_LECH' } else { 'KHOP' }
"@
$b64Kiem = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($maKiem))
$ktHash = ChayTrenB "powershell -NoProfile -EncodedCommand $b64Kiem"
if (($ktHash -join " ") -match "CO_LECH") {
    Loi "Tep tren may B LECH so voi repo. Nhieu kha nang co ai da sua tay tren B."
    $ktHash | Write-Host
    exit 1
}
Dat "hash khop $($mongDoi.Count) tep - khong co tep nao bi sua tay tren may B"

# --- 3. Cau hinh llama-swap ----------------------------------------------------
Buoc "3. Cau hinh llama-swap"
$tepTemplate = Join-Path $PSScriptRoot "chat_template_v22.5.jinja"
$hashTemplate = "e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2"
if (-not (Test-Path -LiteralPath $tepTemplate)) {
    Loi "thieu chat_template_v22.5.jinja trong goi deploy"
    exit 1
}
$hashTemplateThuc = (Get-FileHash -Algorithm SHA256 -LiteralPath $tepTemplate).Hash.ToLower()
if ($hashTemplateThuc -ne $hashTemplate) {
    Loi "chat_template_v22.5.jinja sai hash - khong deploy tep khong ro phien ban"
    exit 1
}
& scp.exe -i $Khoa -o BatchMode=yes -q $tepTemplate `
    "${User}@${MayB}:H:/LTT_LLM/models/chat_template_v22.5.jinja"
if ($LASTEXITCODE -ne 0) { Loi "scp chat template that bai"; exit 1 }
Dat "chat template v22.5 (hash da khoa)"

# Da doi chieu o buoc 1c: toi day tep tren B khop kho, chua co, hoac duoc phep ghi de.
if ($BoQuaYaml) {
    Note "    llama-swap.yaml KHONG chep (-BoQuaYaml)."
} else {
    & scp.exe -i $Khoa -o BatchMode=yes -q $yamlKho `
        "${User}@${MayB}:$Goc/gateway/llama-swap.yaml"
    if ($LASTEXITCODE -ne 0) { Loi "scp llama-swap.yaml that bai"; exit 1 }
    Dat "llama-swap.yaml"
}

# !! CHEP MOT TEP CAU HINH MA KHONG RESTART THI TEP AY KHONG PHAI CAU HINH.
#
#    `llama-swap` doc cau hinh MOT LAN luc khoi dong. Tep moi nam tren dia BAT
#    DONG cho toi khi co thu khac restart dich vu - co the vai ngay sau, va khi
#    do no co hieu luc AM THAM, khong ai cho doi.
#
#    Do 31/08: tep tren dia ghi luc 18:37 mo ta "input public 65K", tien trinh
#    llama-swap khoi dong luc 18:34, va `/running` van bao "90K". Ba con so, hai
#    su that khac nhau, khong mot dong canh bao nao.
#
# ! Script nay KHONG tu restart. `llama-swap` restart la unload model, va mot
#    lan unload giua gio phuc vu la mot quyet dinh van hanh chu khong phai mot
#    buoc phu cua deploy. Nhung IM LANG thi khong chap nhan duoc - nen no PHAT
#    HIEN va NOI.
# !! DONG NAY DA TUNG LAM VO CA SCRIPT. Ban dau no la mot chuoi NHAY KEP chua
#    `\"` va `^|`. PowerShell KHONG thoat bang backslash, nen `\"` ket thuc chuoi
#    SOM va phan con lai thanh lenh:
#
#      The term '\' is not recognized as the name of a cmdlet...
#
#    Va `$p` trong chuoi nhay kep bi may A khai trien thanh rong TRUOC khi gui.
#    Cung ho voi quy tac 3 cua CLAUDE.md ("PowerShell nuot dau ngoac kep").
#
# => NHAY DON o ngoai: may A khong khai trien gi, `"` ben trong la ky tu that,
#    `''` la mot dau nhay don. Va BO HAN dau ong - `@(...)[0]` thay cho
#    `| Select-Object -First 1`, nen khong con phai lo cmd.exe co an `|` khong
#    (do la ly do ban cu phai chap va `^|`).
$qSwap = 'powershell -NoProfile -Command "$p=@(Get-Process llama-swap -EA SilentlyContinue)[0]; if ($p) { $p.StartTime.ToString(''yyyy-MM-ddTHH:mm:ss'') } else { ''KHONG_CHAY'' }"'
$tuoiSwap = ChayTrenB $qSwap
$tuoiSwap = ($tuoiSwap -join "").Trim()
if ($tuoiSwap -and $tuoiSwap -ne "KHONG_CHAY") {
    try {
        $batDau = [datetime]::Parse($tuoiSwap)
        if ($batDau -lt (Get-Date).AddMinutes(-1)) {
            Canh "llama-swap dang chay tu $tuoiSwap - CAU HINH VUA CHEP CHUA CO HIEU LUC."
            Note "    Cau hinh dang chay van la ban CU. De ap ban moi:"
            Note "      Restart-Service LTTLlamaSwap    (tren may B - se UNLOAD model)"
            Note "    Neu chi doi ma cong (khong doi llama-swap.yaml) thi bo qua dong nay."
        }
    } catch { Canh "khong doc duoc thoi diem khoi dong cua llama-swap: $tuoiSwap" }
}

# --- 4. venv -------------------------------------------------------------------
if (-not $BoQuaVenv) {
    Buoc "4. venv + thu vien"
    $py = "C:\Users\$User\AppData\Local\Programs\Python\Python312\python.exe"
    ChayTrenB "if not exist $g\venv $py -m venv $g\venv" | Out-Null
    $pip = "$g\venv\Scripts\python.exe -m pip"
    ChayTrenB "$pip install --quiet --upgrade pip" | Out-Null
    ChayTrenB "$pip install --quiet fastapi uvicorn httpx psutil" | Out-Null
    Dat "fastapi uvicorn httpx psutil"
} else {
    Buoc "4. venv - BO QUA (-BoQuaVenv)"
}

# --- 5. Tep moi truong ---------------------------------------------------------
# !! GHI KHONG BOM (quy tac 1 cua CLAUDE.md). PowerShell 5.1 chen BOM voi
#    Out-File/Set-Content, va mot BOM o day lam dong dau tien doc sai.
Buoc "5. C:\ProgramData\LTTLlm\gateway.env"
$envDir = "C:\ProgramData\LTTLlm"
ChayTrenB "if not exist $envDir mkdir $envDir" | Out-Null

# !! HAI SO CHINH SACH DOC TU `apps/ltt_llm/ngan_sach.py`, KHONG GO TAY (phuong an C).
#
#    Tran vao cua cong = `-c(llama-swap.yaml) - max_out - DEM_UOC`, cung cong thuc
#    voi may A. `-c`/`-np` cong doc thang tu yaml; `max_out`/`DEM_UOC` la chinh
#    sach cua may A, nen script nay HOI ngan_sach qua `xuat_tham_so_a.py` (mot tep
#    .py - CLAUDE.md luat 6) thay vi go so. Ban truoc go tay tran vao cua 3.8 cho
#    CA HAI model (O-02, sai cho 3.5) va tran ra o ba cho.
$pyA = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $pyA) { Loi "khong thay python tren may A de doc ngan_sach"; exit 1 }
$cu = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $raA = & $pyA.Source (Join-Path $PSScriptRoot "xuat_tham_so_a.py") 2>&1
} finally {
    $ErrorActionPreference = $cu
}
if ($LASTEXITCODE -ne 0) { Loi "xuat_tham_so_a.py that bai"; $raA | Write-Host; exit 1 }
$thamSoA = @{}
foreach ($d in $raA) {
    if ("$d" -match '^(LTT_LLM_MAX_OUTPUT_TOKENS|LTT_LLM_DEM_UOC)=([0-9]+)$') {
        $thamSoA[$Matches[1]] = $Matches[2]
    }
}
if ($thamSoA.Count -ne 2) { Loi "xuat_tham_so_a.py khong in du hai tham so"; $raA | Write-Host; exit 1 }
Note ("    tu ngan_sach: " + (($thamSoA.GetEnumerator() | Sort-Object Key | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ", "))

# !! BIEN DA GO (phuong an C buoc 3): cong khong con doc. Xoa khoi gateway.env de
#    tep khong noi mot dieu ma ma khong lam. Khop TIEN TO de bat ca dang `__<model>`.
#    Lich su: MAX_DONG_THOI ghim bang 1 tung bop may B con mot phan ba nang luc sau
#    khi yaml len `-np 3` (Dual-model 4.2); nay so chuoi la `-np` doc tu yaml.
$tienToDaGo = '^(LTT_LLM_MAX_INPUT_TOKENS|LTT_LLM_MAX_DONG_THOI|LTT_LLM_TOKEN_POOL|LTT_LLM_RPM)'

# !! SAN RAM TRONG CUA TRONG TAI (L-25, 18/09): kho la nguon, deploy GHI DE moi lan.
#    No va `--cache-ram` cua `llama-swap.yaml` la MOT rang buoc ngan sach RAM may B
#    (2 x cache + san + bien <= RAM trong luc cache rong); `test_1293` doi chieu ba
#    cho: so nay, mac dinh `llm_gateway/config.py`, va yaml. Truoc L-25 so nay chi
#    duoc ghi khi TAO tep lan dau, nen doi no trong kho khong bao gio toi may B.
$thamSoA['LTT_LLM_RAM_TRONG_GB'] = '24'

$co = ChayTrenB "if exist $envDir\gateway.env (echo CO) else (echo KHONG)"
if (($co -join "") -match "CO") {
    # Cap van hanh khong phai bi mat: migrate tai cho, giu nguyen token/model.
    # Khong dung PowerShell remote inline; scp file tam de tranh loi quoting va
    # dam bao UTF-8 khong BOM tren Windows PowerShell 5.1.
    $tamEnv = Join-Path $env:TEMP "gateway.env.migrate"
    & scp.exe -i $Khoa -o BatchMode=yes -q "${User}@${MayB}:C:/ProgramData/LTTLlm/gateway.env" $tamEnv
    if ($LASTEXITCODE -ne 0) { Loi "scp gateway.env ve de migrate that bai"; exit 1 }
    $dong = [IO.File]::ReadAllLines($tamEnv)
    $daGhi = @{}
    $daGo = @()
    $dong = @($dong | ForEach-Object {
        if ($_ -match $tienToDaGo) {
            $daGo += ($_ -split '=', 2)[0]
        } elseif ($_ -match '^(LTT_LLM_MAX_OUTPUT_TOKENS|LTT_LLM_DEM_UOC|LTT_LLM_RAM_TRONG_GB)=') {
            $k = $Matches[1]
            $daGhi[$k] = $true
            "$k=$($thamSoA[$k])"
        } else { $_ }
    })
    foreach ($k in ($thamSoA.Keys | Sort-Object)) {
        if (-not $daGhi.ContainsKey($k)) { $dong += "$k=$($thamSoA[$k])" }
    }
    [IO.File]::WriteAllText($tamEnv, ($dong -join "`n") + "`n", (New-Object Text.UTF8Encoding($false)))
    & scp.exe -i $Khoa -o BatchMode=yes -q $tamEnv "${User}@${MayB}:C:/ProgramData/LTTLlm/gateway.env"
    $rc = $LASTEXITCODE
    Remove-Item $tamEnv -Force -ErrorAction SilentlyContinue
    if ($rc -ne 0) { Loi "scp gateway.env da migrate that bai"; exit 1 }
    Dat "gateway.env da migrate (giu token/model); tham so tu ngan_sach da ghi"
    if ($daGo.Count -gt 0) {
        Canh ("da GO bien khong con tac dung: " + ($daGo -join ", "))
        Note "    nssm NUONG env luc CAI: cac bien nay con trong moi truong dich vu (vo hai,"
        Note "    cong chi canh bao). Muon sach han: chay lai cai_dat_dich_vu.ps1 tren may B."
    }
} else {
    # Token sinh mot lan, ngau nhien. No KHONG phai bi mat cua nen tang - no chi
    # bao ve cong VLM tren LAN. Nhung van khong duoc in ra log.
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $token = [Convert]::ToBase64String($bytes) -replace "[+/=]", ""

    $noiDung = @(
        "# gateway.env - cong VLM may B. Sinh boi deploy.ps1, KHONG sua tay.",
        "LTT_LLM_HOST=127.0.0.1",
        "LTT_LLM_PORT=8299",
        "LTT_LLM_TOKEN=$token",
        "LTT_LLM_UPSTREAM_URL=http://127.0.0.1:8280",
        "# Fail-closed (Q92): rong = KHONG mo model nao. Mo bang cach liet ke ten.",
        "LTT_LLM_MODELS=",
        "# Hai so duoi day doc tu apps/ltt_llm/ngan_sach.py luc deploy - KHONG sua tay.",
        "LTT_LLM_MAX_OUTPUT_TOKENS=$($thamSoA['LTT_LLM_MAX_OUTPUT_TOKENS'])",
        "LTT_LLM_DEM_UOC=$($thamSoA['LTT_LLM_DEM_UOC'])",
        "# So chuoi (-np) va be KV (-c): KHONG khai o day. Cong doc thang tu",
        "# llama-swap.yaml canh goi llm_gateway (llm_gateway/vat_ly.py).",
        "LTT_LLM_MAX_IMAGES=4",
        "# Nen do duoc: desktop 1515-1612 MiB, ComfyUI thuong tru 6211-16620 MiB.",
        "LTT_LLM_VRAM_SACH_MB=2500",
        "LTT_LLM_RAM_TRONG_GB=$($thamSoA['LTT_LLM_RAM_TRONG_GB'])"
    ) -join "`n"

    $tam = Join-Path $env:TEMP "gateway.env"
    [IO.File]::WriteAllText($tam, $noiDung, (New-Object Text.UTF8Encoding($false)))
    & scp.exe -i $Khoa -o BatchMode=yes -q $tam "${User}@${MayB}:C:/ProgramData/LTTLlm/gateway.env"
    Remove-Item $tam -Force
    Dat "gateway.env da tao (token sinh ngau nhien, KHONG in ra day)"
    Write-Host "  Doc token khi can:" -ForegroundColor Yellow
    Write-Host "    ssh -i $Khoa $User@$MayB ""findstr LTT_LLM_TOKEN $envDir\gateway.env""" -ForegroundColor Yellow
}

# --- 5b. Siet ACL cua tep bi mat -----------------------------------------------
#
# ! Ra soat F21 ngay 01/09: `gateway.env` cho `BUILTIN\Users` quyen doc, tuc MOI
#    tai khoan cuc bo tren may B doc duoc bearer token cua cong. Va do khong phai
#    mot lo xa: may B co hai tai khoan sandbox Codex dang bat
#    (CodexSandboxOffline, CodexSandboxOnline) cong voi Guest -- dung loai tai
#    khoan sinh ra de chay ma khong tin cay.
#
#    So sanh: `app.env` tren may A chi SYSTEM + Administrators, va bao cao audit
#    da ghi ACL do "LA DUNG - dung noi long no". Hai may le ra phai cung chuan.
#
# ! Vi sao nam TRONG script chu khong sua tay tren may B: quy tac 1 o dau tep --
#    sua tay la mat trang o lan deploy sau, mat AM THAM. Mot bien phap bao mat
#    chi song neu no duoc dat lai moi lan deploy.
#
#    Dich vu chay bang LocalSystem nen van doc duoc; `lengo` la Administrator nen
#    deploy van ghi duoc. Ca hai da kiem that 01/09.
$aclLenh = ("icacls C:\ProgramData\LTTLlm\gateway.env /inheritance:d " +
            "&& icacls C:\ProgramData\LTTLlm\gateway.env /remove:g *S-1-5-32-545")
ChayTrenB $aclLenh | Out-Null
$conUsers = ChayTrenB "icacls C:\ProgramData\LTTLlm\gateway.env"
if (($conUsers -join " ") -match "S-1-5-32-545|BUILTIN\\Users") {
    Canh "gateway.env VAN cho BUILTIN\Users doc - bearer token khong duoc bao ve."
} else {
    Dat "ACL gateway.env: chi SYSTEM + Administrators"
}

# --- 6. Kiem nhanh -------------------------------------------------------------
Buoc "6. Kiem import tren may B"
# !! Chay mot TEP .py, khong phai `python -c "..."` - quy tac 3 cua CLAUDE.md:
#    PowerShell nuot dau ngoac kep khi truyen cho .exe, va qua them mot lop ssh
#    nua thi hong chac chan. Da dinh mot lan trong phien nay.
$kq = ChayTrenB "$g\venv\Scripts\python.exe $g\gateway\llm_gateway\deploy\kiem_import.py"
$kq | ForEach-Object { Write-Host "  $_" }

Buoc "Xong"
Write-Host "  Buoc ke tiep:"
Write-Host "    1. Mo model:  sua LTT_LLM_MODELS trong $envDir\gateway.env"
Write-Host "    2. Cai dich vu (can Administrator tren may B):"
Write-Host "         powershell -ExecutionPolicy Bypass -File $Goc/gateway/llm_gateway/deploy/cai_dat_dich_vu.ps1"
Write-Host "    3. Nghiem thu:"
Write-Host "         powershell -ExecutionPolicy Bypass -File llm_gateway\deploy\kiem_tra.ps1"
