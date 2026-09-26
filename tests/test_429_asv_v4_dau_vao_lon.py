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


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Duong tai len BEN VUNG (G6)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'asv.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


class _KhoR2Gia:
    """Kho GIONG R2: cap presigned, KHONG cho duong dan tren dia.

    ⭐ Hinh dang nay moi la hinh dang cua production. `LocalStorage` co
       `local_path`, nen mot phep kiem chi chay tren no se **khong bao gio** di
       vao nhanh presigned — va nhanh do chinh la thu G6 doi.
    """

    def __init__(self, tmp):
        self.goc = Path(tmp)
        self.da_mo: list[str] = []

    def _p(self, khoa):
        d = self.goc / khoa.replace("/", "__")
        return d

    def put(self, khoa, f, content_type=""):
        self._p(khoa).write_bytes(f.read())

    def exists(self, khoa):
        return self._p(khoa).exists()

    def size(self, khoa):
        return self._p(khoa).stat().st_size

    def open(self, khoa):
        self.da_mo.append(khoa)
        return open(self._p(khoa), "rb")

    def url_for(self, khoa, ttl_s=3600):
        return f"https://r2.vi-du/{khoa}?ky=gia"

    def local_path(self, khoa):
        return None                      # <- dung nhu R2

    def promote(self, staging_key, final_key, content_type=""):
        from platform_core.storage import StoredFile
        nguon = self._p(staging_key)
        dich = self._p(final_key)
        dich.write_bytes(nguon.read_bytes())
        nguon.unlink()
        return StoredFile(key=final_key, size=dich.stat().st_size,
                          content_type=content_type)


def test_nguon_soi_duoc_tra_URL_khi_kho_khong_co_dia(tmp_path):
    """Voi R2, ffprobe phai nhan mot URL — khong phai mot ban sao tren dia.

    🔑 `platform_core/media.py:81` da giai thich cai gia: mot video 2 GB di qua
       tunnel chi de doc mot con so.
    """
    kho = _KhoR2Gia(tmp_path)
    ra = assets.nguon_soi_duoc(kho, "asv/u/nguon/x.mp4")
    assert ra.startswith("https://")
    assert kho.da_mo == [], "da mo tep de doc — dang tai ve thay vi soi tai cho"


def test_nguon_soi_duoc_NEM_khi_kho_khong_tra_loi_duoc():
    """Im lang tai ca tep ve la dung hanh vi ham nay ton tai de khong lam."""
    class KhoCam:
        def local_path(self, k): return None
        def url_for(self, k, ttl_s=3600): return None

    with pytest.raises(assets.AssetError, match="khong soi duoc"):
        assets.nguon_soi_duoc(KhoCam(), "k")


def test_ve_cua_NGUOI_KHAC_khong_dung_duoc(db, tmp_path):
    """I6 — chu so huu duoc giai o PHIA MAY CHU, trong cau truy van.

    ⛔ Neu `upload_id` duoc tin, mot nguoi doan duoc ma ve cua nguoi khac se tao
       duoc mot lan chay tren video cua ho — va hoa don ve tay nguoi doan.
    """
    from apps.auto_scan_video import features
    from platform_core import upload_sessions
    from tests.conftest import bao_dam_user

    bao_dam_user(db, "u1")
    bao_dam_user(db, "u2")
    kho = _KhoR2Gia(tmp_path)
    phien = upload_sessions.create(
        db, user_id="u1", app_slug=features.SLUG, filename="a.mp4",
        content_type="video/mp4", expected_size=10,
        max_size=features.TRAN_BEN_VUNG,
        allowed_types=features.KIEU_VIDEO_HOP_LE)
    db.flush()

    with pytest.raises(features.KhongTimThay):
        features.tao_run_tu_ve(db, kho, owner_id="u2", upload_id=phien.id,
                               settings={"giong_id": "Minh Đức"})


def test_ve_khong_ton_tai_bao_KHONG_TIM_THAY_chu_khong_no(db, tmp_path):
    from apps.auto_scan_video import features
    from tests.conftest import bao_dam_user

    bao_dam_user(db, "u1")
    with pytest.raises(features.KhongTimThay):
        features.tao_run_tu_ve(db, _KhoR2Gia(tmp_path), owner_id="u1",
                               upload_id="khong-co-that", settings={"giong_id": "Minh Đức"})


def test_route_tao_UU_TIEN_duong_ben_vung_khi_co_ca_hai():
    """⚠️ Thu tu hai nhanh trong `tao` la mot quyet dinh, khong phai tinh co.

    Neu nhanh multipart dung truoc, mot client cu gui kem ca `upload_id` lan mot
    tep se lang le keo ca lan chay ve duong co tran 90 MB — dung dieu G6 cam.
    """
    import ast

    nguon = (GOC / "apps" / "auto_scan_video" / "routes.py").read_text(encoding="utf-8")
    cay = ast.parse(nguon)
    ham = next(f for f in ast.walk(cay)
               if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
               and f.name == "tao")

    dong_ben_vung = dong_multipart = None
    for nut in ast.walk(ham):
        if isinstance(nut, ast.Attribute) and nut.attr == "tao_run_tu_ve":
            dong_ben_vung = nut.lineno
        if isinstance(nut, ast.Attribute) and nut.attr == "tao_run_tu_tai_len":
            dong_multipart = nut.lineno

    assert dong_ben_vung is not None, "route khong con goi duong ben vung"
    assert dong_multipart is not None
    assert dong_ben_vung < dong_multipart, (
        "nhanh multipart dung TRUOC nhanh ben vung — mot client gui ca hai se bi "
        "keo ve duong co tran 90 MB")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  `upload_sessions` phai nhan slug co DAU GACH DUOI
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_app_trong_kho_deu_tao_duoc_ve_tai_len():
    """🔴 Truoc 2026-09-03, BAY app bi `create()` tu choi thang.

    `_SLUG` la `^[a-z0-9][a-z0-9-]{0,63}$` — khong co `_`. Nen `auto_scan_video`,
    `ltt_voice` (dang BAN), `ltt_llm`, `prompt_ai_ommi` va ba executor ASV deu
    khong dung duoc duong tai len ben vung cua nen tang.

    ⭐ Vi sao no khong lo ra: app duy nhat dang goi `upload_sessions` la
       `autosubvideo` — mot trong so it slug khong co gach duoi — con
       `tests/conftest.py:71` dat `APP_THU_SLUG="appthu"`, nen ca bo test chua
       bao gio di qua nhanh nay voi mot slug that.

    ⇒ Phep kiem nay chay tren **danh sach app that**, khong tren mot slug mau.
      Do la khac biet duy nhat khien no bat duoc thu ma `test_173` khong bat.
    """
    from platform_core.registry import discover
    from platform_core.upload_sessions import _SLUG

    tu_choi = sorted(a.manifest.slug for a in discover()
                     if not _SLUG.fullmatch(a.manifest.slug))
    assert tu_choi == [], (
        f"{len(tu_choi)} app khong tao duoc ve tai len: {tu_choi}. "
        f"`AppManifest` khong cam gach duoi, nen day la mot khiem khuyet cua "
        f"`upload_sessions._SLUG`, khong phai mot han che co chu y.")


def test_noi_rong_slug_KHONG_lam_hong_slug_hop_le_cu():
    """Doi chi duoc NOI RONG: moi slug hop le truoc day van phai hop le."""
    from platform_core.upload_sessions import _SLUG

    for hop_le in ("autosubvideo", "taoanh", "a", "a-b-c", "x9", "auto_scan_video"):
        assert _SLUG.fullmatch(hop_le), hop_le
    # Va nhung thu VAN phai bi tu choi — noi rong khong phai mo toang.
    for xau in ("", "-abc", "_abc", "ABC", "a/b", "a.b", "a b", "a" * 65):
        assert not _SLUG.fullmatch(xau), xau


# ══════════════════════════════════════════════════════════════════════════════
#  §4  `_duong_doc_duoc` an toan o BIEN (N-58 + N-59)
# ══════════════════════════════════════════════════════════════════════════════

class _KhoGiaR2:
    """Kho kieu R2: ⛔ KHONG co dia, nen `local_path` luon None."""

    def __init__(self, noi_dung: dict[str, bytes]):
        self._nd = noi_dung

    def local_path(self, key: str):
        return None

    def open(self, key: str):
        import io
        return io.BytesIO(self._nd[key])


def test_duong_doc_duoc_TU_TAO_thu_muc_chua_ton_tai(tmp_path):
    """🔴 N-58: 3/3 luot production chet `Errno 2` vi thu muc con chua duoc tao."""
    from apps.auto_scan_video.giai_doan_media import _duong_doc_duoc

    kho = _KhoGiaR2({"a/b/seg.wav": b"RIFFxxxx"})
    chua_co = tmp_path / "t0_seg_0001"
    assert not chua_co.exists()

    duong = _duong_doc_duoc(kho, "a/b/seg.wav", chua_co)

    from pathlib import Path as _P
    assert _P(duong).is_file()
    assert _P(duong).read_bytes() == b"RIFFxxxx"


def test_hai_khoa_vao_cung_thu_muc_KHONG_duoc_dung_mot_tep(tmp_path):
    """🔴 N-59: `giai_doan_qc.py:130-131` tai hai khoa vao CUNG mot thu muc.

    Ten tep co dinh ⇒ luot sau ghi de luot truoc ⇒ QC so ban ra voi CHINH NO.
    Loi IM LANG: ⛔ khong nem, chi lam mot phep do khong the truot.
    """
    from apps.auto_scan_video.giai_doan_media import _duong_doc_duoc

    kho = _KhoGiaR2({"ra/master.mp4": b"BAN-RA", "nguon/goc.mp4": b"NGUON"})
    d1 = _duong_doc_duoc(kho, "ra/master.mp4", tmp_path)
    d2 = _duong_doc_duoc(kho, "nguon/goc.mp4", tmp_path)

    assert d1 != d2, "hai khoa khac nhau ra cung mot duong"
    from pathlib import Path as _P
    assert _P(d1).read_bytes() == b"BAN-RA"
    assert _P(d2).read_bytes() == b"NGUON"
