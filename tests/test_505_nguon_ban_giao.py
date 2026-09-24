r"""NGUỒN BÀN GIAO — deploy chép từ một bản xuất BẤT BIẾN, không từ cây sống.

## Sự cố đứng sau tệp này (08/09/2026, 10:11)

Một phiên Claude khác chạy `git stash pop` **giữa** cửa sổ robocopy
(10:11:07–10:13:37). Production nhận `platform_core/jobs.py` ở trạng thái trung
gian — **526 dòng** trong khi commit có **478**. Và nó hỏng theo kiểu tệ nhất:

    EXITCODE=0 · /health/ready 200 · dau_van_tay.json khai dung commit do

Không dấu hiệu nào nói đĩa mang thứ khác. Chỉ `nghiem_thu_deploy` so với
**commit** mới lộ ra, mười lăm phút sau.

⛔ **Ba lớp bảo vệ đều không đủ.** Trước lượt ấy đã có: danh sách trắng
   `git status`, kiểm `mtime` 60 giây + `compileall`, hỏi lại tiến trình sát
   trước khi bấm. Cả ba trả lời về **một thời điểm**; không lớp nào giữ được cây
   đứng yên suốt 2,5 phút robocopy chạy sau đó.

⭐ *Cửa sổ ghi của `git` không đóng được từ phía người ghi — chỉ đóng được từ
   phía người đọc.* Nên nguồn phải **bất biến**, không phải được canh chừng.

## 🔴 Và `git archive` THUẦN là chưa đủ — phần suýt làm hỏng production

Đo 08/09: bản xuất commit **3.650 tệp**, bản đang chạy **4.556**. Phần lớn chênh
lệch là rác (cache công cụ 148, `bench/*.png` 664) — nhưng **mười** tệp là thứ
production **đang dùng**, và chúng gitignored **có chủ ý**:

    apps/upscalevideo/vendor/engine/realesrgan-ncnn-vulkan.exe
    apps/upscalevideo/vendor/engine/vcomp140.dll + vcomp140d.dll
    apps/upscalevideo/vendor/engine/models/*.bin + *.param   (6 tep)
    yolov8n.pt
    tools/vendor_a11y/axe.min.js

Một bản `git archive` thuần sẽ làm app `upscalevideo` **chết trên production**,
và chết **im lặng**: `EXITCODE=0`, `/health/ready` 200, và `nghiem_thu_deploy`
báo `thiếu 0` vì nó **chỉ đếm tệp `.py`**.

⇒ `$VAN_CHUYEN` không phải một tiện ích. Nó là **hợp đồng**.
"""
from __future__ import annotations

import pathlib
import re
import subprocess

import pytest

from tests.cay_nguon_deploy import ghi_chu_cay, goc_nguon_deploy
from tools.nghiem_thu_deploy import _phu_boi

GOC = pathlib.Path(__file__).resolve().parents[1]

#: 🔴 HAI GOC, VA CHUNG TRA LOI HAI CAU HOI KHAC NHAU.
#:
#:    `GOC`       — cay HIEN TAI. Dung cho *"ma dang sua co nhac ten tep nao"*.
#:    `GOC_NGUON` — cay ma DEPLOY CHEP TU (o worktree: cay chinh). Dung cho
#:                  *"tep gitignored co that tren dia khong"*.
#:
#: ⛔ Truoc 13/09/2026 ca hai deu la `GOC`, va hau qua la ba phep kiem trong tep
#:    nay do VINH VIEN o moi worktree: tep gitignored khong di theo
#:    `git worktree add`. Tuc mot phien lam viec dung luat (§5: moi chien dich
#:    mot cay rieng) thi khong bao gio dat duoc mot luot gate xanh — xem
#:    `tests/cay_nguon_deploy.py`.
GOC_NGUON = goc_nguon_deploy()
CAI_DAT = GOC / "setup" / "2-cai-dat.ps1"
VAN_BAN = CAI_DAT.read_text(encoding="ascii", errors="replace")


def _ma_thuc(t: str) -> str:
    """Bỏ chú thích và here-string, chỉ giữ **mã chạy được**.

    🔴 BỐN PHÉP KIỂM ĐẦU TIÊN CỦA TỆP NÀY ĐỎ VÌ THIẾU HÀM NÀY, và cả bốn đỏ vì
       cùng một lý do: chúng khớp vào **chính chú thích giải thích chúng**.

         · `"git worktree add" not in ...`  -> trúng câu *"`git archive` chứ
           KHÔNG `git worktree add`"*
         · regex chống `git archive | tar`  -> trúng câu cảnh báo về chính
           cái bẫy đó
         · `index("Stop-Service")`          -> trúng chú thích *"Chốt chạy
           TRƯỚC `Stop-Service`"*, nằm sớm hơn mã thật

    ⛔ Kho này đã ghi lớp lỗi ấy nhiều lần — *"một bánh cóc khớp với chính lời
       giải thích của nó thì không chốt gì"* — và tôi mắc lại nó trong đúng tệp
       đang viết cảnh báo về nó. Chú thích càng kỹ thì bề mặt va chạm càng lớn,
       nên với một `.ps1` dày chú thích như `2-cai-dat`, đọc văn bản thô **luôn**
       cho câu trả lời sai.

    ⚠️ Cắt theo DÒNG, không cắt `#` giữa dòng: `#` trong một chuỗi PowerShell là
       ký tự thường, và cắt nó sẽ ăn mất mã thật.
    """
    t = re.sub(r"@'.*?'@", "", t, flags=re.S)      # here-string nguyen van
    t = re.sub(r'@".*?"@', "", t, flags=re.S)      # here-string co noi suy
    return "\n".join(d for d in t.splitlines()
                     if not d.lstrip().startswith("#"))


NGUON = _ma_thuc(VAN_BAN)


def _van_chuyen() -> list:
    m = re.search(r"\$VAN_CHUYEN = @\((.*?)\)", NGUON, re.S)
    assert m, "khong tim thay $VAN_CHUYEN trong MA (khong phai trong chu thich)"
    return re.findall(r"'([^']+)'", m.group(1))


def _tep_dai_dien(mau: str) -> list:
    """Vài tệp THẬT nằm dưới một mẫu đường dẫn. Rỗng nếu không có tệp nào."""
    phan = mau.split("\\")
    if "*" not in mau:
        d = GOC_NGUON / mau.replace("\\", "/")
        if d.is_file():
            return [d]
        return [x for x in d.rglob("*") if x.is_file()][:1] if d.is_dir() else []
    goc = GOC_NGUON / phan[0]
    duoi = "/".join(phan[2:])
    ra = []
    for con in (sorted(goc.iterdir()) if goc.is_dir() else []):
        d = con / duoi
        if d.is_dir():
            ra += [x for x in d.rglob("*") if x.is_file()][:1]
        elif d.is_file():
            ra.append(d)
    return ra


# ── 1. Nguồn phải là bản xuất, không phải cây sống ──────────────────────────

def test_robocopy_chep_tu_BAN_XUAT_khong_tu_cay_song():
    """🔴 HỒI QUY 08/09/2026. `robocopy $src` chép từ cây đang sống."""
    m = re.search(r"^\$rc = robocopy (\S+) \$appDir", NGUON, re.M)
    assert m, "khong tim thay lenh robocopy chinh"
    assert m.group(1) == "$srcChep", (
        f"robocopy chep tu {m.group(1)} - phai la $srcChep (ban xuat bat bien)")


def test_ban_xuat_dung_git_archive_KHONG_dung_worktree():
    """`git archive` không chạm `.git`; `git worktree add` ghi vào
    `.git/worktrees`. Với bốn phiên dùng chung một `.git`, khác biệt đó không nhỏ."""
    assert "git -C $src archive" in NGUON
    assert "git worktree add" not in NGUON, (
        "dung `git worktree add` la ghi vao .git cua cay dung chung")


def test_KHONG_noi_ong_khi_giai_nen():
    """⛔ Ống của PowerShell 5.1 đi qua tầng văn bản và **làm hỏng dữ liệu nhị
    phân**. `git archive | tar -x` là một cái bẫy im lặng."""
    assert "archive --format=tar -o" in NGUON, "phai ghi ra tep tar roi giai nen"
    assert not re.search(r"git[^\n]*archive[^\n]*\|\s*(&\s*)?tar", NGUON), (
        "dang noi ong `git archive | tar` - hong du lieu nhi phan tren PS 5.1")


def test_compileall_chay_tren_BAN_XUAT():
    """Phạm vi kiểm phải trùng phạm vi giao.

    ⛔ Trước 08/09 nó quét cả `.claude/worktrees/` — sáu checkout của bốn phiên —
       nên một tệp đang được ghi ở cây **người khác** chặn được deploy. Đã xảy
       ra lúc 09:43. Và thông điệp `Error compiling` khi ấy nói sai nghĩa: nó
       nghĩa là *"có người đang gõ phím"*, không phải *"mã hỏng"*.
    """
    m = re.search(r"'-x', '\(node_modules[^\n]*\n\s*(\$\w+)\)", NGUON)
    assert m, "khong tim thay doi so duong dan cua compileall"
    assert m.group(1) == "$srcChep", (
        f"compileall quet {m.group(1)} - phai quet $srcChep")


# ── 2. Danh sách vận chuyển là HỢP ĐỒNG ────────────────────────────────────

def test_danh_sach_van_chuyen_ton_tai_va_khong_rong():
    assert _van_chuyen(), "danh sach van chuyen rong"


@pytest.mark.parametrize("can", [
    # -> apps/upscalevideo/engine.py:30  _EXE = _ENGINE_DIR / "realesrgan-..."
    "apps\\*\\vendor",
    # -> cutclipshort/adapters/yolo.py:29, va `cutclipshort/` CO tren production
    #
    # ⚠️ Suýt lọt khỏi danh sách: một lượt grep chỉ quét `apps/` và
    #    `platform_core/` ra **0 kết quả**, vì `cutclipshort/` là một gói ở
    #    **gốc kho**. Phạm vi tìm kiếm hẹp hơn phạm vi kết luận.
    "yolov8n.pt",
])
def test_moi_duong_LOAD_BEARING_deu_duoc_khai(can):
    """🔴 Ba đường này gitignored **có chủ ý** nhưng production **đọc lúc chạy**.

    Bỏ một cái ra khỏi danh sách là làm một app chết im lặng sau lượt deploy
    tiếp theo — `nghiem_thu_deploy` không thấy, vì nó chỉ đếm `.py`.
    """
    assert can in _van_chuyen(), f"thieu '{can}' trong $VAN_CHUYEN"


def test_moi_duong_khai_deu_CO_THAT_tren_dia():
    """⛔ ĐỐI CHỨNG NGƯỢC. Một đường khai mà không tồn tại là một dòng chết: nó
    làm danh sách trông đầy đủ hơn thực tế, và che đúng chỗ đang thiếu."""
    thieu = [m for m in _van_chuyen() if not _tep_dai_dien(m)]
    assert not thieu, (f"khai nhung khong co tren dia: {thieu} {ghi_chu_cay()}")


def test_moi_duong_khai_deu_THAT_SU_bi_gitignore():
    """Nếu một đường **không** bị ignore thì nó đã nằm trong `git archive` rồi,
    và khai lại ở đây là thừa — một dòng thừa hôm nay là một dòng gây nhầm mai.

    ⛔ Hỏi một TỆP đại diện, không hỏi thư mục: `.gitignore` bỏ qua
       `tools/vendor_a11y/axe.min.js` mà **không** bỏ qua `tools/vendor_a11y/`,
       và chính ca đó làm bản đầu của phép kiểm này đỏ oan.
    """
    thua = []
    for mau in _van_chuyen():
        for tep in _tep_dai_dien(mau)[:1]:
            r = subprocess.run(["git", "check-ignore", "-q", str(tep)],
                               cwd=GOC_NGUON, capture_output=True)
            if r.returncode != 0:
                thua.append(f"{mau} (vd {tep.relative_to(GOC_NGUON).as_posix()})")
    assert not thua, f"cac duong nay KHONG bi gitignore nen da co trong archive: {thua}"


#: Thư mục chứa rác sinh ra — không phải thứ ai đó cố ý vendor vào kho.
_RAC = ("__pycache__", ".ruff_cache", ".mypy_cache", ".import_linter_cache",
        ".pytest_cache", "node_modules", ".venv", "venv", "dist", "build",
        "test-results", "tmp", "logs", "data", "temp_videos", ".claude",
        "bench", ".playwright-cli", ".playwright-mcp", "secrets")


def _xd_cua_robocopy() -> set:
    """Thu muc ma robocopy cua `2-cai-dat.ps1` LOAI (`/XD ... /XF`).

    🔴 Do 19/09/2026 (L1 `phien/sua-test-do`): mot phien Codex de
       `.codex/worktrees/cli-compat-final-audit/` (ca mot ban sao kho) trong cay
       chinh ⇒ phep kiem nay do voi hang tram tep "chua khai" — trong khi
       robocopy loai `.codex` tu lau, tep do KHONG BAO GIO len production.
       `_RAC` chep tay tung thu muc nen lech `/XD`. Doc thang `/XD` tu ma deploy
       thi hai noi khong the lech nhau nua.
    """
    m = re.search(r"/XD\s+(.*?)\s+/XF", NGUON, re.S)
    assert m, "khong tim thay `/XD ... /XF` cua robocopy trong 2-cai-dat.ps1"
    return {w for w in m.group(1).replace("`", " ").split() if w}


def _gitignored_bi_ma_runtime_nhac() -> set:
    """Tập tệp **gitignored** mà mã chạy trên production có nhắc tên.

    Đây là **phép đo**, không phải một danh sách soạn tay — nó là vế đối chứng
    cho `$VAN_CHUYEN`.
    """
    loai = _xd_cua_robocopy()
    r = subprocess.run(
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
        # Hoi cay NGUON DEPLOY: day la cau "tren dia co gi", va dia co nghia la
        # dia ma `2-cai-dat.ps1` se doc. Xem `tests/cay_nguon_deploy.py`.
        cwd=GOC_NGUON, capture_output=True, text=True)
    ung_vien = []
    for d in r.stdout.split("\n"):
        d = d.strip()
        if not d or any(p in _RAC or p in loai for p in d.split("/")):
            continue
        if d.endswith((".pyc", ".log", ".png", ".jpg", ".mp4", ".json", ".txt",
                       ".md", ".tsbuildinfo", ".ini")):
            continue
        ung_vien.append(d)
    if not ung_vien:
        return set()

    # 🔴 PHAI LOC `tools/` VA `tests/` — xem chu thich o duoi ve lan do OAN.
    ma = subprocess.run(["git", "ls-files", "*.py"], cwd=GOC,
                        capture_output=True, text=True).stdout.split("\n")
    chay_that = [f for f in ma if f.strip()
                 and not f.startswith(("tools/", "tests/", "bench/"))]
    # 🔴 CHI MA THUC THI, ⛔ khong ke docstring/chu thich.
    #
    #    `.env` con lot mot lan nua sau khi da so theo ranh gioi tu: tham
    #    chieu DUY NHAT cua no trong ca kho la mot **docstring** o
    #    `public_api/examples.py`. Mot dong van xuoi noi "tep .env" KHONG lam
    #    cho `.env` thanh thu ma production doc — nhung phep kiem lai ket luan
    #    the, roi doi khai no vao `$VAN_CHUYEN`, tuc doi DEPLOY CHEP mot tep
    #    BI MAT len may chu. Sai ve phia hanh dong.
    #
    # ⭐ Cung lop loi voi `test_332` (do vi mot chuoi trong docstring) va voi
    #    `test_60` (da phai loc dung cach nay tu truoc). Kho CO SAN
    #    `ma_thuc_thi`; dung lai thay vi doc van ban tho.
    from tests.test_60_app_registry import ma_thuc_thi

    than = "\n".join(
        ma_thuc_thi((GOC / f).read_text(encoding="utf-8", errors="replace"))
        for f in chay_that if (GOC / f).is_file())
    # 🔴 SO THEO RANH GIOI TU, ⛔ KHONG so chuoi con tu do.
    #
    #    Ca 24/09: `.env` bi tinh la "ma runtime co nhac" — vi `.env` la CHUOI
    #    CON cua **`os.environ`**, co o hang chuc tep. Bat ky ai dat mot `.env`
    #    trong cay deu lam phep kiem nay do, va thong diep thi tro sang
    #    `$VAN_CHUYEN` — tuc no to giac mot chuyen khong xay ra.
    #
    # ⛔ Va day la CUNG MOT bai hoc ma tep nay da hoc ba dong duoi:
    #    `test__phu_boi_khong_khop_gan_dung` chot rang mau phai so THEO TUNG
    #    DOAN duong dan. Bai hoc do duoc sua o `_phu_boi` va **bo sot o day** —
    #    hai phep so cung tra loi cau "tep nay co duoc nhac khong", mot cai da
    #    sac, mot cai van cun.
    def _duoc_nhac(ten: str) -> bool:
        return re.search(rf"(?<![A-Za-z0-9_]){re.escape(ten)}(?![A-Za-z0-9_])",
                         than) is not None

    return {d for d in ung_vien if _duoc_nhac(pathlib.PurePosixPath(d).name)}


def test__phu_boi_khong_khop_gan_dung():
    """🔴 Fix round 2 cua `tools/nghiem_thu_deploy.py::_phu_boi` (xem chu thich
    o do): ban dau ham nay so CHUOI CON sau dau `*` (`sau.strip("/") in duong`),
    nen mau `apps/*/vendor` (dang Windows) khop NHAM `apps/upscalevideo/
    vendor_x.py` — mot tep KHONG duoc khai lot qua am tham chi vi "vendor" la
    chuoi con cua "vendor_x.py".

    `_phu_boi` gio import THANG tu `tools/nghiem_thu_deploy.py` — nguon that
    cho logic nay — thay vi chep lai o day de hai ban khong the lech nhau lan
    nua. Phep kiem nay ghim ca hai chieu: mau PHAI so THEO TUNG DOAN duong dan,
    khong so chuoi con tu do."""
    # Ten gan giong nhung KHONG phai doan duong day du -> KHONG duoc khop.
    assert not _phu_boi("apps/*/vendor", "apps/upscalevideo/vendor_x.py")
    assert not _phu_boi("apps/*/vendor", "apps/upscalevideo/xvendor/x.exe")
    # Doan duong day du -> PHAI khop.
    assert _phu_boi("apps/*/vendor", "apps/upscalevideo/vendor/engine/x.exe")


def test_DANH_SACH_VAN_CHUYEN_khop_dung_tap_DO_DUOC():
    """🔴 HAI CHIỀU, và không có `skip` nào.

    ⛔ BẢN ĐẦU CỦA PHÉP KIỂM NÀY TỰ BỎ QUA CHÍNH NÓ KHI MỌI THỨ ĐÚNG.

       Nó viết *"không còn tệp gitignored nào ngoài danh sách ⇒ `pytest.skip`"*.
       Nghe hợp lý, và hoàn toàn sai: ở trạng thái **khoẻ** nó không khẳng định
       gì cả, chỉ lên tiếng ở trạng thái **đã hỏng**. Bánh cóc `bo qua im lang`
       bắt được ngay (27 -> 28), và luật của kho đúng: *"một test bị bỏ qua là
       một test KHÔNG canh gì cả."*

    ⭐ Bản này xanh vì **hai tập bằng nhau** — một mệnh đề thật — chứ không vì
       không có gì để nói. Và nó bắt được **cả chiều ngược** mà bản cũ không
       thấy: một mục **thừa** trong danh sách (tệp đã khai nhưng không còn ai
       đọc) sẽ đi theo mọi lượt deploy mãi mãi mà không ai biết.

    ⚠️ GIỚI HẠN: phép đo bắt tham chiếu theo **tên tệp trong mã nguồn**. Một
       đường dẫn ghép hoàn toàn động (`Path(cfg["thu_muc"]) / ten_bien`) thì nó
       không thấy. Nó thu hẹp cửa, không đóng cửa.
    """
    do_duoc = _gitignored_bi_ma_runtime_nhac()
    khai = _van_chuyen()

    # Chieu 1: moi tep DO DUOC phai co mot muc khai phu no.
    thieu = sorted(d for d in do_duoc
                   if not any(_phu_boi(k, d) for k in khai))
    assert not thieu, (
        "tep gitignored duoc MA RUNTIME tham chieu nhung KHONG khai trong "
        "$VAN_CHUYEN:\n  " + "\n  ".join(thieu)
        + "\n=> hoac khai chung vao setup/2-cai-dat.ps1, hoac commit chung.")

    # Chieu 2: moi muc KHAI phai phu it nhat mot tep do duoc.
    thua = sorted(k for k in khai
                  if not any(_phu_boi(k, d) for d in do_duoc))
    assert not thua, (
        "muc khai trong $VAN_CHUYEN nhung KHONG mã runtime nao nhac toi:\n  "
        + "\n  ".join(thua)
        + "\n=> go chung ra; mot muc thua di theo moi luot deploy mai mai.")


# ── 3. Chuỗi alembic phải giải được trong bản xuất ─────────────────────────

def test_co_chot_kiem_chuoi_alembic_TRUOC_Stop_Service():
    """🔴 Đo 08/09: một migration **đã commit** có cha là một tệp **chưa theo
    dõi**. Bỏ tệp cha ra thì `ScriptDirectory` ném `KeyError` ngay khi dựng —
    alembic không giải được head **nào cả**.

    Với nguồn là `git archive`, mọi tệp chưa commit đều vắng mặt, nên một chuỗi
    phụ thuộc vào tệp untracked sẽ chết ở `alembic upgrade head` — bước chạy
    **sau `Stop-Service`**, tức sau khi đã tự tay tạo ra downtime.
    """
    assert "ScriptDirectory" in VAN_BAN, "thieu phep kiem chuoi alembic"

    # ⛔ ĐO BẰNG SỐ DÒNG CỦA MÃ THẬT, và đây là lần sửa thứ HAI của cùng phép
    #    kiểm này — đáng ghi vì hai lần sai theo hai kiểu khác nhau:
    #
    #      lần 1: đo trên văn bản thô -> trúng chú thích *"Chot chay TRUOC
    #             `Stop-Service`"*, nằm sớm hơn mọi lệnh
    #      lần 2: đo trên `NGUON` đã cắt chú thích -> nhưng `ScriptDirectory`
    #             nằm trong một **here-string**, mà `_ma_thuc` cắt here-string
    #
    # ⭐ Tức mỗi bản sửa lại rơi vào đúng vùng mù của bản trước. Cách thoát là
    #    thôi tìm một chuỗi và bắt đầu hỏi **dòng nào là mã**: quét từng dòng,
    #    bỏ dòng chú thích, rồi lấy chỉ số dòng.
    dong = VAN_BAN.splitlines()

    def _dong_ma(mau: str) -> int:
        for i, d in enumerate(dong):
            if not d.lstrip().startswith("#") and re.search(mau, d):
                return i
        return -1

    # `throw` cua cong alembic la MA THAT (khong nam trong here-string).
    i_kiem = _dong_ma(r"Chuoi alembic KHONG giai duoc")
    i_stop = _dong_ma(r"^\s*Stop-Service ")
    assert i_kiem >= 0, "khong tim thay `throw` cua cong alembic"
    assert i_stop >= 0, "khong tim thay LENH Stop-Service"
    assert i_kiem < i_stop, (
        f"cong alembic o dong {i_kiem+1} nam SAU Stop-Service (dong {i_stop+1}) "
        "- hong o do la da co downtime")


def test_chuoi_alembic_giai_duoc_khi_CHI_CO_tep_da_commit(tmp_path):
    """Bất biến: chuỗi alembic dựng **chỉ từ tệp đã commit** phải giải được.

    🔴 BẢN ĐẦU CỦA PHÉP KIỂM NÀY CHẶT HƠN BẤT BIẾN, và tôi giữ lại câu chuyện
       vì cái sai ấy có hình dạng đáng nhớ.

       Nó đòi **mọi** migration trên đĩa phải đã commit. Nghe hợp lý, và nó đỏ
       ngay trong vòng một giờ — nhưng vì một lý do **lành**: một phiên khác
       đang soạn `20260908_1100_workflow_v2_dinh_nghia.py`, một migration mới
       ở **ngọn** chuỗi.

    ⭐ Ngọn thì vô hại. `git archive` đơn giản không chứa nó, và chuỗi giải
       được tới `e7b2c94a1d38` như thường. Thứ nguy hiểm là một tệp chưa commit
       nằm ở **GỐC** — làm cha cho một migration đã commit. Đó là ca 08/09
       (`c9d4e1a77b02`), và khi ấy `ScriptDirectory` ném `KeyError` ngay lúc
       dựng: không head nào giải được, và deploy chết **sau `Stop-Service`**.

    ⛔ Một bánh cóc chặt hơn bất biến sẽ đỏ ở mọi phiên đang soạn migration —
       tức nó sẽ bị tắt trong một tuần, và khi ấy ta mất luôn phần nó chốt
       đúng. Nên phép kiểm này đo **đúng thứ deploy làm**: dựng lại tập tệp đã
       commit rồi hỏi alembic.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    r = subprocess.run(["git", "ls-files", "alembic"],
                       cwd=GOC, capture_output=True, text=True)
    tep = [d.strip() for d in r.stdout.split("\n") if d.strip()]
    assert tep, "khong doc duoc danh sach tep alembic da commit"

    # Dung lai DUNG thu `git archive` se cho: chi tep da commit.
    for d in tep:
        dich = tmp_path / d
        dich.parent.mkdir(parents=True, exist_ok=True)
        dich.write_bytes((GOC / d).read_bytes())

    cfg = Config()
    cfg.set_main_option("script_location", str(tmp_path / "alembic"))
    try:
        heads = ScriptDirectory.from_config(cfg).get_heads()
    except Exception as e:  # noqa: BLE001 - moi kieu hong deu la hong
        pytest.fail(
            f"chuoi alembic KHONG giai duoc tu tep da commit: "
            f"{type(e).__name__}: {e}\n"
            "Gan nhu chac chan co mot migration CHUA COMMIT dang lam CHA cho "
            "mot migration da commit. Commit no truoc khi deploy.")
    assert heads, "khong co head nao"


# ── 4. Dấu vân tay khai NỘI DUNG ĐÃ GIAO, không chỉ commit định giao ───────

def test_dau_van_tay_ghi_ca_noi_dung_va_nguon():
    """🔴 Sự cố 10:11: marker khai `c795ebc7` trong khi đĩa mang bản 526 dòng.

    Marker **không sai theo luật cũ của nó** — nó ghi commit mà deploy *định*
    giao. Nhưng người đọc hiểu nó là *"đĩa đang mang commit này"*, và một lượt
    rollback sau đó khôi phục một bản bẩn mà `/health/version` báo là hợp lệ.
    Sai số đẩy về phía **yên tâm**.
    """
    # ⛔ HỎI PHÉP GÁN, KHÔNG HỎI CHUỖI CON — và đây là bản sửa sau một đối
    #    chứng ĐỎ HỤT. Bản đầu viết `assert "noi_dung" in NGUON`; tôi gỡ dòng
    #    `noi_dung = $bam` ra khỏi script và phép kiểm **vẫn xanh**, vì chuỗi
    #    `noi_dung=` còn nằm trong một dòng `Ok "..."` in ra màn hình.
    #
    # ⭐ Tức một bánh cóc có thể được giữ xanh bởi **chính thông điệp mô tả nó**.
    #    Cùng họ với chuyện chú thích ở `_ma_thuc`, nhưng ở đây thủ phạm là một
    #    chuỗi hiển thị — thứ trông còn giống mã hơn cả chú thích.
    for khoa in ("noi_dung", "nguon", "so_tep"):
        assert re.search(rf"^\s*{khoa}\s*=\s*\S", NGUON, re.M), (
            f"dau van tay khong GAN truong `{khoa}` (chuoi con khong tinh)")
    assert "'cay-song'" in NGUON, (
        "phai phan biet ban giao tu BAN XUAT voi ban giao tu CAY SONG")


# ── 5. Ràng buộc chung của mọi script setup ────────────────────────────────

def test_van_thuan_ASCII_va_khong_BOM():
    """PowerShell 5.1 đọc `.ps1` không BOM theo bảng mã ANSI. Một dấu tiếng Việt
    làm hỏng cả câu lệnh và báo lỗi ở một dòng chẳng liên quan."""
    raw = CAI_DAT.read_bytes()
    xau = [i for i, b in enumerate(raw) if b > 127]
    assert not xau, f"co byte non-ASCII o vi tri {xau[:5]}"
    assert raw[:3] != b"\xef\xbb\xbf", "co BOM"


def test_duong_lui_van_con_khi_khong_co_git():
    """⛔ Bộ cài phải chạy được từ một **bản chép thuần** không có `.git` —
    `.DESCRIPTION` ở đầu tệp hứa điều đó, và lần cài đầu tiên trên một máy chủ
    mới đi đúng đường ấy."""
    assert re.search(r"\$srcChep\s*=\s*\$src\b", NGUON), (
        "khong con duong lui ve cay song khi khong doc duoc commit")
    assert "chep TU CAY SONG (duong lui)" in VAN_BAN, (
        "duong lui phai NOI RA rang no la duong lui")


def test_ten_tep_chi_tinh_la_DUOC_NHAC_khi_dung_ranh_gioi_tu():
    """🔑 Doi chung cho phep do o `_gitignored_bi_ma_runtime_nhac`.

    `.env` la chuoi con cua `os.environ`. Neu so chuoi con tho thi bat ky cay
    nao co mot tep `.env` cung lam phep kiem do — va thong diep tro sang
    `$VAN_CHUYEN`, tuc no to giac mot chuyen khong he xay ra.

    ⭐ Cung bai hoc voi `test__phu_boi_khong_khop_gan_dung` ngay tren: hai phep
       so cung tra loi mot cau hoi, va bai hoc chi duoc ap vao MOT cai.
    """
    import re as _re

    def nhac(ten, than):
        return _re.search(
            rf"(?<![A-Za-z0-9_]){_re.escape(ten)}(?![A-Za-z0-9_])", than)

    assert not nhac(".env", 'v = os.environ.get("X")'), "os.environ khong phai .env"
    assert not nhac(".env", "load_dotenv()"), "dotenv khong phai .env"
    # 🔑 Ve con lai: mot tham chieu THAT van phai duoc bat.
    assert nhac(".env", 'doc(".env")')
    assert nhac("config.json", 'P = "data/config.json"')
