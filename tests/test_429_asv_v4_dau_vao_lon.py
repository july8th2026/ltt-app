"""Auto Scan Video V4 — large input: streaming hash and the durable upload path.

V2 accepted video through `await video.read()` behind a 90 MB cap (`routes.py:79,155`),
then held those bytes while *also* writing a temp copy *and* streaming them into storage —
the whole video resident twice. `V3_TO_V4_CORRECTIONS` §4 makes durable large-video input a
**critical gate** (G6).

Two halves, and they fail differently:

**§1 streaming hash.** `assets.bam(Path(x).read_bytes())` is correct and cheap to keep
       believing in, because it never produces a wrong answer — it just makes the machine
       swap when two runs overlap. A defect with no wrong output is one that survives
       review.

**§2 the durable path.** `platform_core.upload_sessions` already does this, and already has
       a live caller (`apps/autosubvideo/services/source_drafts.py`). This is a **reuse**,
       so the tests here are mostly about not re-implementing it badly: owner resolved
       server-side, integrity checked, and the request never holding the body.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from apps.auto_scan_video import assets

GOC = Path(__file__).resolve().parent.parent


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Bam theo dong chay
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("co", [
    0,                    # tep rong — hop le voi mot phep bam, va de quen
    1,
    assets.KHOI_DOC - 1,  # ngay duoi mot khoi
    assets.KHOI_DOC,      # dung mot khoi
    assets.KHOI_DOC + 1,  # ngay tren mot khoi — cho vong lap phai lap lai
    assets.KHOI_DOC * 2 + 7,
])
def test_bam_tep_bang_HET_bam_toan_bo_bytes(tmp_path, co):
    """Hai duong phai cho cung mot ket qua, o moi kich thuoc quanh bien khoi.

    🔑 Day la ca ly do doi duoc: neu hai duong lech nhau du chi o mot kich thuoc,
       thi moi van tay sinh truoc ban doi se khong khop van tay sinh sau — va he
       qua khong phai mot loi, ma la **chay lai toan bo cac giai doan dat tien**
       cho moi lan chay cu.
    """
    tep = tmp_path / "m.bin"
    du_lieu = bytes((i * 7 + 3) % 256 for i in range(co))
    tep.write_bytes(du_lieu)

    assert assets.bam_tep(tep) == assets.bam(du_lieu)
    assert assets.bam_tep(str(tep)) == hashlib.sha256(du_lieu).hexdigest()


def test_bam_tep_KHONG_nap_ca_tep_vao_bo_nho(tmp_path, monkeypatch):
    """Chot HANH VI, khong chot loi hua.

    ⛔ Mot phep kiem chi so sanh ket qua se van xanh neu ai do viet lai
       `bam_tep` thanh `bam(Path(d).read_bytes())` — cung dau ra, mat het ly do
       ton tai. Nen o day ta do **kich thuoc lan doc lon nhat**.

    ⭐ Cach do: thay `open` bang mot ban boc ghi lai moi `read(n)`. Neu ham doc
       ca tep mot lan, se co mot lan doc lon hon KHOI_DOC.
    """
    tep = tmp_path / "m.bin"
    tep.write_bytes(b"x" * (assets.KHOI_DOC * 3 + 11))

    lan_doc: list[int] = []
    mo_that = open

    class BocDoc:
        def __init__(self, f):
            self._f = f

        def read(self, n=-1):
            khoi = self._f.read(n)
            lan_doc.append(len(khoi))
            return khoi

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self._f.close()
            return False

    def mo_boc(duong, che_do="r", *a, **kw):
        return BocDoc(mo_that(duong, che_do, *a, **kw))

    monkeypatch.setattr("builtins.open", mo_boc)
    ra = assets.bam_tep(tep)

    assert ra == hashlib.sha256(b"x" * (assets.KHOI_DOC * 3 + 11)).hexdigest()
    assert lan_doc, "khong doc gi ca — phep kiem khong do duoc gi"
    assert max(lan_doc) <= assets.KHOI_DOC, (
        f"co mot lan doc {max(lan_doc)} byte — `bam_tep` dang nap ca tep vao RAM")


def test_khong_con_module_ASV_nao_bam_bang_read_bytes():
    """Banh coc: `V4_RESOURCE_CPU_GPU_POLICY` cam bam media bang `read_bytes()`.

    ⭐ Doc AST, khong quet van ban — docstring cua chinh `assets.bam_tep` giai
       thich khuon xau bang cach viet no ra, va mot bo do quet van ban se bat
       dung loi giai thich do. (Lan thu tu trong phien nay; xem bao cao pha 04.)
    """
    import ast

    xau = []
    for tep in sorted((GOC / "apps" / "auto_scan_video").rglob("*.py")):
        if "__pycache__" in tep.parts:
            continue
        cay = ast.parse(tep.read_text(encoding="utf-8"))
        for nut in ast.walk(cay):
            # Khuon: bam(<gi do>.read_bytes())
            if not isinstance(nut, ast.Call):
                continue
            ten = (nut.func.attr if isinstance(nut.func, ast.Attribute)
                   else getattr(nut.func, "id", ""))
            if ten != "bam":
                continue
            for con in nut.args:
                if (isinstance(con, ast.Call)
                        and isinstance(con.func, ast.Attribute)
                        and con.func.attr == "read_bytes"):
                    xau.append(f"{tep.relative_to(GOC)}:{nut.lineno}")
    assert xau == [], (
        f"con bam media bang read_bytes(): {xau} — dung `assets.bam_tep(duong)`")


def test_bo_do_read_bytes_that_su_bat_duoc():
    """Bo do tren mot tap gan rong phai tu chung minh no khong phai den xanh."""
    import ast

    def co_vi_pham(nguon: str) -> bool:
        cay = ast.parse(nguon)
        for nut in ast.walk(cay):
            if not isinstance(nut, ast.Call):
                continue
            ten = (nut.func.attr if isinstance(nut.func, ast.Attribute)
                   else getattr(nut.func, "id", ""))
            if ten != "bam":
                continue
            for con in nut.args:
                if (isinstance(con, ast.Call)
                        and isinstance(con.func, ast.Attribute)
                        and con.func.attr == "read_bytes"):
                    return True
        return False

    assert co_vi_pham("x = assets.bam(Path(nguon).read_bytes())")
    assert co_vi_pham("x = bam(p.read_bytes())")
    # Ba dang KHONG duoc bao dong:
    assert not co_vi_pham("x = assets.bam_tep(nguon)")
    assert not co_vi_pham("x = assets.bam(goi)")          # bam mot bytes co san
    assert not co_vi_pham("d = Path(x).read_bytes()")     # doc, khong de bam


# ══════════════════════════════════════════════════════════════════════════════
#  §1b  Doc tu KHO cung phai theo dong chay
# ══════════════════════════════════════════════════════════════════════════════

class _KhoGia:
    """Kho toi thieu, ghi lai moi lan `read(n)` de do duoc kich thuoc lan doc."""

    def __init__(self, du_lieu: bytes):
        self._du_lieu = du_lieu
        self.lan_doc: list[int] = []

    def open(self, khoa):
        kho = self

        class F:
            def __init__(self):
                self._i = 0

            def read(self, n=-1):
                if n is None or n < 0:
                    khoi = kho._du_lieu[self._i:]
                else:
                    khoi = kho._du_lieu[self._i:self._i + n]
                self._i += len(khoi)
                kho.lan_doc.append(len(khoi))
                return khoi

            def close(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return F()


def test_do_va_bam_khong_nap_ca_artifact_vao_bo_nho():
    """`kiem_toan_ven` chay cho MOI artifact cua MOI lan chay.

    ⛔ Truoc pha 05 no goi `_doc_het`, nghia la `final.mp4` — ca cuon phim — nam
       trong RAM cua worker moi lan doi soat toan ven. Khong loi nao bao: phep
       kiem van dung, chi la worker phinh len bang kich thuoc san pham no vua lam.
    """
    du_lieu = b"z" * (assets.KHOI_DOC * 2 + 5)
    kho = _KhoGia(du_lieu)

    co, checksum = assets.do_va_bam(kho, "asv/u/r/render/final.mp4")

    assert co == len(du_lieu)
    assert checksum == hashlib.sha256(du_lieu).hexdigest()
    assert max(kho.lan_doc) <= assets.KHOI_DOC, (
        f"co mot lan doc {max(kho.lan_doc)} byte — dang nap ca artifact vao RAM")


def test_do_va_bam_dung_voi_artifact_rong():
    kho = _KhoGia(b"")
    co, checksum = assets.do_va_bam(kho, "k")
    assert co == 0
    assert checksum == hashlib.sha256(b"").hexdigest()


def test_tai_nguon_ve_dia_KHONG_nap_ca_video_vao_RAM(tmp_path):
    """🔴 Cho nguy hiem hon ca route, va no khong co tran nao.

    `routes.py` cat o 90 MB. `giai_doan_media._duong_doc_duoc` thi khong: voi
    kho R2 no tai nguon ve dia, va truoc pha 05 no lam viec do bang
    `dich.write_bytes(f.read())` — ca video trong RAM. Duong tai len ben vung
    cua V4 cho phep 2 GiB, va toan bo 2 GiB do se di thang qua dong do.
    """
    from apps.auto_scan_video import giai_doan_media

    du_lieu = b"v" * (assets.KHOI_DOC * 3 + 17)
    kho = _KhoGia(du_lieu)

    duong = giai_doan_media._duong_doc_duoc(kho, "asv/u/nguon/x.mp4", tmp_path)

    assert Path(duong).read_bytes() == du_lieu
    assert max(kho.lan_doc) <= assets.KHOI_DOC, (
        f"co mot lan doc {max(kho.lan_doc)} byte — dang nap ca video vao RAM")
