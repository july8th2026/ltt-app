"""ASV final (22/09) — hop dong ngon ngu: nguon {zh,en,vi}, dich {vi,en}.

Chot bon cua, moi cua mot cau hoi:

  §1 `ngon_ngu.kiem_cap`          — cap khach khai o CUA, truoc credit
  §2 `kiem_nguon_da_doan`         — ASR doan ra gi thi chot lai ngay sau ASR
  §3 `rang_giong`                 — giong phai o CUNG lan voi dich
  §4 loi nhac `vi` KHONG troi     — mo `en` khong duoc doi mot chu cua duong `vi`

⛔ Khong phep kiem nao o day goi model, ASR hay giong that.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (cache_chung, cai_dat, giong_noi, hop_dong_v4,  # noqa: E402
                                  long_tieng, nan_cho_vua, ngon_ngu as nn, qc_ai,
                                  rang_giong)
from tests import test_423_asv_giao_dien as _mt  # noqa: E402

moi_truong = _mt.moi_truong

TU_CHON = hop_dong_v4.CHE_DO_GIONG_TU_CHON
TU_KHOP = hop_dong_v4.CHE_DO_GIONG_TU_KHOP


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Cap khai o cua
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("nguon,dich", [
    ("zh", "vi"), ("zh", "en"), ("en", "vi"), ("vi", "en"), ("auto", "vi"),
    ("", "en"), ("", ""),
])
def test_cap_trong_hop_dong_DUOC_nhan(nguon, dich):
    n, d = nn.kiem_cap(nguon, dich)
    assert d in nn.DICH_HOP_LE and (n == nn.TU_DOAN or n in nn.NGUON_HOP_LE)


@pytest.mark.parametrize("nguon,dich", [
    ("zh", "zh"),      # zh khong bao gio la dich — khong co giong zh
    ("ja", "vi"),      # nguon ngoai hop dong
    ("vi", "vi"),      # trung nhau
    ("en", "en"),
    ("en", "fr"),
])
def test_cap_ngoai_hop_dong_bi_TU_CHOI(nguon, dich):
    with pytest.raises(nn.NgonNguError):
        nn.kiem_cap(nguon, dich)


def test_tap_dich_nam_trong_tap_lan_giong():
    from apps.ltt_voice.lan_ngon_ngu import LAN_HOP_LE
    assert set(nn.DICH_HOP_LE) <= set(LAN_HOP_LE)
    assert hop_dong_v4.NGON_NGU_DICH_HOP_LE == nn.DICH_HOP_LE


def test_ho_so_CU_khong_co_khoa_dich_la_vi():
    """V4–V6 chi sinh tieng Viet: vang khoa = `vi` la su that, khong phai doan."""
    assert cai_dat.tu_ho_so({}).ngon_ngu_dich == "vi"
    assert cai_dat.tu_ho_so({"ngon_ngu_dich": "en"}).ngon_ngu_dich == "en"
    assert cai_dat.chuan_hoa({"ngon_ngu_dich": "EN"})["ngon_ngu_dich"] == "en"


def _nop(client, csrf, tmp_path, **them):
    from tests.fixtures.asv_media import tiny_mp4
    tep = tiny_mp4(tmp_path / "a.mp4", duration_s=1.0)
    from apps.ltt_voice.giong_mau import DANH_SACH
    du_lieu = {"csrf_token": csrf, "che_do": "fit_original",
               "che_do_giong": TU_CHON, "giong_id": DANH_SACH[0].ma, **them}
    with open(tep, "rb") as f:
        return client.post("/auto-scan-video/tao", data=du_lieu,
                           files={"video": ("a.mp4", f, "video/mp4")})


def test_HTTP_cap_trung_nhau_bi_TU_CHOI_truoc_khi_tao_run(moi_truong, tmp_path):
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, ngon_ngu_nguon="vi", ngon_ngu_dich="vi")
    assert r.status_code == 400
    assert "trùng nhau" in r.text


def test_HTTP_zh_sang_vi_DUOC_nhan_va_LUU_vao_ho_so(moi_truong, tmp_path):
    """Doi chung cua bai tren: neu cua tu choi MOI cap thi bai tren van xanh."""
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, ngon_ngu_nguon="zh", ngon_ngu_dich="vi")
    assert r.status_code == 200, r.text[:300]

    import platform_core.db as dbmod
    from sqlalchemy import select
    from apps.auto_scan_video.tables import AsvRun
    db = next(dbmod.get_session())
    try:
        run = db.execute(select(AsvRun).order_by(AsvRun.created_at.desc())).scalars().first()
        cai = cai_dat.doc(run)
        assert (cai.ngon_ngu_nguon, cai.ngon_ngu_dich) == ("zh", "vi")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Chot sau ASR
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("asr,dich,ra", [("zh", "vi", "zh"), ("yue", "en", "zh"),
                                          ("en", "vi", "en"), ("vi", "en", "vi")])
def test_ASR_doan_trong_hop_dong_thi_DI_TIEP(asr, dich, ra):
    assert nn.kiem_nguon_da_doan(asr, dich) == ra


@pytest.mark.parametrize("asr,dich", [("ja", "vi"), ("", "vi"), ("vi", "vi"), ("en", "en")])
def test_ASR_doan_ngoai_hop_dong_thi_DUNG_truoc_giai_doan_tra_tien(asr, dich):
    with pytest.raises(nn.NgonNguError):
        nn.kiem_nguon_da_doan(asr, dich)


def test_khoa_cache_chep_loi_MANG_ngon_ngu_dich():
    """Dung lai ban chep loi cheo dich la bo qua phep chot §2."""
    import inspect
    ma = inspect.getsource(cache_chung.dau_vao_noi_dung)
    assert '"ngon_ngu_dich"' in ma


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Giong cung lan voi dich
# ══════════════════════════════════════════════════════════════════════════════

def test_giong_mau_lan_vi_KHONG_doc_ban_en():
    from apps.ltt_voice.giong_mau import DANH_SACH
    vi = next(g for g in DANH_SACH if g.ngon_ngu == "vi")
    with pytest.raises(rang_giong.RangGiongError):
        rang_giong.kiem_o_cua(None, owner_id="u", che_do=TU_CHON, giong_id=vi.ma,
                              ngon_ngu_dich="en")
    # doi chung: cung giong, dich vi -> qua
    rang_giong.kiem_o_cua(None, owner_id="u", che_do=TU_CHON, giong_id=vi.ma,
                          ngon_ngu_dich="vi")


def test_giong_cua_khach_DUA_LAN_DICH_cho_ltt_voice_chot(monkeypatch):
    goi = {}

    def _giai(db, *, owner_id, voice_id="", preset="", ngon_ngu=""):
        goi["ngon_ngu"] = ngon_ngu
        return ("ref", "p")

    monkeypatch.setattr(giong_noi, "giai_giong", _giai)
    rang_giong.kiem_o_cua(None, owner_id="u", che_do=TU_CHON, giong_id="giong-rieng",
                          ngon_ngu_dich="en")
    assert goi["ngon_ngu"] == "en"


def test_AUTO_MATCH_loc_ung_vien_THEO_LAN_dich(monkeypatch):
    from apps.ltt_voice import giong_mau
    thay = {}
    that = giong_mau.loc

    def _loc(**kw):
        thay.update(kw)
        return that(**kw)

    monkeypatch.setattr(giong_mau, "loc", _loc)
    dd = rang_giong.DacDiemMongMuon(gioi="nam", vung="bac", phong_cach="")
    yc = rang_giong.YeuCau(che_do=TU_KHOP, dac_diem=dd, ngon_ngu_dich="en")
    kq = rang_giong.rang(None, owner_id="u", yeu_cau=yc)
    assert thay.get("ngon_ngu") == "en"
    # ⚠️ Hom nay kho giong mau chua co giong `en` (20/20 lan `vi`) ⇒ CHUA_RANG,
    #    KHONG phai lay mot giong `vi` doc ban tieng Anh.
    if not that(ngon_ngu="en"):
        assert not kq.da_chot


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Loi nhac `vi` giu nguyen tung ky tu
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_nhac_vi_GIU_cum_da_nghiem_thu():
    """🔴 **Nhip khong con la mot chuoi go tay — banh coc da DOI CHO (23/09).**

    Ban cu chot dung chuoi `"khoang 4,5 am tiet/giay"`. Con so 4,5 do CHUA TUNG
    DUOC DO: `tools/do_toc_do_giong.py --che-do tts` doc sau doan tieng Viet
    that bang giong `Minh Duc` va do duoc **3,35** am tiet/giay (2 vong, 12 luot,
    do lech chuan 0,15) — tuc moi cau cua luot viet dau dai hon khe ~34% theo
    dung thiet ke, va luot nghiem thu nen v3 tra gia bang 11 luot viet lai.

    ⇒ Banh coc bay gio chot dieu DUNG: cac cum **tinh ra tu `ngon_ngu.NHIP`**,
      khong go tay o hai cho. Doi con so la doi MOT cho, va phai co so do moi.
    """
    d = [{"ma": "a", "chu": "x", "bat": 0, "ket": 1}]
    lt = long_tieng.loi_nhac(d, tat_ca=d, ngon_ngu_goc="zh", dac_diem_giong={})[0]["content"]
    assert lt.startswith("Ban la bien tap vien long tieng tieng Viet. Ban KHONG dich "
                         "tung chu: ban viet lai cau thoai sao cho nguoi Viet nghe")
    assert f"({nn.CUM['vi']['nhip']})" in lt
    assert nn.CUM["vi"]["nhip"] == "khoang 3,35 am tiet/giay"
    nan = nan_cho_vua.loi_nhac_nan({"ma": "a", "goc": "x"}, chu_hien_tai="y",
                                   giay_do_duoc=4.0, khe=3.0)[0]["content"]
    assert "Van phai la tieng Viet noi tu nhien" in nan
    assert nn.CUM["vi"]["nhip_moi_giay"] in nan
    qc = qc_ai.loi_nhac_ngu_nghia([{"ma": "a", "goc": "x", "chu": "y"}])[0]["content"]
    # ⭐ GEMBA-MQM (91d921f4): loi nhac hoi LIET KE LOI + MUC NGHIEM TRONG,
    #    khong con hoi cau NHI PHAN dat/khong dat.
    assert qc.startswith("Ban soat ban long tieng tieng Viet. Voi moi cap "
                         "(cau goc, cau tieng Viet), hay LIET KE cac loi dich")


def test_loi_nhac_en_KHONG_con_mot_chu_tieng_Viet_nao_ve_dich():
    d = [{"ma": "a", "chu": "x", "bat": 0, "ket": 1}]
    for van in (
        long_tieng.loi_nhac(d, tat_ca=d, ngon_ngu_goc="zh", dac_diem_giong={},
                            ngon_ngu_dich="en")[0]["content"],
        nan_cho_vua.loi_nhac_nan({"ma": "a", "goc": "x"}, chu_hien_tai="y",
                                 giay_do_duoc=4.0, khe=3.0, ngon_ngu_dich="en")[0]["content"],
        qc_ai.loi_nhac_ngu_nghia([{"ma": "a", "goc": "x", "chu": "y"}], "en")[0]["content"],
    ):
        assert "tieng Viet" not in van and "nguoi Viet" not in van
        assert "tieng Anh" in van


def test_van_tay_long_tieng_DOI_khi_doi_dich():
    kw = dict(checksum_ban_ghi="c", van_tay_ban="b", ma_giong="g", provider="p", model="m")
    assert (long_tieng.van_tay_long_tieng(**kw, ngon_ngu_dich="vi")
            != long_tieng.van_tay_long_tieng(**kw, ngon_ngu_dich="en"))
