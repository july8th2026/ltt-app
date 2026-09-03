"""Pha 16 — ban do thoi gian va ban phoi am.

Nam nhom:

  A. Phep doi     — moc NGUON sang moc BAN RA, va cai gi KHONG co anh
  B. Ke hoach     — lap tren truc BAN RA, khong tron hai dong ho
  C. Ban phoi     — bieu thuc ffmpeg, chia lo, chuan am luong mot lan
  D. Hai preset   — giu hinh giu nguyen do dai; cat thi theo canh con lai
  E. KHONG AI     — pha nay cam goi model, chot bang AST
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from apps.auto_scan_video import am_master, ban_do_thoi_gian as bd, thoi_gian as tg

# 🔴 Cac phep kiem chay het chuoi cham toi `audio_prepare`.
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401


# ══════════════════════════════════════════════════════════════════════════════
#  A. Phep doi
# ══════════════════════════════════════════════════════════════════════════════

def test_giu_nguyen_thi_moc_khong_doi():
    m = bd.BanDoThoiGian.giu_nguyen(100.0)
    assert m.ra(0.0) == 0.0
    assert m.ra(37.5) == 37.5
    assert m.thoi_luong_ra == 100.0
    assert m.so_cho_noi == 0


def test_moc_SAU_mot_canh_bi_cat_lui_lai_dung_bang_phan_da_cat():
    """🔴 Menh de trung tam cua ca pha.

    Giu [0;10) va [30;50). Giay 35 cua nguon la giay 15 cua ban ra — vi 20 giay
    o giua da bien mat. Dat mot doan tieng o giay 35 cua ban ra la dat no vao mot
    cho khac han cho no thuoc ve, va sai so do **tich luy** theo tung canh cat.
    """
    m = bd.BanDoThoiGian.tu_khoang([(0, 10), (30, 50)], thoi_luong_nguon=50.0)
    assert m.ra(5.0) == 5.0
    assert m.ra(30.0) == 10.0
    assert m.ra(35.0) == 15.0
    assert m.thoi_luong_ra == 30.0
    assert m.so_cho_noi == 1


def test_moc_NAM_TRONG_phan_cat_KHONG_co_anh():
    """⛔ `None`, khong phai moc gan nhat.

    Ep ve moc gan nhat la bien mot cau thoai **da bi cat** thanh mot cau thoai
    **dat sai cho** — doi mot mat mat NHIN THAY duoc thanh mot loi KHO TIM.
    """
    m = bd.BanDoThoiGian.tu_khoang([(0, 10), (30, 50)], thoi_luong_nguon=50.0)
    assert m.ra(20.0) is None


def test_ra_gan_nhat_ton_tai_cho_DUNG_MOT_viec():
    """Nen nhac la mot dong lien tuc: cho noi phai la mot moc CO THAT.

    ⛔ Loi thoai thi khong duoc dung ham nay — xem phep kiem tren.
    """
    m = bd.BanDoThoiGian.tu_khoang([(0, 10), (30, 50)], thoi_luong_nguon=50.0)
    assert m.ra_gan_nhat(20.0) == 10.0      # dau khoang giu ke tiep
    assert m.ra_gan_nhat(35.0) == 15.0      # trong phan giu thi giong `ra`


def test_hai_khoang_LIEN_NHAU_duoc_gop():
    """⭐ Giua hai canh lien nhau cung duoc giu **khong co cho cat nao**. De
    chung tach roi la tao mot ranh gia trong moi phep tinh sau do."""
    m = bd.BanDoThoiGian.tu_khoang([(0, 10), (10, 20)], thoi_luong_nguon=20.0)
    assert m.giu == ((0.0, 20.0),)
    assert m.so_cho_noi == 0


def test_khoang_ROI_KHONG_bi_sap_xep_lai():
    """⛔ Sap xep lai la dung lai canh phim — mot quyet dinh bien tap khong ai o
    day duoc phep lam. `tu_khoang` sap theo THOI GIAN, khong theo thu tu nhap."""
    m = bd.BanDoThoiGian.tu_khoang([(30, 50), (0, 10)], thoi_luong_nguon=50.0)
    assert m.giu == ((0.0, 10.0), (30.0, 50.0))


def test_ban_ra_KHONG_BAO_GIO_dai_hon_nguon():
    """Loi hua cua hop dong V4, chot nhu mot **he qua** do qua duong dung that.

    🔴 Ban dau day la mot chot RIENG trong `kiem()`, va no **khong bao gio no
       duoc**: cac khoang khong chong lan va deu ket thuc trong `[0, T]` thi tong
       cua chung luon <= T. Mot chot khong bao gio no trong nhu mot lop bao ve,
       khong bao ve gi, va noi doi voi nguoi doc ve thu dang duoc canh giu.

    ⭐ Nen no bi go khoi ma, va menh de duoc do o day — tren nhieu hinh dang dau
       vao di qua `tu_khoang`, ke ca nhung dau vao co y lam hong.
    """
    for khoang, nguon in (
            ([(0, 10), (30, 50)], 50.0),
            ([(0, 50)], 50.0),
            ([(30, 50), (0, 10)], 50.0),        # nhap khong theo thu tu
            ([(0, 10), (10, 20), (20, 30)], 30.0),   # lien nhau, se duoc gop
            ([(0, 10), (5, 20)], 20.0),         # chong lan nhau
    ):
        m = bd.BanDoThoiGian.tu_khoang(khoang, thoi_luong_nguon=nguon)
        assert m.thoi_luong_ra <= nguon + 1e-6, (
            f"{khoang} cho ban ra {m.thoi_luong_ra} > nguon {nguon}")


def test_khoang_VUOT_thoi_luong_nguon_thi_NEM():
    """Cai `kiem()` that su bat duoc: mot khoang ket thuc NGOAI nguon."""
    with pytest.raises(bd.BanDoError, match="vượt quá"):
        bd.kiem(bd.BanDoThoiGian(((0.0, 200.0),), 100.0))


def test_hai_khoang_CHONG_LAN_thi_NEM():
    with pytest.raises(bd.BanDoError, match="chồng lấn"):
        bd.kiem(bd.BanDoThoiGian(((0.0, 20.0), (10.0, 30.0)), 50.0))


def test_ban_do_RONG_thi_NEM():
    with pytest.raises(bd.BanDoError, match="không giữ lại"):
        bd.kiem(bd.BanDoThoiGian((), 50.0))


def test_ban_do_doc_di_ghi_lai_GIU_NGUYEN_van_tay():
    """Bai hoc pha 14: mot bo tuan tu hoa khong co bo giai tuan tu la mot dinh
    dang chua ai thu doc."""
    m = bd.BanDoThoiGian.tu_khoang([(0, 10), (30, 50)], thoi_luong_nguon=50.0)
    lai = bd.BanDoThoiGian.tu_dict(m.sang_dict())
    assert lai.van_tay() == m.van_tay()
    assert lai.giu == m.giu


# ══════════════════════════════════════════════════════════════════════════════
#  B. Ke hoach lap tren truc BAN RA
# ══════════════════════════════════════════════════════════════════════════════

def _muc(n=3, buoc=10.0, dai=2.0):
    return [{"ma": f"seg_{i:04d}", "bat": i * buoc, "ket": i * buoc + dai}
            for i in range(n)]


def test_khong_co_ban_do_thi_hanh_vi_KHONG_DOI():
    """⭐ Preset giu hinh khong duoc doi mot mili giay nao vi pha 16."""
    muc = _muc()
    dai = {m["ma"]: 1.5 for m in muc}
    a = tg.lap_ke_hoach(muc, dai, tong_giay=30.0, che_do="fit_original")
    b = tg.lap_ke_hoach(muc, dai, tong_giay=30.0, che_do="fit_original",
                        ban_do=bd.BanDoThoiGian.giu_nguyen(30.0))
    assert [d["dat_tai_ms"] for d in a["doan"]] == [d["dat_tai_ms"] for d in b["doan"]]


def test_ke_hoach_dat_doan_tren_truc_BAN_RA():
    """🔴 Voi mot canh bi cat o giua, doan thu ba phai lui lai."""
    muc = _muc(3, buoc=10.0, dai=2.0)          # bat o 0, 10, 20
    dai = {m["ma"]: 1.5 for m in muc}
    # Cat [12; 18): doan 0 va 1 giu nguyen, doan 2 (bat o 20) lui 6 giay.
    ban_do = bd.BanDoThoiGian.tu_khoang([(0, 12), (18, 30)], thoi_luong_nguon=30.0)
    ke = tg.lap_ke_hoach(muc, dai, tong_giay=30.0, ban_do=ban_do)
    theo_ma = {d["ma"]: d for d in ke["doan"]}
    assert theo_ma["seg_0000"]["dat_tai_ms"] == 0
    assert theo_ma["seg_0002"]["dat_tai_ms"] == 14_000, (
        "doan thu ba phai o giay 14 cua ban ra (20 - 6), khong phai giay 20")
    assert ke["tong_ms"] == 24_000


def test_doan_thuoc_phan_DA_CAT_ma_van_co_tieng_thi_NEM():
    """⛔ Mot cau thoai thuoc canh da cat khong duoc troi sang canh khac."""
    muc = [{"ma": "seg_0000", "bat": 0.0, "ket": 2.0},
           {"ma": "seg_0001", "bat": 14.0, "ket": 16.0}]
    dai = {m["ma"]: 1.5 for m in muc}
    ban_do = bd.BanDoThoiGian.tu_khoang([(0, 12), (18, 30)], thoi_luong_nguon=30.0)
    with pytest.raises(tg.ThoiGianError, match="đã cắt"):
        tg.lap_ke_hoach(muc, dai, tong_giay=30.0, ban_do=ban_do)


def test_ngan_sach_doan_nhan_MOC_DA_DOI_khong_phai_muc_goc():
    """🔴 Loi ma chinh ban va cua pha nay suyt tao ra.

    Ban truoc nhan `muc` roi tu doc `muc[i]["bat"]` — gio NGUON — rot trir vao
    `tong_ms` gio BAN RA. Hieu hai moc nguon **khong bang** khoang cach cua chung
    o ban ra khi giua chung co mot canh bi cat.
    """
    import inspect

    tham = list(inspect.signature(tg.ngan_sach_doan).parameters)
    assert tham[0] == "moc_ms", (
        "tham so dau phai la MOC DA DOI, khong phai `muc` goc")
    assert tg.ngan_sach_doan([0, 2000, 4000], 0, tong_ms=10_000) == 2000
    assert tg.ngan_sach_doan([0, 2000, 4000], 2, tong_ms=10_000) == 6000


def test_ban_do_di_CUNG_ke_hoach():
    """Mot ke hoach dat doan o giay 74 vo nghia neu khong biet giay 74 cua ban ra
    ung voi dau trong nguon. Hai nua tach roi la hai nua se lech phien ban."""
    muc = _muc()
    ke = tg.lap_ke_hoach(muc, {m["ma"]: 1.5 for m in muc}, tong_giay=30.0,
                         ban_do=bd.BanDoThoiGian.tu_khoang(
                             [(0, 12), (18, 30)], thoi_luong_nguon=30.0))
    assert "ban_do" in ke
    lai = bd.BanDoThoiGian.tu_dict(ke["ban_do"])
    assert lai.thoi_luong_ra == 24.0
    assert ke["thoi_luong_nguon_ms"] == 30_000


# ══════════════════════════════════════════════════════════════════════════════
#  C. Ban phoi
# ══════════════════════════════════════════════════════════════════════════════

def test_amix_luon_normalize_KHONG():
    """⛔ Mac dinh cua `amix` **chia trung binh** theo so dau vao, tuc them mot
    doan tieng lam nho ca ban nen."""
    bt = am_master.bieu_thuc_lo(3, [0, 1000, 2000], [1.0, 1.0, 1.0])
    assert "normalize=0" in bt
    assert "normalize=1" not in bt


def test_moi_doan_duoc_TRE_dung_moc_cua_no():
    bt = am_master.bieu_thuc_lo(2, [0, 1500], [1.0, 1.0])
    assert "adelay=0|0" in bt
    assert "adelay=1500|1500" in bt


def test_he_so_co_gian_thanh_atempo_va_bi_CHAN():
    bt = am_master.bieu_thuc_lo(1, [0], [1.1])
    assert "atempo=1.100000" in bt
    # He so 1,0 thi KHONG duoc chen `atempo`: mot phep loc thua la mot lan doi
    # mau tin hieu khong can thiet.
    assert "atempo" not in am_master.bieu_thuc_lo(1, [0], [1.0])
    with pytest.raises(am_master.MasterError, match="co giãn"):
        am_master.bieu_thuc_lo(1, [0], [3.0])


def test_chia_lo_chan_so_dau_vao_moi_lan_chay():
    """🔴 Mot `filter_complex` voi 400 dau vao vuot tran 32.767 ky tu cua dong
    lenh Windows, va no bi cat **im lang**."""
    lo = am_master.chia_lo(100, moi_lo=24)
    assert lo[0] == (0, 24)
    assert lo[-1][1] == 100
    assert all(j - i <= 24 for i, j in lo)
    assert sum(j - i for i, j in lo) == 100


def test_chia_lo_doc_hang_so_luc_GOI():
    """Bai hoc pha 14: mot mac dinh gan luc dinh nghia ham la mot num van trong
    nhu da chinh ma khong chinh gi."""
    cu = am_master.DOAN_MOI_LO
    try:
        am_master.DOAN_MOI_LO = 5
        assert len(am_master.chia_lo(10)) == 2
    finally:
        am_master.DOAN_MOI_LO = cu


def test_chuan_am_luong_MOT_LAN_o_cuoi_khong_phai_tung_lo():
    """⛔ `loudnorm` doi muc cua ca dong tin hieu; chay tren tung manh roi cong
    lai cho ra mot ket qua khong ai du doan duoc.

    Chot bang AST: `loudnorm` chi duoc xuat hien trong `tron_cuoi`.
    """
    cay = ast.parse(Path(am_master.__file__).read_text(encoding="utf-8"))
    trong = {}
    for n in ast.walk(cay):
        if isinstance(n, ast.FunctionDef):
            src = ast.get_source_segment(
                Path(am_master.__file__).read_text(encoding="utf-8"), n) or ""
            trong[n.name] = "loudnorm" in src
    assert trong.get("tron_cuoi"), "`tron_cuoi` khong chuan am luong"
    assert not trong.get("tron_lo"), (
        "`tron_lo` chuan am luong — chay loudnorm tren tung lo roi cong lai cho "
        "ra mot muc khong du doan duoc")


def test_van_tay_master_doi_theo_MOI_thanh_phan():
    goc = dict(van_tay_nen="n", van_tay_ke_hoach="k", van_tay_ban_do="b",
               phien_ban_ffmpeg_="f")
    nen = am_master.van_tay_master(**goc)
    for khoa in goc:
        khac = {**goc, khoa: goc[khoa] + "x"}
        assert am_master.van_tay_master(**khac) != nen, f"{khoa} khong vao van tay"


# ══════════════════════════════════════════════════════════════════════════════
#  E. KHONG mot loi goi model nao
# ══════════════════════════════════════════════════════════════════════════════

def test_pha_16_KHONG_goi_model():
    """⛔ Pha 16 cam bang chu: "No AI calls". Chot bang AST tren ca hai module."""
    from apps.auto_scan_video import ban_do_thoi_gian

    for mod in (am_master, ban_do_thoi_gian):
        van = Path(mod.__file__).read_text(encoding="utf-8")
        cay = ast.parse(van)
        for n in ast.walk(cay):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                ten = getattr(n, "module", "") or ""
                ten += " ".join(a.name for a in n.names)
                assert "dieu_phoi" not in ten and ".ai" not in ten, (
                    f"{Path(mod.__file__).name} nhap duong goi model")
            if isinstance(n, ast.Call):
                goi = (n.func.attr if isinstance(n.func, ast.Attribute)
                       else getattr(n.func, "id", ""))
                assert goi not in ("goi_tinh_tien", "goi"), (
                    f"{Path(mod.__file__).name} goi model — pha 16 cam")


def test_NGAN_SACH_tinh_tren_truc_BAN_RA_chu_khong_tren_NGUON():
    """🔴 Lo hong ma kiem dot bien tim ra: phep kiem tren chi chot CHU KY.

    Chot chu ky (`tham so dau ten la gi`) khong ngan duoc nguoi goi truyen moc
    NGUON vao — va dot bien lam dung the thi bo test van xanh. Mot phep kiem do
    HINH DANG cua ham thay vi HANH VI cua no la mot phep kiem do sai thu.

    ⭐ Nen phep kiem nay dung mot mau thu ma hai cach tinh cho ra **hai vi tri
       khac nhau**, va chot dung con so cua cach dung:

         nguon:  seg0 [0;2], seg1 [10;12], cat [3;9)
         ban ra: seg0 [0;2], seg1 [4;6]

       Ngan sach cua seg0 o truc BAN RA la 4 giay; o truc NGUON la 10 giay. Voi
       mot doan tieng dai 5 giay, cach dung sinh ra 1,6 giay no troi va day seg1
       xuong 5,6 giay; cach sai khong thay no nao va dat seg1 o 4,8 giay.
    """
    muc = [{"ma": "seg_0000", "bat": 0.0, "ket": 2.0},
           {"ma": "seg_0001", "bat": 10.0, "ket": 12.0}]
    dai = {"seg_0000": 5.0, "seg_0001": 1.0}
    ban_do = bd.BanDoThoiGian.tu_khoang([(0, 3), (9, 20)], thoi_luong_nguon=20.0)

    ke = tg.lap_ke_hoach(muc, dai, tong_giay=20.0, ban_do=ban_do)
    theo_ma = {d["ma"]: d for d in ke["doan"]}

    assert theo_ma["seg_0000"]["ngan_sach_ms"] == 4000, (
        "ngan sach cua doan dau phai la 4 giay (truc ban ra), khong phai 10 giay "
        "(truc nguon)")
    assert theo_ma["seg_0000"]["troi_sau_ms"] > 0, (
        "5 giay tieng trong khe 4 giay ma khong sinh no troi — dang tinh tren "
        "ngan sach cua truc NGUON")
    assert theo_ma["seg_0001"]["dat_tai_ms"] == 5600, (
        "doan hai phai bi no troi day xuong 5,6 giay; 4,8 giay nghia la ngan "
        "sach dang doc moc NGUON")


def test_preset_GIU_HINH_khong_duoc_DOC_ban_bien_tap():
    """🔴 Lo hong thu hai. Cung hinh dang voi chot cua pha 12
    ("giu hinh khong doc y kien cua VLM"), va cung ly do.

    Preset giu hinh **sao chep** luong hinh: khong canh nao bi cat, nen ban do la
    dong nhat. Doc ban bien tap o day khong sai ve ket qua — nhung no tao mot
    **phu thuoc khong can co**, va mot phu thuoc khong can co la mot duong hong
    khong can co: mot run giu hinh se that bai neu `EDIT_PLAN` thieu artifact,
    du no khong can artifact do de lam gi.
    """
    from apps.auto_scan_video import features, giai_doan_thoi_gian, hop_dong_v4

    class RunGia:
        id, owner_id = "r1", "uA"
        settings = {"preset": hop_dong_v4.PRESET_GIU_HINH}

    def cam(*a, **k):
        raise AssertionError(
            "preset giu hinh da doc giai doan khac — no khong duoc phu thuoc "
            "vao ban bien tap")

    goc = features.giai_doan_theo_ten
    features.giai_doan_theo_ten = cam
    try:
        m = giai_doan_thoi_gian._ban_do(None, None, RunGia(), tong_giay=42.0)
    finally:
        features.giai_doan_theo_ten = goc

    assert m.thoi_luong_ra == 42.0
    assert m.so_cho_noi == 0
