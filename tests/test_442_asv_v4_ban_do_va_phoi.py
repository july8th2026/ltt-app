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
#  B. Ke hoach lap tren truc NGUON — GIAI DOAN 1 KHONG CAT GI (b4, 25/09)
# ══════════════════════════════════════════════════════════════════════════════

def _muc(n=3, buoc=10.0, dai=2.0):
    return [{"ma": f"seg_{i:04d}", "bat": i * buoc, "ket": i * buoc + dai}
            for i in range(n)]


def test_lap_ke_hoach_KHONG_CON_mot_tham_so_nao_de_nhanh_theo_preset():
    """🔴 Nghiem thu 1+2 cua b4: hai preset dung CHUNG duong voice.

    ⛔ Chot bang **CAU TRUC**, khong bang mot phep do tren hai lan chay: mot phep
       do chi noi rang hai lan chay hom nay trung nhau, con chu ky ham noi rang
       chung ⛔ khong the tach ra. `ban_do` bien mat ⇒ khong con cho nao cam mot
       quyet dinh cat vao giai doan 1.
    """
    import inspect

    tham = set(inspect.signature(tg.lap_ke_hoach).parameters)
    assert "ban_do" not in tham, (
        "`ban_do` da roi khoi giai doan 1 (b4 hai giai doan) — cat canh nam o "
        "giai doan 2, tren MP4 da xong")
    assert tham == {"muc", "thoi_luong_tieng", "tong_giay", "che_do", "nhom_gop"}


def test_ke_hoach_dat_doan_tren_truc_NGUON():
    """🔴 Menh de moi: giai doan 1 giao TOAN BO do dai goc, nen khong moc nao lui.

    Truoc b4, cat `[12; 18)` lam doan thu ba (bat o giay 20) lui ve giay 14. Nay
    khong phep cat nao chay o giai doan 1 ⇒ no o dung giay 20.
    """
    muc = _muc(3, buoc=10.0, dai=2.0)          # bat o 0, 10, 20
    dai = {m["ma"]: 1.5 for m in muc}
    ke = tg.lap_ke_hoach(muc, dai, tong_giay=30.0)
    theo_ma = {d["ma"]: d for d in ke["doan"]}
    assert theo_ma["seg_0000"]["dat_tai_ms"] == 0
    assert theo_ma["seg_0002"]["dat_tai_ms"] == 20_000
    assert ke["tong_ms"] == 30_000 == ke["thoi_luong_nguon_ms"]


def test_loi_doan_thuoc_phan_DA_CAT_KHONG_CON_TON_TAI():
    """⭐ Mot lop loi BIEN MAT, khong phai duoc kiem ky hon.

    `ThoiGianError('Doan {ma} thuoc phan da cat nhung van co tieng')` chi sinh ra
    duoc khi mot phep cat da chay TRUOC khi lap ke hoach tieng. O thu tu moi
    khong co phep cat nao o truoc, nen cau hoi khong con.

    🔑 Chot **su vang mat** bang mot phep chay THAT (`_muc` nam ca trong va ngoai
       moi khoang tuong tuong), ⛔ khong bang `grep` chuoi thong bao: mot chuoi
       bien khoi ma van co the con trong .po, va mot chuoi con trong ma van co
       the khong bao gio duoc nem.
    """
    muc = [{"ma": "seg_0000", "bat": 0.0, "ket": 2.0},
           {"ma": "seg_0001", "bat": 14.0, "ket": 16.0}]
    dai = {m["ma"]: 1.5 for m in muc}
    ke = tg.lap_ke_hoach(muc, dai, tong_giay=30.0)     # ⛔ khong nem
    assert {d["ma"] for d in ke["doan"]} == {"seg_0000", "seg_0001"}


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


def test_ke_hoach_KHONG_CON_khoa_ban_do__BO_chu_khong_de_RONG():
    """⛔ Mot khoa `"ban_do": {}` luon co mat se trong nhu mot ban do DA duoc tinh
    va ra ket qua trong — dung bay "hai trang thai gop thanh mot gia tri".

    ⭐ `thoi_luong_nguon_ms` o lai: no la ban khai cua loi hua "toan bo do dai
       goc", va `tong_ms` phai bang no o giai doan 1.
    """
    muc = _muc()
    ke = tg.lap_ke_hoach(muc, {m["ma"]: 1.5 for m in muc}, tong_giay=30.0)
    assert "ban_do" not in ke
    assert ke["thoi_luong_nguon_ms"] == 30_000 == ke["tong_ms"]
    assert ke["schema"] == tg.SCHEMA_KE_HOACH >= 2


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
    """⚠️ `:all=1` — bai hoc mang tu trinh render cu sang o pha 17.

    Thieu no thi `adelay` **chi tre kenh dau**, va tieng lech hai ben tai: hong
    theo kieu nghe thay duoc nhung rat kho goi ten.
    """
    bt = am_master.bieu_thuc_lo(2, [0, 1500], [1.0, 1.0])
    assert "adelay=0:all=1" in bt
    assert "adelay=1500:all=1" in bt


def test_moi_dau_vao_duoc_dat_DINH_DANG_truoc_khi_tron():
    """⭐ Bai hoc thu hai mang sang: tieng TTS va nhac nen khong cung tan so, va
    de `amix` tu chon la de no chon theo dau vao dau tien."""
    bt = am_master.bieu_thuc_lo(3, [0, 100, 200], [1.0, 1.0, 1.0])
    assert bt.count("aformat=") == 3


def test_chuan_am_luong_co_DUAL_MONO():
    """⚠️ Bai hoc da tra gia mot lan o pha 18 cua ban truoc: mot doan tieng MONO
    upmix len stereo bi `loudnorm` **do to hon thuc te 3 dB** neu thieu co nay.
    May sinh tieng tra ve mono, nen do la duong chay binh thuong.

    🔴 **Ban dau phep kiem nay quet VAN BAN cua tep, va no tu lam minh xanh.**

       Doan chu thich ngay tren dong ma co chua chuoi `dual_mono=true` de giai
       thich luat. Nen khi kiem dot bien go **chinh dong ma** di, phep kiem van
       tim thay chuoi do — trong chu thich — va bao xanh.

    ⭐ Day dung la cai bay ma `test_401._vi_pham` da hoc mot lan roi, chi la theo
       chieu NGUOC LAI: o do mot guard bao dong tren doan van giai thich no; o
       day mot phep kiem duoc **thoa man** boi doan van giai thich no. Ca hai deu
       den tu viec doc VAN BAN thay vi doc CAU TRUC.

    ⇒ Doc AST. Chu thich khong bao gio vao cay cu phap.
    """
    import ast
    from pathlib import Path as _P

    # ⚠️ Pha 22 tach bo loc chuan am ra `bieu_thuc_chuan_am` de kiem duoc ma
    #    khong phai chay ca mot lan tron. Nen phep kiem doi cho: doc KET QUA
    #    that cua ham do — manh hon doc AST, vi no la chinh chuoi di vao ffmpeg.
    bt = am_master.bieu_thuc_chuan_am("[a]", "[b]", tong_giay=3.0)
    assert "dual_mono=true" in bt, (
        "bo loc chuan am khong dat `dual_mono=true` — mot doan mono upmix len "
        f"stereo se bi do to hon thuc te 3 dB ({bt})")

    # ⛔ Va `tron_cuoi` phai THAT SU dung ham do. Neu khong, chuoi tren la mot
    #    ban khai dep dat canh mot lenh ffmpeg khac han — dung loai lech ma pha
    #    22 vua tim thay o trinh render.
    cay = ast.parse(_P(am_master.__file__).read_text(encoding="utf-8"))
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "tron_cuoi"]
    assert ham, "khong tim thay `tron_cuoi`"
    goi = {n.func.id for n in ast.walk(ham[0])
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "bieu_thuc_chuan_am" in goi, (
        "`tron_cuoi` khong con dung `bieu_thuc_chuan_am`")


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
    goc = dict(van_tay_nen="n", van_tay_ke_hoach="k",
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


def test_NGAN_SACH_tinh_tren_truc_NGUON__va_do_la_truc_DUY_NHAT():
    """🔴 Ban truoc chot rang ngan sach phai doc truc BAN RA (khac truc NGUON khi
    co canh bi cat). O b4 hai truc **la mot** o giai doan 1, nen menh de duoc
    phat bieu lai: ngan sach doc `moc_ms` DA DOI, va moc da doi = moc nguon.

    ⭐ `ngan_sach_doan` van nhan `moc_ms` chu khong nhan `muc` goc — chu ky do
       ⛔ khong duoc noi long, vi giai doan 2 (`ke_cat`) se lai can dung no tren
       mot truc khac.

           nguon: seg0 [0;2], seg1 [10;12] — khong cat gi
           ngan sach seg0 = 10 giay; doan tieng 5 giay ⇒ khong no troi
    """
    import inspect

    assert list(inspect.signature(tg.ngan_sach_doan).parameters)[0] == "moc_ms"

    muc = [{"ma": "seg_0000", "bat": 0.0, "ket": 2.0},
           {"ma": "seg_0001", "bat": 10.0, "ket": 12.0}]
    dai = {"seg_0000": 5.0, "seg_0001": 1.0}
    ke = tg.lap_ke_hoach(muc, dai, tong_giay=20.0)
    theo_ma = {d["ma"]: d for d in ke["doan"]}
    assert theo_ma["seg_0000"]["ngan_sach_ms"] == 10_000
    assert theo_ma["seg_0000"]["troi_sau_ms"] == 0, (
        "5 giay tieng trong mot khe 10 giay ⛔ khong duoc sinh no troi nao")
    assert theo_ma["seg_0001"]["dat_tai_ms"] == 10_000


def test_KHONG_preset_NAO_doc_ban_bien_tap_o_timing_align():
    """🔴 Chot cu manh hon: truoc b4 chi preset GIU HINH khong duoc doc ban bien
    tap; nay **khong preset nao** doc no o `timing_align`.

    Vi sao dieu do quan trong: mot phu thuoc khong can co la mot duong hong
    khong can co. Truoc b4, mot run `smart_localize` that bai neu `EDIT_PLAN`
    thieu artifact — ke ca khi loi thoai da duoc sinh xong. Nay `_ban_do` khong
    ton tai, nen duong do khong ton tai.

    ⛔ Chot bang AST chu khong bang mot lan chay: mot lan chay chi chung minh
       rang HOM NAY khong ai doc; cay cu phap chung minh rang ⛔ khong co dong
       nao de doc.
    """
    import ast
    from pathlib import Path as _P

    from apps.auto_scan_video import giai_doan_thoi_gian

    assert not hasattr(giai_doan_thoi_gian, "_ban_do"), (
        "`_ban_do` da bi xoa o b4 — cat canh khong con o giai doan 1")

    cay = ast.parse(_P(giai_doan_thoi_gian.__file__).read_text(encoding="utf-8"))
    doc = {n.attr for n in ast.walk(cay)
           if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
           and n.value.id == "pipeline"}
    assert "EDIT_PLAN" not in doc, sorted(doc)
    assert "ban_bien_tap" not in {
        a.name.split(".")[-1] for n in ast.walk(cay)
        if isinstance(n, ast.ImportFrom) for a in n.names}
