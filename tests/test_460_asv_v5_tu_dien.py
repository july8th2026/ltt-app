"""Pha V5 — tu dien ten rieng: doc du lieu, van tay, va duong toi nguoi dung.

## Vi sao tep nay ton tai

`apps/ltt_voice/text_pipeline.chuan_hoa` nhan `tu_dien_rieng` tu truoc, va
`giong_noi` truyen no suot bon cho. Nang luc **da co**; thu thieu la mot duong
de khach cap du lieu vao. Do la ca thu ba trong mot ngay cua cung mot hinh dang
loi: *nang luc co, duong toi nguoi dung thi khong* — va khong phep kiem nao do
vi moi tang deu dung phan cua no.

⭐ Nen tep nay khong chi kiem `phan_tich()` doc dung. No kiem **ca duong**:
   form -> route -> `settings` -> giai doan -> van tay.

## Luat quan trong nhat nam o §B

Hai tu dien khac nhau tren **cung** mot cau chu cho hai tep tieng khac nhau.
Van tay khong doc tu dien thi hai ket qua ay dung chung mot khoa luu tru, va
khach thu hai nhan tieng cua khach thu nhat.

⚠️ Va cai bay **nguoc lai** cung that: them mot khoa rong vao van tay se lam
   MOI van tay cu doi, va ca kho tieng da sinh bi vut di ma khong ai yeu cau.
   Nen `{}` va `None` phai cho cung mot van tay. Ca hai chieu deu duoc chot duoi.
"""
from __future__ import annotations

import pytest

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong


# ══════════════════════════════════════════════════════════════════════════════
#  A. Doc du lieu — sai thi TU CHOI, khong doan
# ══════════════════════════════════════════════════════════════════════════════

def test_rong_va_trang_deu_ra_dict_rong():
    from apps.auto_scan_video import tu_dien

    assert tu_dien.phan_tich("") == {}
    assert tu_dien.phan_tich("   \n  \n") == {}
    assert tu_dien.phan_tich(None) == {}


def test_doc_duoc_dang_dung_va_bo_khoang_trang():
    from apps.auto_scan_video import tu_dien

    ra = tu_dien.phan_tich("  Nguyễn Huệ  =  Nguyễn Huệ  \n\nHà Nội=Hà Nội\n")
    assert ra == {"Nguyễn Huệ": "Nguyễn Huệ", "Hà Nội": "Hà Nội"}


def test_dong_THIEU_dau_bang_bi_TU_CHOI_chu_khong_bi_bo_qua():
    """⛔ Bo qua im lang mot dong la de khach tuong mot cai ten da duoc sua.

    Ho chi biet khi nghe lai video da giao — tuc sau khi da tra tien.
    """
    from apps.auto_scan_video import tu_dien

    with pytest.raises(tu_dien.TuDienLoi) as e:
        tu_dien.phan_tich("Nguyễn Huệ - Nguyễn Huệ")
    assert "2" not in str(e.value)          # phai chi dung dong 1


def test_thieu_mot_ve_thi_TU_CHOI():
    from apps.auto_scan_video import tu_dien

    for xau in ("Nguyễn Huệ =", "= Nguyễn Huệ", " = "):
        with pytest.raises(tu_dien.TuDienLoi):
            tu_dien.phan_tich(xau)


def test_mot_ten_KHAI_HAI_LAN_thi_TU_CHOI_chu_khong_lay_cai_sau():
    """Hai cach doc cho mot ten la mot mau thuan CUA KHACH. Chon ho mot cai la
    doan, va doan dung mot lan thi lan sau ho tin rang ta luon doan dung."""
    from apps.auto_scan_video import tu_dien

    with pytest.raises(tu_dien.TuDienLoi):
        tu_dien.phan_tich("Huệ = Huệ\nHuệ = Hue")


def test_co_TRAN_so_muc_va_do_dai():
    """Tu dien di vao MOI doan cua mot lan chay, tuc no nam trong vong lap tinh
    tien. Mot tu dien khong tran la mot hoa don khong co day."""
    from apps.auto_scan_video import tu_dien

    qua_nhieu = "\n".join(f"T{i} = t{i}" for i in range(tu_dien.SO_MUC_TOI_DA + 5))
    with pytest.raises(tu_dien.TuDienLoi):
        tu_dien.phan_tich(qua_nhieu)

    qua_dai = "x" * (tu_dien.DAI_TOI_DA + 1) + " = y"
    with pytest.raises(tu_dien.TuDienLoi):
        tu_dien.phan_tich(qua_dai)


# ══════════════════════════════════════════════════════════════════════════════
#  B. Van tay — CA HAI chieu cua cai bay
# ══════════════════════════════════════════════════════════════════════════════

def _vt(**kw):
    from apps.auto_scan_video import giong_noi

    goc = {"ma_doan": "d1", "chu": "xin chào", "voice_id": "v1", "preset": "p"}
    goc.update(kw)
    return giong_noi.van_tay_doan(**goc)


def test_HAI_tu_dien_khac_nhau_cho_HAI_van_tay_khac_nhau():
    """🔴 Luat trung tam. Thieu no thi khach thu hai nhan tieng cua khach thu
    nhat, va khong co gi trong he thong noi rang dieu do vua xay ra."""
    a = _vt(tu_dien={"Huệ": "Huệ"})
    b = _vt(tu_dien={"Huệ": "Hue"})
    assert a != b


def test_RONG_va_VANG_MAT_cho_CUNG_mot_van_tay():
    """⚠️ Chieu nguoc lai, va no cung that: `{}` nghia la "khong co tu dien", y
    het `None`. Cho chung hai van tay khac nhau se lam MOI van tay cu doi va vut
    ca kho tieng da sinh — mot phep don dep khong ai yeu cau."""
    assert _vt() == _vt(tu_dien=None) == _vt(tu_dien={})


def test_thu_tu_khoa_KHONG_doi_van_tay():
    """Hai dict cung noi dung, go khac thu tu, la CUNG mot tu dien."""
    assert _vt(tu_dien={"a": "A", "b": "B"}) == _vt(tu_dien={"b": "B", "a": "A"})


# ══════════════════════════════════════════════════════════════════════════════
#  C. Duong toi nguoi dung — cho khong tang nao so huu
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_loi_goi_van_tay_nao_duoc_QUEN_tu_dien():
    """🔑 `_van_tay` doi `tu_dien` la THAM SO BAT BUOC, khong mac dinh.

    ⛔ Ban dau toi dinh cho no mac dinh `None`. Neu the, quen mot loi goi se cho
       ra mot **bam sai** thay vi mot loi — va mot bam sai thi im lang, moi phep
       kiem van xanh, chi khach la nhan nham tep tieng.

    ⭐ Phep kiem nay doc chu ky that chu khong khop van ban, va no chot **cach
       hong khong the xay ra**, khong chot mot gia tri.
    """
    import inspect

    from apps.auto_scan_video import giai_doan_giong

    ts = inspect.signature(giai_doan_giong._van_tay).parameters["tu_dien"]
    assert ts.default is inspect.Parameter.empty, (
        "`tu_dien` co mac dinh — quen mot loi goi se thanh mot bam sai im lang")
    assert ts.kind is inspect.Parameter.KEYWORD_ONLY


def test_o_nhap_CO_MAT_tren_man_hinh(moi_truong):
    """Nang luc co ma khong co o nhap thi van la vo hinh voi khach — dung ca
    `NHAN_LOC["phong_cach"]` da song ba thang trong mach ma khong ai toi duoc."""
    a = moi_truong[1]
    van = a.get("/auto-scan-video/").text
    assert 'name="tu_dien"' in van


def test_tu_dien_SAI_bi_tu_choi_o_route_va_KHONG_tao_lan_chay(moi_truong,
                                                              tmp_path):
    """Cung luat voi vung che: mot dau vao sai KHONG duoc tao ra mot lan chay.

    ⚠️ Dung `_tao_run_cho` cua `test_423` chu khong tu dung form: mau tu
       dung cua toi nop mot tep 32 byte khong phai mp4 that va an ve 400, tuc
       no do vi mot ly do KHAC voi ly do no dinh do — mot phep kiem xanh/do
       nham nguyen nhan con te hon khong co phep kiem.
    """
    import platform_core.db as dbmod
    from apps.auto_scan_video import tables as T
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong

    db = next(dbmod.get_session())
    truoc = db.query(T.AsvRun).count()
    db.close()

    r = _mt._tao_run_cho(a, csrf, tmp_path,
                         tu_dien="Nguyễn Huệ - Nguyễn Huệ")

    db = next(dbmod.get_session())
    sau = db.query(T.AsvRun).count()
    db.close()
    assert sau == truoc, "mot tu dien sai van tao ra mot lan chay"
    # `_lai_voi_loi` tra **400 co chu y** (routes.py:434) — mot form bi tu
    #  choi khong duoc tra 200. Toi da ky vong 200 va ky vong ay moi la cai
    #  sai; doc ma roi moi chot.
    assert r.status_code == 400, r.status_code
    assert "=" in r.text, "trang loi phai noi ro dang dung"


def test_tu_dien_DUNG_di_vao_settings_cua_lan_chay(moi_truong, tmp_path):
    """🔑 Doan cuoi cua duong: form -> route -> `settings`. Thieu doan nay
    thi o nhap la mot cua gia — khach go vao, khong bao gio thay tac dung.
    """
    import platform_core.db as dbmod
    from apps.auto_scan_video import tables as T
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _mt._tao_run_cho(a, csrf, tmp_path, tu_dien="Huệ = Huê")
    assert r.status_code == 200, r.text[:300]

    db = next(dbmod.get_session())
    run = db.query(T.AsvRun).order_by(T.AsvRun.created_at.desc()).first()
    db.close()
    assert (run.settings or {}).get("tu_dien") == {"Huệ": "Huê"}
