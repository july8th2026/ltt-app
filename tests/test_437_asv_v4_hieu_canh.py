"""Auto Scan Video V4 — hieu canh (VLM) + ho so noi dung, va DUONG TINH TIEN
lan dau chay that (pha 11).

**§1 phan hoi sai luoc do KHONG phai artifact thanh cong** — yeu cau 5. Va mot
     phan biet dat gia: mot canh **da doc va tra ve rac** khac han mot canh
     **chua doc**. Cai dau da ton tien va phai vao so cai; cai sau thi chua.

**§2 checkpoint theo CANH** — mot lan VLM hong o canh 47 khong duoc bat 46 canh
     truoc chay lai; chung da tra tien roi.

**§3 ngu canh CO CHAN** — cua so thi giac do duoc 65.536 token. Gui ca ban chep
     loi kem moi canh cham tran do theo cach te nhat: xanh o canh 1, 413 o canh
     40, sau khi da tra tien cho 39 canh.

**§4 duong tinh tien DANG SONG** — 🔑 pha 06 va pha 08 deu ghi no rang "chua co
     gi goi `su_dung.ghi`". Pha 11 la nguoi goi tra tien dau tien, nen day la
     cho tra no do. So cai phai ghi o **ca ba** nhanh: da giao, tu choi, mo ho.

⛔ Khong phep kiem nao goi model that.
"""
from __future__ import annotations

import ast
import json
import pathlib

import pytest

from apps.auto_scan_video import ai, hieu_canh as hc, su_dung as sd
from apps.auto_scan_video import features, pipeline
from apps.auto_scan_video.tables import AsvRun, AsvStage

GOC = pathlib.Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "auto_scan_video"


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


def _run(db, *, owner="u1", held=1000) -> AsvRun:
    r = AsvRun(owner_id=owner, source_key="asv/u1/x.mp4", settings={"giong_id": "Minh Đức"},
               credit_held=held)
    db.add(r); db.flush()
    for g in pipeline.CHUOI:
        db.add(AsvStage(run_id=r.id, owner_id=owner, stage=g.ten))
    db.flush()
    return r


def _kq(noi_dung: str) -> dict:
    """Boc mot chuoi thanh KET QUA cua `ai.goi`.

    ⭐ `doc_hieu_canh` nhan ca ket qua chu khong nhan rieng `noi_dung`, va do
       la ban sua 09/09: boc `noi_dung` ra bang tay lam mat `finish_reason`,
       tuc lam mat thu duy nhat phan biet "model tra sai" voi "model het tran
       token giua khoi suy nghi".

    ⚠️ `finish_reason="stop"` o day la co y: cac ca duoi day deu la model DA
       tra loi xong roi tra sai, khong phai bi cat.
    """
    return {"noi_dung": noi_dung, "finish_reason": "stop", "suy_nghi": ""}


def _canh_ok(**k) -> str:
    """Mot phan hoi VLM dung hinh dang ma `loi_nhac_canh` YEU CAU.

    🔴 Ban nay tung boc trong mot khoa `canh` — mot hinh dang khong loi nhac nao
       hoi va khong model nao duoc bao tra ve. Tuc bo test tu cung cap dau vao
       cho mot nhanh chi ton tai de chieu no, va nhanh THAT (phan hoi phang, thu
       ma loi dan mo ta) khong duoc mot phep kiem nao chay qua. Pha 27 bo lop
       boc o ca ba cho: loi dan, khai bao `DOC_CANH`, va o day.
    """
    d = {"loai": "phong van", "chu_the": ["nguoi dan"], "hanh_dong": "noi",
         "cam_xuc": "binh tinh", "quan_trong": 0.8, "de_xuat": "giu",
         "do_tin": 0.9, "ly_do": "co loi thoai chinh", "canh_bao": []}
    d.update(k)
    return json.dumps(d, ensure_ascii=False)


class _Do:
    """`SuDung` cua nen tang, gia."""

    def __init__(self, vao=100, ra=50, tin=True):
        self.token_vao, self.token_ra, self.dang_tin = vao, ra, tin


def _tiem_goi(monkeypatch, *, noi_dung="", loi=None, do=None):
    def _gia(db, thao_tac, messages, **k):
        if loi is not None:
            raise loi
        return {"noi_dung": noi_dung, "provider": "ltt_llm",
                "model": "qwen38-vision", "su_dung": do or _Do()}
    monkeypatch.setattr(ai, "goi", _gia)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Luoc do nghiem ngat
# ══════════════════════════════════════════════════════════════════════════════

def test_doc_duoc_phan_hoi_dung_luoc_do():
    h = hc.doc_hieu_canh(_kq(_canh_ok()), "canh_0001")
    assert h.ma_canh == "canh_0001" and h.de_xuat == hc.GIU
    assert h.quan_trong == 0.8 and h.do_tin == 0.9
    assert h.chu_the == ("nguoi dan",)


@pytest.mark.parametrize("xau, vi_sao", [
    (_canh_ok(de_xuat="bia_ra"), "de_xuat ngoai tap hop"),
    (_canh_ok(quan_trong=5), "quan_trong ngoai [0,1]"),
    (_canh_ok(quan_trong=-1), "quan_trong am"),
    (_canh_ok(do_tin="rat tin"), "do_tin khong phai so"),
    (_canh_ok(chu_the="mot chuoi"), "chu_the khong phai mang"),
    (_canh_ok(canh_bao={"a": 1}), "canh_bao khong phai mang"),
    ('{}', "thieu de_xuat va do_tin"),
    ('{"de_xuat": "giu"}', "co de_xuat nhung thieu do_tin"),
    ('{"canh": {"de_xuat": "giu", "do_tin": 0.9}}',
     "phan hoi boc trong mot khoa `canh` — hinh dang khong ai hoi"),
    ("khong phai json", "khong co JSON nao"),
])
def test_phan_hoi_sai_luoc_do_thi_NEM(xau, vi_sao):
    """⛔ Mot truong thieu thanh `None` di tiep se lo ra o pha 12 duoi dang
    "khong canh nao duoc giu" — mot thong bao khong lien quan gi den nguyen
    nhan, va nguoi doc se di tim o nham cho."""
    with pytest.raises((hc.HieuCanhError, ai.LuocDoSai)):
        hc.doc_hieu_canh(_kq(xau), "canh_0001")


def test_truong_qua_dai_bi_CAT_chu_khong_bi_tu_choi():
    """⭐ Mot cau `ly_do` 5.000 ky tu khong lam hong ket qua — no chi la mot
    model noi nhieu. Cat va di tiep; tu choi o day la vut ca canh."""
    h = hc.doc_hieu_canh(_kq(_canh_ok(ly_do="x" * 5000)), "c1")
    assert len(h.ly_do) <= 500


def test_ho_so_LOC_ve_dung_ba_mat_cua_catalog():
    """🔴 Mot mat thu tu se cho ra mot bo loc khong bao gio khop — cung ly do
    voi `rang_giong` pha 09."""
    van = json.dumps({"the_loai": "tai lieu", "nhip": "cham",
                      "dac_diem_giong": {"gioi": "nu", "vung": "bac",
                                         "tuoi": "30", "mau_toc": "den"}})
    hs = hc.doc_ho_so(van)
    assert set(hs.dac_diem_giong) <= {"gioi", "vung", "phong_cach"}
    assert hs.dac_diem_giong["gioi"] == "nu"


def test_ho_so_thieu_truong_bat_buoc_thi_NEM():
    with pytest.raises((hc.HieuCanhError, ai.LuocDoSai)):
        hc.doc_ho_so('{"the_loai": "tai lieu"}')      # thieu `nhip`


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Ngu canh co chan
# ══════════════════════════════════════════════════════════════════════════════

def test_chi_lay_loi_thoai_TRONG_canh():
    """⭐ Mot canh 4 giay khong can biet phut thu 30 noi gi — gui no la tra tien
    token cho mot thu model se bo qua."""
    bg = {"doan": [{"bat": 0, "ket": 3, "chu": "trong canh."},
                   {"bat": 50, "ket": 52, "chu": "xa lac."}]}
    assert hc.ngu_canh_cho_canh(bg, 0.0, 5.0) == "trong canh."


def test_ngu_canh_bi_CHAN_do_dai():
    bg = {"doan": [{"bat": 0, "ket": 100, "chu": "cau. " * 2000}]}
    ra = hc.ngu_canh_cho_canh(bg, 0.0, 100.0)
    assert len(ra) <= hc.NGU_CANH_MOI_CANH


def test_cat_o_dau_CAU_chu_khong_giua_tu():
    """⚠️ Mot cau cut lam model doan tiep phan thieu, va no doan bang token cua
    khach."""
    bg = {"doan": [{"bat": 0, "ket": 9, "chu": ("mot cau hoan chinh. " * 200)}]}
    ra = hc.ngu_canh_cho_canh(bg, 0.0, 9.0, toi_da=100)
    assert ra.endswith("."), f"cat giua chung: {ra[-30:]!r}"


def test_tran_ngu_canh_hop_ly_so_voi_cua_so_THI_GIAC():
    assert hc.NGU_CANH_MOI_CANH <= 4000
    assert ai.cua_so_ngu_canh(ai.DOC_CANH) < ai.cua_so_ngu_canh(ai.DICH_THUAT)


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Van tay: doi prompt = mat cache
# ══════════════════════════════════════════════════════════════════════════════

def test_van_tay_ON_DINH_voi_cung_dau_vao():
    a = hc.van_tay_canh("c1", "ngu canh", 2, 0.4)
    assert a == hc.van_tay_canh("c1", "ngu canh", 2, 0.4)


@pytest.mark.parametrize("doi", [
    {"ma_canh": "c2"}, {"ngu_canh": "khac"}, {"so_khung": 3}, {"nguong": 0.5},
])
def test_doi_bat_ky_dau_vao_nao_thi_van_tay_DOI(doi):
    goc = dict(ma_canh="c1", ngu_canh="x", so_khung=2, nguong_canh=0.4)
    moi = dict(goc)
    moi.update({("nguong_canh" if k == "nguong" else k): v
                for k, v in doi.items()})
    assert hc.van_tay_canh(**goc) != hc.van_tay_canh(**moi)


def test_doi_PHIEN_BAN_PROMPT_thi_van_tay_DOI(monkeypatch):
    """⛔ Thieu no thi doi mot cau prompt xong, cache van khop, va lan chay dung
    lai ket qua sinh boi prompt CU — mot thay doi san pham khong bao gio toi
    khach."""
    a = hc.van_tay_canh("c1", "x", 2, 0.4)
    monkeypatch.setattr(hc, "PHIEN_BAN_HIEU_CANH", hc.PHIEN_BAN_HIEU_CANH + 1)
    assert hc.van_tay_canh("c1", "x", 2, 0.4) != a


def test_van_tay_gom_CA_phien_ban_cua_cua_goi(monkeypatch):
    """Hai phien ban doi doc lap: cau hoi (pha 11) va cua goi (pha 08)."""
    a = hc.van_tay_canh("c1", "x", 2, 0.4)
    monkeypatch.setattr(ai, "PHIEN_BAN_LUOC_DO", ai.PHIEN_BAN_LUOC_DO + 1)
    assert hc.van_tay_canh("c1", "x", 2, 0.4) != a


# ══════════════════════════════════════════════════════════════════════════════
#  §4  DUONG TINH TIEN — no cua pha 06 va pha 08, tra o day
# ══════════════════════════════════════════════════════════════════════════════

def test_luot_DA_GIAO_ghi_so_cai_voi_so_TOKEN_do_duoc(db, monkeypatch):
    run = _run(db)
    _tiem_goi(monkeypatch, noi_dung=_canh_ok(), do=_Do(120, 80, True))

    ai.goi_tinh_tien(db, run, ai.DOC_CANH, [{"role": "user", "content": "x"}],
                     stage=pipeline.CONTENT_PROCESS, item_key="canh_0001")

    dong = sd.cac_dong(db, run)
    assert len(dong) == 1
    assert dong[0].trang_thai == sd.DA_GIAO
    assert dong[0].don_vi == sd.TOKEN and dong[0].so_luong == 200
    assert dong[0].ghi_chu["token_vao"] == 120


def test_provider_KHONG_tra_so_do_thi_ghi_don_vi_LUOT(db, monkeypatch):
    """🔴 `cong_vlm.SuDung.dang_tin` = False. Hai cach gian nhat deu la noi doi:
    ghi `so_luong=0` la bia rang no mien phi; ghi `TU_CHOI` la bia rang no chua
    chay. Thu do duoc la **mot luot da giao**."""
    run = _run(db)
    _tiem_goi(monkeypatch, noi_dung=_canh_ok(), do=_Do(0, 0, False))

    ai.goi_tinh_tien(db, run, ai.DOC_CANH, [{"role": "user", "content": "x"}],
                     stage=pipeline.CONTENT_PROCESS, item_key="c1")

    d = sd.cac_dong(db, run)[0]
    assert d.trang_thai == sd.DA_GIAO
    assert d.don_vi == sd.LUOT and d.so_luong == 1.0
    assert d.ghi_chu.get("khong_do_duoc") is True


def test_luot_TU_CHOI_van_duoc_ghi_va_KHONG_mang_credit(db, monkeypatch):
    run = _run(db)
    _tiem_goi(monkeypatch, loi=ai.AiError("provider tu choi"))

    with pytest.raises(ai.AiError):
        ai.goi_tinh_tien(db, run, ai.DOC_CANH, [{"role": "user", "content": "x"}],
                         stage=pipeline.CONTENT_PROCESS, item_key="c1")

    d = sd.cac_dong(db, run)[0]
    assert d.trang_thai == sd.TU_CHOI and d.credit == 0
    assert features.tong_da_dung(db, run) == 0


def test_luot_MO_HO_duoc_ghi_va_CHAN_duong_thu_lai(db, monkeypatch):
    """⛔ Chi ghi khi thanh cong la de mot lan mo ho bien mat khoi so sach —
    dung luc no can duoc nhin thay nhat."""
    run = _run(db)
    _tiem_goi(monkeypatch, loi=ai.AiMoHo("mat ket noi"))

    with pytest.raises(ai.AiMoHo):
        ai.goi_tinh_tien(db, run, ai.DOC_CANH, [{"role": "user", "content": "x"}],
                         stage=pipeline.CONTENT_PROCESS, item_key="c1")

    assert len(sd.cac_mo_ho(db, run)) == 1
    with pytest.raises(features.AsvError):
        features.thu_lai_giai_doan(db, run.id, run.owner_id,
                                   pipeline.CONTENT_PROCESS)


def test_cua_chan_ngan_sach_chay_TRUOC_khi_goi(db, monkeypatch):
    """🔑 Het ngan sach thi hong SACH SE truoc khi tieu, khong phai mot hoa don
    bat ngo sau khi tieu."""
    run = _run(db, held=5)
    da_goi = []
    monkeypatch.setattr(ai, "goi", lambda *a, **k: da_goi.append(1))

    with pytest.raises(features.AsvError):
        ai.goi_tinh_tien(db, run, ai.DOC_CANH, [{"role": "user", "content": "x"}],
                         stage=pipeline.CONTENT_PROCESS, item_key="c1",
                         uoc_credit=999)
    assert da_goi == [], "da goi model du ngan sach khong du"


def test_lap_lai_CUNG_canh_khong_ghi_so_cai_hai_lan(db, monkeypatch):
    """⭐ `ma_dispatch` gom (thao tac, giai doan, ma canh) nen mot lan chay lai
    cung canh bi rang buoc `UNIQUE(run_id, ma_dispatch)` chan — va do la mot
    THANH CONG, khong phai loi: no vua chan mot lan tinh tien thu hai."""
    run = _run(db)
    _tiem_goi(monkeypatch, noi_dung=_canh_ok(), do=_Do(10, 10, True))

    for _ in range(3):
        ai.goi_tinh_tien(db, run, ai.DOC_CANH, [{"role": "user", "content": "x"}],
                         stage=pipeline.CONTENT_PROCESS, item_key="canh_0001")

    assert len(sd.cac_dong(db, run)) == 1, "ghi so cai nhieu lan cho mot canh"
    sd.doi_soat(db, run)


def test_moi_canh_la_MOT_don_vi_viec_rieng(db, monkeypatch):
    """§2: mot lan VLM hong o canh 47 khong duoc bat 46 canh truoc chay lai."""
    run = _run(db)
    _tiem_goi(monkeypatch, noi_dung=_canh_ok(), do=_Do(10, 10, True))

    for i in range(1, 4):
        ai.goi_tinh_tien(db, run, ai.DOC_CANH, [{"role": "user", "content": "x"}],
                         stage=pipeline.CONTENT_PROCESS, item_key=f"canh_{i:04d}")

    assert len(features.cac_don_vi(db, run.id, pipeline.CONTENT_PROCESS)) == 3
    assert len(sd.cac_dong(db, run)) == 3
    sd.doi_soat(db, run)


def test_hai_khach_KHONG_dung_chung_so_cai(db, monkeypatch):
    """Yeu cau 6: mot canh hong cua khach nay khong duoc cham so cua khach kia."""
    a, b = _run(db, owner="u-a"), _run(db, owner="u-b")
    _tiem_goi(monkeypatch, noi_dung=_canh_ok(), do=_Do(10, 10, True))

    ai.goi_tinh_tien(db, a, ai.DOC_CANH, [{"role": "user", "content": "x"}],
                     stage=pipeline.CONTENT_PROCESS, item_key="canh_0001")
    ai.goi_tinh_tien(db, b, ai.DOC_CANH, [{"role": "user", "content": "x"}],
                     stage=pipeline.CONTENT_PROCESS, item_key="canh_0001")

    assert {d.owner_id for d in sd.cac_dong(db, a)} == {"u-a"}
    assert {d.owner_id for d in sd.cac_dong(db, b)} == {"u-b"}
    assert len(sd.cac_dong(db, a)) == len(sd.cac_dong(db, b)) == 1


def test_so_ke_gom_duoc_chi_phi_theo_nang_luc(db, monkeypatch):
    """`cost aggregation evidence` cua pha nay."""
    run = _run(db)
    _tiem_goi(monkeypatch, noi_dung=_canh_ok(), do=_Do(100, 100, True))
    for i in range(1, 4):
        ai.goi_tinh_tien(db, run, ai.DOC_CANH, [{"role": "user", "content": "x"}],
                         stage=pipeline.CONTENT_PROCESS, item_key=f"c{i}")

    ke = sd.so_ke(db, run)
    theo = {m["nang_luc"]: m for m in ke["theo_nang_luc"]}
    assert theo["doc_canh"]["don_vi"] == sd.TOKEN
    assert theo["doc_canh"]["so_luong"] == 600
    assert ke["tong"]["da_giao"] == 3


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Pham vi: chua cat, chua render, chua TTS
# ══════════════════════════════════════════════════════════════════════════════

def test_pha_11_KHONG_cat_render_hay_sinh_tieng():
    cay = ast.parse((APP / "hieu_canh.py").read_text(encoding="utf-8"))
    goi = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            f = n.func
            goi.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    for cam in ("cat", "render", "ket_xuat", "goi_cong", "tong_hop", "sinh"):
        assert cam not in goi, f"hieu_canh.py goi {cam!r} — ngoai pham vi pha 11"


def test_hieu_canh_di_qua_CUA_GOI_chu_khong_tu_goi_dieu_phoi():
    van = (APP / "hieu_canh.py").read_text(encoding="utf-8")
    assert "dieu_phoi" not in van
    assert "from . import ai" in van


def test_prompt_thuoc_ve_ASV_khong_phai_nen_tang():
    """§ranh gioi pha 08: ASV so huu prompt/luoc do; nen tang so huu van chuyen."""
    van = (APP / "hieu_canh.py").read_text(encoding="utf-8")
    assert "def loi_nhac_canh" in van and "def loi_nhac_ho_so" in van
