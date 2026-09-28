"""`check_xuong_dong.py` phai dem DUNG so dong doi that, khong chi in `0`.

🔴 **SU CO 28/09/2026.** Hook chan dung mot commit lat ket dong, va in:

    apps/prompt_ai_ommi/project_schema.py
       HEAD=tron  ->  hien tai=LF   (thay doi THAT: 0 dong)

Tep ay luc do co **14 dong doi that** (them hang so `IMAGE_JOB_TYPE` kem mot khoi
chu thich). Nguyen nhan: `git diff --numstat` **khong kem moc so** thi so cay lam
viec voi **INDEX**, con hook chay tu `pre-commit` — thoi diem thay doi **da duoc
stage**. Nen diff luon RONG. Thuoc la them `HEAD`.

## ⭐ Vi sao dang mot phep kiem, du PHAN QUYET cua hook van dung

Dong *"0 dong that"* la mot **khang dinh ve y dinh**: no noi voi nguoi doc *"ban
chi lat ket dong, khong doi noi dung"*. Va dong chi duong ngay duoi no khuyen
**ghi lai tep theo kieu HEAD**. Ai tin con so `0` roi lam dung the se **mat luon
phan noi dung vua sua** — hook van do (verdict dung), nhung no vua day nguoi doc
vao mot hanh dong pha hoai.

⇒ Mot cong chat luong khong chi phai KET LUAN dung; phan **giai thich** cua no
  cung la mot phep do, va mot phep do sai thi sai du ket luan co dung.

## ⛔ Vi sao phep kiem dung mot KHO GIT RIENG chu khong do tren cay nay

Hook doc `git status` + `git show HEAD:` cua cwd. Do tren cay that se (a) ghi vao
cay — thu bo phep kiem nay cam, va (b) phu thuoc vao viec cay dang co gi, tuc
ket qua doi theo phien khac. Mot kho nap trong `tmp_path` cho toan quyen dung
DUNG hai tinh huong can do.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
CHOT = GOC / "tools" / "check_xuong_dong.py"

CR = chr(13)
NL = chr(10)
CRLF = (CR + NL).encode()
LF = NL.encode()

#: So dong THEM vao ca "lat + doi noi dung". Phep kiem doc lai chinh hang so nay
#: chu ⛔ khong go `4` trong phan assert — doi so o day thi phep kiem van dung.
SO_DONG_THEM = 4


def _dung_kho(thu_muc: Path) -> Path:
    """Kho git co HAI tep: `a.py` thuan CRLF, `b.py` TRON (17 CRLF + 3 LF).

    `b.py` tron la co y: no la hinh dang cua `project_schema.py` trong su co, va
    no kiem luon rang `--ignore-cr-at-eol` chuan hoa CA HAI phia.
    """
    def g(*a: str) -> None:
        subprocess.run(["git", *a], cwd=thu_muc, capture_output=True, check=False)

    g("init", "-q", ".")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    # ⛔ `autocrlf` PHAI tat: neu may cua nguoi chay bat no, git se tu doi ket
    #    dong luc checkout va phep kiem do mot thu khac han.
    g("config", "core.autocrlf", "false")

    dong = [f"dong {i}".encode() for i in range(1, 21)]
    (thu_muc / "a.py").write_bytes(CRLF.join(dong) + CRLF)
    (thu_muc / "b.py").write_bytes(
        b"".join(x + (LF if i in (5, 10, 15) else CRLF) for i, x in enumerate(dong)))
    g("add", "a.py", "b.py")
    g("commit", "-qm", "base")
    return thu_muc


def _sua_va_stage(kho: Path) -> None:
    """`a.py`: CHI lat ket dong. `b.py`: lat ket dong VA them dong that."""
    (kho / "a.py").write_bytes((kho / "a.py").read_bytes().replace(CRLF, LF))

    noi = (kho / "b.py").read_bytes().replace(CRLF, LF).rstrip(LF).split(LF)
    noi += [f"# dong them {i}".encode() for i in range(SO_DONG_THEM)]
    (kho / "b.py").write_bytes(LF.join(noi) + LF)

    # ⭐ `git add` la mau chot cua ca phep kiem: no tai hien DUNG trang thai ma
    #    `pre-commit` thay (thay doi da stage), va do la trang thai lam con bo
    #    hien ra. Bo dong nay thi ban cu cung xanh.
    subprocess.run(["git", "add", "a.py", "b.py"], cwd=kho,
                   capture_output=True, check=False)


def _chay(kho: Path, ma_nguon: bytes) -> dict[str, str]:
    """Chay mot ban cua chot trong `kho`, tra `{ten tep: so dong that}`."""
    (kho / "_chot.py").write_bytes(ma_nguon)
    r = subprocess.run([sys.executable, "_chot.py"], cwd=kho, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    ra: dict[str, str] = {}
    ten = None
    for d in r.stdout.splitlines():
        s = d.strip()
        if s.endswith(".py") and not s.startswith("("):
            ten = s
        m = re.search(r"thay doi THAT: (\S+) dong", s)
        if m and ten:
            ra[ten] = m.group(1)
            ten = None
    assert ra, f"khong doc duoc dong 'thay doi THAT' nao:\n{r.stdout}\n{r.stderr}"
    return ra


def test_chi_lat_ket_dong_thi_bao_0_dong_that(tmp_path):
    """Ca DE: khong doi noi dung ⇒ `0`. Day la ca ban cu cung dung."""
    k = _dung_kho(tmp_path)
    _sua_va_stage(k)
    assert _chay(k, CHOT.read_bytes())["a.py"] == "0"


def test_lat_ket_dong_KEM_doi_noi_dung_thi_bao_DUNG_so_dong(tmp_path):
    """Ca su co: tep TRON, lat het ve LF, them `SO_DONG_THEM` dong."""
    k = _dung_kho(tmp_path)
    _sua_va_stage(k)
    ra = _chay(k, CHOT.read_bytes())
    assert ra["b.py"] == str(SO_DONG_THEM), (
        f"bao {ra['b.py']} dong that, dung ra {SO_DONG_THEM}. Mot con so 0 o day "
        f"noi voi nguoi doc rang ho CHI lat ket dong — va dong chi duong ngay "
        f"duoi khuyen ghi lai tep theo kieu HEAD, tuc MAT noi dung vua sua.")


def test_TIEM_LOI_bo_moc_HEAD_thi_ca_su_co_bao_SAI(tmp_path):
    """Doi chung: go `HEAD` khoi lenh diff ⇒ phep kiem tren PHAI do.

    ⭐ Khong co buoc nay thi hai phep tren co the dang xanh vi mot ly do khong
       lien quan (vd `_chay` doc sai dinh dang roi tra ve mot dict rong nhung
       assert van lot). Tiem dung con bo cu roi doi thay no lo dien la cach duy
       nhat chung minh phep kiem nay CO THE do.
    """
    k = _dung_kho(tmp_path)
    _sua_va_stage(k)

    goc = CHOT.read_text(encoding="utf-8")
    CU = '_git("diff", "HEAD", "--ignore-cr-at-eol", "--numstat",'
    assert CU in goc, (
        "khong tim thay lenh diff co `HEAD` — hoac ban va da bi go, hoac lenh "
        "duoc viet lai. Neu viet lai thi cap nhat chuoi neo nay.")
    hong = goc.replace(CU, '_git("diff", "--ignore-cr-at-eol", "--numstat",', 1)

    ra = _chay(k, hong.encode("utf-8"))
    assert ra["a.py"] == "0", "ca chi-lat phai van la 0 ngay ca khi tiem loi"
    assert ra["b.py"] == "0", (
        f"tiem loi ma van bao {ra['b.py']} — nghia la con bo goc KHONG phai thieu "
        f"`HEAD`, va phep kiem tren dang xanh vi mot ly do khac. Dung tin no.")


def test_phan_quyet_KHONG_doi_giua_hai_ban(tmp_path):
    """Ban va chi doi phan GIAI THICH: ca hai ban deu FAIL ⇒ cong khong doi.

    ⭐ Quan trong voi mot ban va vao cong chat luong: no ⛔ khong duoc am tham
       noi hay that chat cai cong. Do ca hai chieu tren CUNG mot kho.
    """
    k = _dung_kho(tmp_path)
    _sua_va_stage(k)

    goc = CHOT.read_text(encoding="utf-8")
    hong = goc.replace('_git("diff", "HEAD", "--ignore-cr-at-eol", "--numstat",',
                       '_git("diff", "--ignore-cr-at-eol", "--numstat",', 1)
    ma = {}
    for nhan, src in (("va", goc), ("cu", hong)):
        (k / "_chot.py").write_bytes(src.encode("utf-8"))
        r = subprocess.run([sys.executable, "_chot.py"], cwd=k, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        ma[nhan] = r.returncode
    assert ma["va"] == ma["cu"] == 1, (
        f"ma thoat doi: ban va {ma['va']}, ban cu {ma['cu']}. Ban va chi duoc "
        f"doi dong GIAI THICH, ⛔ khong duoc doi phan quyet cua cong.")
