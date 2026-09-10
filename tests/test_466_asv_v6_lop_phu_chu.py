"""V6 pha 11 — LOP PHU CHU: bon luat, mot ranh gioi, va cau hoi "co ai di khong".

## Vi sao bo kiem nay khong giong bo kiem cua `vung_che`

Hinh hoc thi giong — cung bon luat, va do la co y: mot bo luat thu hai la mot bo
se lech. Cai KHAC nam o hai cho, va ca hai deu la cho da tra gia:

**1. Ranh gioi voi `subtitle_burn` phai la CO HOC.**
`CAM_TRONG_MVP` cam `subtitle_burn` vi `apps/autosubvideo` so huu no, va
`V6_OPERATING_CONTRACT` noi lai cau ay. Nhung ca hai dung **cung mot bo loc**
(`drawtext`). Mot giao uoc ("dung dung lop phu de lam phu de") se bi vi pham
boi chinh nguoi viet no — kho nay da ghi dieu do thanh luat sau khi mot phien
viet §4.9 roi vi pham no o luot ke. Nen ranh gioi o day la hai con so va mot
phep tu choi:

    · `chu` la MOT dong  — ky tu dieu khien bi TU CHOI, khong bi loc bo
    · toi da `SO_LOP_PHU_TOI_DA` lop

**2. Cach truyen chu la mot PHEP DO, khong phai mot gu.**
Do tren may nay, 7 chuoi thu:

    text= da thoat tung ky tu   hong 3/7   (dau tieng Viet, `:`, `\\`)
    textfile=                   hong 0/7

Ba cai hong la ba TANG khac nhau — bo tach tham so cua filter, bo thoat, va
bang ma doi so dong lenh tren Windows. Mot bang thoat ky tu phai dung ca ba, va
no chi "dung" toi chuoi thu tiep theo. Nen §3 chot **cach truyen**, khong chot
noi dung chuoi da thoat.

## Va cau hoi cuoi cung, §6

Kho nay co mot hinh dang loi da duoc dat ten: *"nang luc co, khong ai di tren
duong"* — moi tang dung, moi phep kiem xanh, va khong lan chay nao goi toi.
`vung_che` da song hai phien ban voi `tu_giay`/`den_giay` **duoc nhan, duoc
kiem, duoc luu** va khong dong ma nao doc.

⇒ §6 khong hoi "co ham do khong". No chan `_chay` va doc **dong lenh ffmpeg
  that su duoc dung**.
"""
from __future__ import annotations

import json
import os

import pytest

from apps.auto_scan_video import ban_dung, che_do_render as cdr, hop_dong_v4
from apps.auto_scan_video import ket_xuat, lop_phu as lp
from tests import rao_chan_nang

# ⚠️ Nhap MODULE roi lay THUOC TINH, khong `from ... import moi_truong`. Dang
#    nhap truc tiep tao mot ten thu hai trong khong gian ten cua tep nay va
#    `ruff` bao F811 khi mot fixture cung ten da co. Khuon nay do `test_455`
#    ghi lai va `test_461` dung lai.
from tests import test_423_asv_giao_dien as _gd
from tests import test_447_asv_v4_giao_dien_san_pham as _sp

moi_truong = _gd.moi_truong
_nop = _sp._nop
_settings = _sp._settings


def _lop(**thay):
    goc = {"chu": "Dang ky kenh", "x": 0.1, "y": 0.8, "co_chu": 0.06,
           "mau": "trang", "vien": True}
    goc.update(thay)
    return goc


KHOANG = [(0.0, 10.0), (20.0, 30.0)]


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Bon luat hinh hoc — CUNG bo luat voi `vung_che`, khong phai ban thu hai
# ══════════════════════════════════════════════════════════════════════════════

def test_toa_do_la_PHAN_SO_khong_phai_pixel():
    """L1. Mot con so > 1 la mot con so tinh bang pixel — va no bi TU CHOI."""
    with pytest.raises(lp.LopPhuLoi):
        lp.chuan_hoa_mot(_lop(x=120))


@pytest.mark.parametrize("xau", ["a", None, "", float("nan"), float("inf")])
def test_gia_tri_khong_doc_duoc_thi_TU_CHOI(xau):
    """L2. ⛔ `float('nan')` doc duoc va MOI phep so sanh voi no deu False, nen
    no lot qua `0 <= x <= 1` neu khong chan rieng."""
    with pytest.raises(lp.LopPhuLoi):
        lp.chuan_hoa_mot(_lop(x=xau))


def test_co_chu_ngoai_khoang_thi_TU_CHOI():
    for co in (0.001, 0.9):
        with pytest.raises(lp.LopPhuLoi):
            lp.chuan_hoa_mot(_lop(co_chu=co))


def test_mau_la_TAP_DONG():
    """⛔ Khong nhan chuoi tu do. Mot ten mau di thang vao bieu thuc filter la
    mot cho tiem chuoi, va `#RRGGBB` cua khach thi khong ai kiem."""
    with pytest.raises(lp.LopPhuLoi):
        lp.chuan_hoa_mot(_lop(mau="red"))
    with pytest.raises(lp.LopPhuLoi):
        lp.chuan_hoa_mot(_lop(mau="white@0.5:x=0"))
    for m in lp.MAU:
        assert lp.chuan_hoa_mot(_lop(mau=m))["mau"] == m


def test_khong_khai_gio_thi_KHONG_co_khoa_gio():
    """L4 (nua ky thuat): vang mat va `0` la HAI y dinh khac nhau. Ghi `0` vao
    `tu_giay` la "tu dau video"; vang mat la "ca video"."""
    ra = lp.chuan_hoa_mot(_lop())
    assert "tu_giay" not in ra and "den_giay" not in ra


def test_gio_nguoc_thi_TU_CHOI_khong_dao_lai():
    with pytest.raises(lp.LopPhuLoi):
        lp.chuan_hoa_mot(_lop(tu_giay=9.0, den_giay=2.0))


def test_gio_am_thi_TU_CHOI():
    with pytest.raises(lp.LopPhuLoi):
        lp.chuan_hoa_mot(_lop(tu_giay=-1.0))


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Ranh gioi voi `subtitle_burn` — CO HOC, khong phai loi hua
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("xau", ["dong mot\ndong hai", "a\tb", "a\rb", "a\x00b"])
def test_ky_tu_dieu_khien_bi_TU_CHOI_khong_bi_LOC_BO(xau):
    """🔑 Bai quan trong nhat cua §2, va hai menh de trong mot.

    ⛔ **Tu choi**, khong loc bo: mot chuoi bi loc am tham la mot chuoi khach
       khong go, va ho chi thay no tren ban da render.

    ⭐ Va `\\n` nam trong danh sach ay chinh la ranh gioi voi `subtitle_burn`:
       mot lop phu khong the mang hai dong, nen no khong the mang mot ban phu
       de.
    """
    with pytest.raises(lp.LopPhuLoi):
        lp.chuan_hoa_mot(_lop(chu=xau))


def test_qua_SO_LOP_PHU_TOI_DA_thi_TU_CHOI():
    ds = [_lop(chu=f"dong {i}") for i in range(lp.SO_LOP_PHU_TOI_DA + 1)]
    with pytest.raises(lp.LopPhuLoi):
        lp.chuan_hoa(ds)
    assert len(lp.chuan_hoa(ds[:-1])) == lp.SO_LOP_PHU_TOI_DA


def test_tran_do_dai_mot_dong():
    with pytest.raises(lp.LopPhuLoi):
        lp.chuan_hoa_mot(_lop(chu="x" * (lp.CHU_TOI_DA + 1)))


def test_chu_rong_thi_TU_CHOI():
    for x in ("", "   "):
        with pytest.raises(lp.LopPhuLoi):
            lp.chuan_hoa_mot(_lop(chu=x))


def test_thong_bao_tu_choi_CHI_DUONG_sang_cong_cu_phu_de():
    """⭐ Mot cau tu choi tot noi ca *"khong duoc"* lan *"the thi dung gi"*. Neu
    khong, khach se tim cach lach — vd nhoi ba lop lam ba dong phu de."""
    with pytest.raises(lp.LopPhuLoi) as e:
        lp.chuan_hoa_mot(_lop(chu="a\nb"))
    assert "phụ đề" in str(e.value)


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Chuoi bo loc — chot CACH TRUYEN, vi cach truyen la thu da do
# ══════════════════════════════════════════════════════════════════════════════

def _duong_chu(tmp_path, ds):
    return lp.viet_tep_chu(ds, tmp_path)


def test_dung_textfile_KHONG_dung_text(tmp_path):
    r"""🔴 Do duoc: `text=` hong 3/7 chuoi thu, `textfile=` hong 0/7.

    Ba cai hong la ba TANG: dau `:` (bo tach tham so), dau `\` (bo thoat), va
    bang ma doi so dong lenh tren Windows. Chot o day de khong ai "don gian
    hoa" no ve `text=` roi thay xanh — vi bo kiem se chi thu chuoi ASCII.
    """
    ds = lp.chuan_hoa([_lop()])
    loc = cdr.loc_cat_noi(KHOANG, lop_phu=ds,
                          duong_chu=_duong_chu(tmp_path, ds), cao_khung=360)
    assert "textfile=" in loc
    assert "drawtext=" in loc
    assert ":text=" not in loc


def test_expansion_none_luon_co_mat(tmp_path):
    """⛔ Khong co no thi `%` va `{...}` trong chu cua khach duoc `drawtext` doc
    nhu ma dinh dang — mot dong `%{pts}` se in ra dong ho."""
    ds = lp.chuan_hoa([_lop()])
    loc = cdr.loc_cat_noi(KHOANG, lop_phu=ds,
                          duong_chu=_duong_chu(tmp_path, ds), cao_khung=360)
    assert "expansion=none" in loc


def test_chu_KHONG_bao_gio_nam_trong_chuoi_loc(tmp_path):
    """Doi chung cho bai tren, va no manh hon: du chu co ky tu hiem toi dau,
    chuoi loc cung khong chua no."""
    ds = lp.chuan_hoa([_lop(chu="Gio: 12:30 - 50%")])
    loc = cdr.loc_cat_noi(KHOANG, lop_phu=ds,
                          duong_chu=_duong_chu(tmp_path, ds), cao_khung=360)
    assert "12:30" not in loc
    assert "50%" not in loc


def test_tep_chu_la_UTF8_khong_BOM(tmp_path):
    """⛔ Ba byte BOM se hien ra thanh mot ky tu rac o dau dong chu."""
    ds = lp.chuan_hoa([_lop(chu="Đăng ký")])
    duong = lp.viet_tep_chu(ds, tmp_path)
    b = open(duong[0], "rb").read()
    assert not b.startswith(b"\xef\xbb\xbf")
    assert b.decode("utf-8") == ds[0]["chu"]


def test_khong_dat_gio_thi_KHONG_co_enable(tmp_path):
    ds = lp.chuan_hoa([_lop()])
    loc = cdr.loc_cat_noi(KHOANG, lop_phu=ds,
                          duong_chu=_duong_chu(tmp_path, ds), cao_khung=360)
    assert "enable=" not in loc


def test_dat_gio_thi_enable_dung_khoang_cua_BAN_RA(tmp_path):
    r"""🔑 Moc khach nhap la moc NGUON; bo loc chay tren ban RA. Voi
    `KHOANG = [(0,10), (20,30)]`, giay 22 cua nguon la giay 12 cua ban ra.

    ⚠️ Va dau phay trong `between()` phai duoc thoat: trong cu phap filter `,`
       ngan hai BO LOC.
    """
    ds = lp.chuan_hoa([_lop(tu_giay=22.0, den_giay=24.0)])
    loc = cdr.loc_cat_noi(KHOANG, lop_phu=ds,
                          duong_chu=_duong_chu(tmp_path, ds), cao_khung=360)
    assert "enable=between(t" in loc
    assert "12.0000" in loc and "14.0000" in loc
    assert chr(92) + "," in loc


def test_lop_phu_dat_gio_rot_vao_doan_da_CAT_thi_NEM(tmp_path):
    """⛔ Bo qua im lang la giao mot video khong co dong chu khach da go, va ho
    chi biet khi xem tep da nhan."""
    ds = lp.chuan_hoa([_lop(tu_giay=12.0, den_giay=15.0)])   # nam trong (10,20)
    with pytest.raises(cdr.CheDoError) as e:
        cdr.loc_cat_noi(KHOANG, lop_phu=ds,
                        duong_chu=_duong_chu(tmp_path, ds), cao_khung=360)
    # ⭐ Cau loi phai noi ve LOP PHU, khong phai ve vung che. Hai tinh nang, hai
    #    cau — mot cau chung chung buoc khach doan minh vua lam gi sai.
    assert "lớp phủ" in str(e.value)


def test_vien_tinh_ra_PIXEL_va_TI_LE_voi_do_phan_giai():
    """🔴 `borderw` KHONG nhan bieu thuc (do duoc: `borderw=H*0.004` ->
    *"Invalid argument"*), khac `fontsize`. Nen do day phai tinh truoc — va no
    phai TI LE, khong phai mot hang so."""
    l = lp.chuan_hoa_mot(_lop(co_chu=0.06))
    assert lp.vien_px(l, 360) < lp.vien_px(l, 2160)
    assert lp.vien_px(l, 360) >= 1
    with pytest.raises(lp.LopPhuLoi):
        lp.vien_px(l, 0)


def test_chu_ve_SAU_vung_che(tmp_path):
    """⚠️ Nguoc lai thi mot dong chu roi trung o che se bi chinh o do lam mo —
    va khach ve chu de nguoi ta doc duoc no."""
    ds = lp.chuan_hoa([_lop()])
    vung = [{"loai": "lam_mo", "x0": 0.1, "y0": 0.1, "x1": 0.4, "y1": 0.3}]
    loc = cdr.loc_cat_noi(KHOANG, vung, lop_phu=ds,
                          duong_chu=_duong_chu(tmp_path, ds), cao_khung=360)
    assert loc.index("boxblur") < loc.index("drawtext")


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Van tay — L4, va mot lo cache co that
# ══════════════════════════════════════════════════════════════════════════════

def _vt(**thay):
    return cdr.van_tay_che_do(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
                              khoang=KHOANG, **thay)


def test_doi_CHU_thi_doi_van_tay():
    """⛔ Doi mot dong chu ma van tay khong doi la giao lai ban render cu — tuc
    khach sua chinh ta xong van thay loi chinh ta cu."""
    a = _vt(lop_phu=lp.chuan_hoa([_lop(chu="Dang ky kenh")]))
    b = _vt(lop_phu=lp.chuan_hoa([_lop(chu="Dang ky kenh nhe")]))
    assert a != b


@pytest.mark.parametrize("thay", [{"x": 0.5}, {"y": 0.5}, {"co_chu": 0.12},
                                  {"mau": "vang"}, {"vien": False},
                                  {"do_mo": 0.5}, {"tu_giay": 1.0}])
def test_doi_BAT_KY_tham_so_nao_cung_doi_van_tay(thay):
    a = _vt(lop_phu=lp.chuan_hoa([_lop()]))
    b = _vt(lop_phu=lp.chuan_hoa([_lop(**thay)]))
    assert a != b, f"doi {thay} ma van tay khong doi"


def test_khong_co_lop_phu_thi_van_tay_GIONG_ban_khong_khai():
    """⭐ Doi chung cho ca §4: neu them mot khoa rong cung doi van tay thi moi
    lan chay cu deu mat cache ma khong vi ly do gi."""
    assert _vt() == _vt(lop_phu=[])


def test_PHIEN_BAN_CHE_DO_da_len_bac():
    assert cdr.PHIEN_BAN_CHE_DO >= 4


def test_PHIEN_BAN_CHE_DO_CO_vao_van_tay_cua_tep_ra():
    """🔴 **Lo nay co that va no khong lien quan toi lop phu.**

    `giai_doan_ket_xuat._van_tay` hua *"doi cach dung lenh deu doi no"* nhung no
    bam ban dung + `PHIEN_BAN_KET_XUAT` + ffmpeg. Chuoi loc thi do
    `che_do_render.loc_cat_noi` dung: doi cach lam mo, doi thu tu chang, them
    mot bo loc — cung ban dung, cung van tay, khac tep ra.

    ⛔ Va no khong bao gio no; no hien ra nhu mot lan chay lai "nhanh bat
       thuong" tra ve dung tep cu.
    """
    import ast
    import inspect

    from apps.auto_scan_video import giai_doan_ket_xuat as gdk

    cay = ast.parse(inspect.getsource(gdk._van_tay))
    ten = {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}
    assert "PHIEN_BAN_CHE_DO" in ten


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Ba tang cuong che "khong the co o preset giu hinh"
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_dung_TU_CHOI_lop_phu_o_duong_sao_chep():
    """Tang 2. Cung rang buoc VAT LY voi vung che: `drawtext` la mot bo loc, bo
    loc doi hoi giai ma, `-c:v copy` khong giai ma khung nao."""
    ban = {"schema": ban_dung.SCHEMA_BAN_DUNG,
           "hinh": {"khoa": "v", "che_do": ban_dung.CHE_DO_HINH,
                    "cach_render": cdr.SAO_CHEP,
                    "lop_phu": [_lop()], "cao_khung": 360},
           "tieng": {"nen": {"khoa": "n"}, "master": {"khoa": "m"}, "lop": []}}
    with pytest.raises(ban_dung.BanDungError) as e:
        ban_dung.kiem(ban)
    assert "Lớp phủ" in str(e.value)


def test_ban_dung_TU_CHOI_lop_phu_khong_co_cao_khung():
    """🔴 Thieu no thi lan chay hong o TRINH RENDER — sau khi da chiem mot suat
    ffmpeg va tai vai tram MB."""
    ban = {"schema": ban_dung.SCHEMA_BAN_DUNG,
           "hinh": {"khoa": "v", "che_do": ban_dung.CHE_DO_HINH,
                    "cach_render": cdr.CAT_MA_HOA_LAI,
                    "lop_phu": [_lop()], "cao_khung": 0},
           "tieng": {"nen": {"khoa": "n"}, "master": {"khoa": "m"}, "lop": []}}
    with pytest.raises(ban_dung.BanDungError) as e:
        ban_dung.kiem(ban)
    assert "chiều cao khung hình" in str(e.value)


def test_hai_cau_TU_CHOI_khac_nhau_cho_vung_va_cho_lop_phu():
    """⛔ Khong gop hai chot lam mot dieu kien `or`. Khach ve mot O CHE va khach
    go mot DONG CHU la hai viec, va mot cau chung chung buoc ho phai doan."""
    def _ban(**hinh):
        h = {"khoa": "v", "che_do": ban_dung.CHE_DO_HINH,
             "cach_render": cdr.SAO_CHEP}
        h.update(hinh)
        return {"schema": ban_dung.SCHEMA_BAN_DUNG, "hinh": h,
                "tieng": {"nen": {"khoa": "n"}, "master": {"khoa": "m"},
                          "lop": []}}

    with pytest.raises(ban_dung.BanDungError) as a:
        ban_dung.kiem(_ban(vung=[{"loai": "lam_mo"}]))
    with pytest.raises(ban_dung.BanDungError) as b:
        ban_dung.kiem(_ban(lop_phu=[_lop()], cao_khung=360))
    assert str(a.value) != str(b.value)


def test_giao_dien_khoa_cong_cu_theo_preset():
    """Tang 1. Khoi `data-preset-can` — cung khuon voi vung che va cat."""
    from pathlib import Path

    goc = Path(__file__).resolve().parent.parent
    van = (goc / "apps/auto_scan_video/templates/asv_trang_chinh.html"
           ).read_text(encoding="utf-8")
    i = van.index('id="asv-nhom-lop-phu"')
    khoi = van[i - 200:i + 400]
    assert "data-preset-can" in khoi
    assert 'name="lop_phu"' in van


def test_hang_o_dieu_khien_co_SAN_chieu_rong_tren_man_hep():
    """🔴 **Loi nay chi trinh duyet thay, va no KHONG tran ngang.**

    Do that o 375px truoc khi sua: hang co BON o dieu khien (`flex:1 1 90px`)
    chia nhau 234px, ra **40px moi cai**. Mot o `<input type=number>` 40px khong
    hien noi `100`; mot `<select>` 40px khong hien noi mot ten mau.

    ⛔ `document.scrollWidth == clientWidth` — khong tran ngang — nen mot chot
       "khong duoc tran ngang" **im lang** o dung ca nay. Hang cua vung che thi
       khong dinh, vi no chi co HAI o.

    ⇒ Hai nua, va thieu mot nua thi luat khong ton tai:
        · JS phai gan lop `asv-lp-o` (danh dau "hang nay bon o")
        · CSS phai cho hang do XUONG DONG kem mot san chieu rong

    Sau khi sua, do lai o 375px: bon o thanh 113px, xep 2x2, khong tran ngang.
    """
    from pathlib import Path

    goc = Path(__file__).resolve().parent.parent
    js = (goc / "server/static/asv.js").read_text(encoding="utf-8")
    assert "asv-vung-gio-o asv-lp-o" in js, "JS khong gan lop danh dau"

    css = (goc / "server/static/ltt.css").read_text(encoding="utf-8")
    assert ".asv-lp-o{flex-wrap:wrap}" in css, "hang khong duoc phep xuong dong"
    assert ".asv-lp-o>.asv-vung-gio{" in css and "min-width:100px" in css, (
        "thieu san chieu rong — cac o van co lai duoc toi 40px")


def test_giao_dien_KHONG_dung_o_nhieu_dong():
    """⛔ Mot `<textarea>` trong khoi lop phu la mot loi moi dan phu de vao. Ranh
    gioi phai la CO HOC o CA HAI dau, khong chi o may chu."""
    from pathlib import Path

    goc = Path(__file__).resolve().parent.parent
    van = (goc / "apps/auto_scan_video/templates/asv_trang_chinh.html"
           ).read_text(encoding="utf-8")
    i = van.index('id="asv-nhom-lop-phu"')
    j = van.index("</div>", van.index('id="asv-lop-phu"', i))
    assert "<textarea" not in van[i:j]

    js = (goc / "server/static/asv.js").read_text(encoding="utf-8")
    k = js.index("4c. Lop phu chu")
    l = js.index("5. Tai len BEN VUNG", k)
    assert 'createElement("textarea")' not in js[k:l]


# ══════════════════════════════════════════════════════════════════════════════
#  §6  CO AI DANG DI TREN DUONG KHONG
# ══════════════════════════════════════════════════════════════════════════════

def test_dung_lenh_THUC_SU_mang_drawtext_ra_ffmpeg(tmp_path):
    """🔑 Khong doc AST, doc **dong lenh ffmpeg that su duoc dung**.

    ⛔ Mot phep kiem AST hoi *"co dong ma do khong"*; cau can hoi la *"dong ma
       do co CHAY khong"*. `test_465` da tra gia cho bai hoc ay: mot ban tiem
       `None if True else _do_am_luong(...)` giu nut goi trong cay AST va ca 12
       bai van xanh.
    """
    ds = lp.chuan_hoa([_lop(chu="Dang ky")])
    duong = lp.viet_tep_chu(ds, tmp_path)
    ban = {"schema": ban_dung.SCHEMA_BAN_DUNG,
           "preset": hop_dong_v4.PRESET_CAT_THONG_MINH,
           "hinh": {"khoa": "v", "che_do": ban_dung.CHE_DO_HINH,
                    "cach_render": cdr.CAT_MA_HOA_LAI, "bo_ma_hoa": "libx264",
                    "khoang_giu": [[0.0, 10.0]], "vung": [],
                    "lop_phu": ds, "cao_khung": 720},
           "tieng": {"master": {"khoa": "m"}, "nen": {"khoa": "n"}, "lop": [],
                     "tan_so": 48000, "so_kenh": 2},
           "ra": {"container": "mp4", "codec_tieng": "aac",
                  "bitrate_tieng": "192k", "faststart": True,
                  "thoi_luong_giay": 10.0},
           "cong_cu": {"ffmpeg": "n7.0"}}
    cmd = ket_xuat.dung_lenh(ban, ffmpeg_bin="ffmpeg", duong_video="v.mp4",
                             duong_master="m.wav", duong_lop=[],
                             duong_ra="r.mp4", duong_chu=duong)
    loc = cmd[cmd.index("-filter_complex") + 1]
    assert "drawtext=" in loc
    assert "textfile=" in loc
    assert "borderw=" in loc


def test_thieu_tep_chu_thi_NEM_chu_khong_bo_qua(tmp_path):
    """⛔ Lech so luong hay lech thu tu deu KHONG lam ffmpeg hong — chung chi lam
    ban ra sai: dong chu thu nhat mang noi dung cua dong thu hai."""
    ds = lp.chuan_hoa([_lop(), _lop(chu="dong hai")])
    ban = {"schema": ban_dung.SCHEMA_BAN_DUNG,
           "preset": hop_dong_v4.PRESET_CAT_THONG_MINH,
           "hinh": {"khoa": "v", "che_do": ban_dung.CHE_DO_HINH,
                    "cach_render": cdr.CAT_MA_HOA_LAI, "bo_ma_hoa": "libx264",
                    "khoang_giu": [[0.0, 10.0]], "vung": [],
                    "lop_phu": ds, "cao_khung": 720},
           "tieng": {"master": {"khoa": "m"}, "nen": {"khoa": "n"}, "lop": [],
                     "tan_so": 48000, "so_kenh": 2},
           "ra": {"container": "mp4", "codec_tieng": "aac",
                  "bitrate_tieng": "192k", "faststart": True,
                  "thoi_luong_giay": 10.0},
           "cong_cu": {"ffmpeg": "n7.0"}}
    with pytest.raises(ket_xuat.KetXuatError):
        ket_xuat.dung_lenh(ban, ffmpeg_bin="ffmpeg", duong_video="v.mp4",
                           duong_master="m.wav", duong_lop=[],
                           duong_ra="r.mp4", duong_chu=[str(tmp_path / "a.txt")])


def test_giai_doan_ban_dung_CHUYEN_lop_phu_tu_cai_dat():
    """Nua con lai cua cau hoi: co ai **dat** `lop_phu` vao ban dung khong.

    ⚠️ Doc AST o day la du, va chi du, vi bai tren da chot dau kia cua duong:
       ban dung CO `lop_phu` thi dong lenh CO `drawtext`. Hai bai cong lai phu
       het doan duong; mot minh bai nay thi khong.
    """
    import ast
    import inspect

    from apps.auto_scan_video import giai_doan_ban_dung as gdb

    cay = ast.parse(inspect.getsource(gdb.chay))
    kw = {k.arg for n in ast.walk(cay) if isinstance(n, ast.Call)
          for k in n.keywords if k.arg}
    assert "lop_phu" in kw and "cao_khung" in kw


def test_giai_doan_ket_xuat_GHI_tep_chu_truoc_khi_goi():
    import ast
    import inspect

    from apps.auto_scan_video import giai_doan_ket_xuat as gdk

    van = inspect.getsource(gdk)
    assert "viet_tep_chu" in van
    cay = ast.parse(van)
    goi = {n.func.attr for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "viet_tep_chu" in goi


# ══════════════════════════════════════════════════════════════════════════════
#  §7  Hop dong san pham — mot muc, dung MOT trang thai
# ══════════════════════════════════════════════════════════════════════════════

def test_text_overlay_DA_duoc_khai_la_dang_phuc_vu():
    """⛔ Mot muc chi VANG MAT thi "chua khai" va "bi cam" trong giong het nhau.
    `FEATURE_PARITY_MATRIX.md` xep no la `DEFER` tu V5 ma khong dong ma nao noi
    dieu do — tuc mot quyet dinh chi ton tai trong mot tep `.md`."""
    assert "text_overlay" in hop_dong_v4.NANG_LUC_DOI_DIEM_ANH
    assert "mask_region" in hop_dong_v4.NANG_LUC_DOI_DIEM_ANH


def test_logo_anh_DA_duoc_khai_la_HOAN_lai():
    """⭐ Khac `CAM_TRONG_MVP`: logo **se mo**, no dang cho duong nhap anh (pha
    08). Viet ra de mot pha sau khong phai doan."""
    assert "logo_image" in hop_dong_v4.HAU_MVP


def test_subtitle_burn_VAN_bi_cam():
    """🔑 Doi chung cho ca pha 11: lop phu chu KHONG duoc lam `subtitle_burn`
    doi ten. `apps/autosubvideo` van so huu viec do."""
    assert "subtitle_burn" in hop_dong_v4.CAM_TRONG_MVP
    assert "subtitle_burn" not in hop_dong_v4.NANG_LUC_DOI_DIEM_ANH


def test_mot_nang_luc_KHONG_duoc_o_hai_bang():
    """Chot noi tai cua hop dong phai NO khi mot ma vua dang phuc vu vua nam
    trong `HAU_MVP` — ma thi dang chay, tai lieu thi noi "chua lam"."""
    cu = hop_dong_v4.NANG_LUC_DOI_DIEM_ANH
    try:
        hop_dong_v4.NANG_LUC_DOI_DIEM_ANH = cu + ("zoom",)   # co trong CAM
        with pytest.raises(ValueError, match="vua dang phuc vu"):
            hop_dong_v4._kiem_tra_hop_dong()
    finally:
        hop_dong_v4.NANG_LUC_DOI_DIEM_ANH = cu
    hop_dong_v4._kiem_tra_hop_dong()      # ban that phai xanh


# ══════════════════════════════════════════════════════════════════════════════
#  §8  ENGINE THAT — nang, sau rao chan
# ══════════════════════════════════════════════════════════════════════════════

@rao_chan_nang.NANG
@pytest.mark.skipif(os.environ.get(rao_chan_nang.BIEN) != "1",
                    reason=rao_chan_nang.LY_DO)
def test_engine_ve_chu_DUNG_LUC_va_khong_dong_gi_ngoai_cua_so(tmp_path):
    """🔑 Bang chung ENGINE, va **ban do dau tien cua toi SAI**.

    Thiet ke: mot nguon 6 giay, mot lop phu dat gio `[2,0 ; 4,0)`; do PSNR ban
    CO lop phu voi ban KHONG, tai ba moc.

    ⛔ Luot dau ghi hai ban bang `libx264 -crf 12`:

           t=1,0s NGOAI cua so   PSNR = inf       <- trung khop
           t=5,0s NGOAI cua so   PSNR = 53,25 dB  <- KHAC, du bo loc khong ve gi

       Khac biet ay khong den tu bo loc ma tu **bo ma hoa**: cac khung 2-4s cua
       ban co lop phu chua chu, nen cac khung P sau do tham chieu mot lich su
       khac. Va su BAT DOI XUNG chi ra nguyen nhan — t=1,0s trung khop vi no la
       khung I dau chuoi, chua co lich su nao de lech.

    ⇒ FFV1 (khong mat mat). Khi do `inf` moi co nghia la "tung diem anh".

    ⭐ Duong cheo (t=3,0 so t=1,0 cua CUNG mot ban) de chac rang phep do PHAN
       BIET duoc — khong co no, ba con `inf` co the chi nghia la moi khung deu
       giong nhau.
    """
    import re
    import subprocess

    def chay(cmd):
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=300, errors="replace")

    cao = 360
    khoang = [(0.0, 6.0)]

    def render(ten, ds):
        duong = lp.viet_tep_chu(ds, tmp_path / "chu") if ds else []
        loc = cdr.loc_cat_noi(khoang, lop_phu=ds, duong_chu=duong,
                              cao_khung=cao)
        ra = tmp_path / f"{ten}.mkv"
        r = chay(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                  "-f", "lavfi", "-i",
                  f"testsrc2=size=640x{cao}:rate=25:duration=6",
                  "-filter_complex", loc, "-map", "[ra]", "-t", "6",
                  "-c:v", "ffv1", "-level", "3", str(ra)])
        assert r.returncode == 0, r.stderr[-1200:]
        return ra

    def khung(video, giay, ten):
        ra = tmp_path / f"{ten}.png"
        r = chay(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                  "-ss", f"{giay:.3f}", "-i", str(video), "-frames:v", "1",
                  str(ra)])
        assert r.returncode == 0 and ra.exists(), r.stderr[-600:]
        return ra

    def psnr(a, b):
        r = chay(["ffmpeg", "-hide_banner", "-i", str(a), "-i", str(b),
                  "-lavfi", "psnr", "-f", "null", "-"])
        m = re.search(r"average:(inf|[0-9.]+)", r.stderr or "")
        assert m, (r.stderr or "")[-800:]
        return float("inf") if m.group(1) == "inf" else float(m.group(1))

    ds = lp.chuan_hoa([_lop(chu="Đăng ký kênh: 50%",
                            x=0.08, y=0.80, co_chu=0.09, mau="vang",
                            tu_giay=2.0, den_giay=4.0)])
    co = render("co", ds)
    khong = render("khong", [])

    for giay in (1.0, 5.0):
        d = psnr(khung(co, giay, f"a{giay}"), khung(khong, giay, f"b{giay}"))
        assert d == float("inf"), (
            f"t={giay}s nam NGOAI cua so ma ban ra van khac ({d} dB)")

    trong = psnr(khung(co, 3.0, "a3"), khung(khong, 3.0, "b3"))
    assert trong < 60, f"t=3,0s nam TRONG cua so ma khong doi gi ({trong} dB)"

    cheo = psnr(khung(co, 3.0, "c3"), khung(co, 1.0, "c1"))
    assert cheo < 60, "duong cheo trung khop => phep do khong phan biet duoc gi"


# ══════════════════════════════════════════════════════════════════════════════
#  §9  HTTP that — tang thu nhat cua ba tang, va no o TRUOC cua tien
# ══════════════════════════════════════════════════════════════════════════════

def test_preset_giu_hinh_TU_CHOI_lop_phu(moi_truong, tmp_path):
    """⛔ Va tu choi **truoc khi giu credit**, khong phai o `ban_dung.kiem` sau
    chin giai doan. Mot lan chay bi chan o do la mot lan chay khach da tra."""
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_GIU_HINH,
             lop_phu=json.dumps([_lop()]))
    assert r.status_code == 400, "phai tra ve trang co loi, khong phai 303"
    assert "/run/" not in str(r.url), "khong duoc tao lan chay nao"
    assert "không thể vẽ chữ lên hình" in r.text


def test_preset_cat_NHAN_lop_phu_va_LUU_vao_settings(moi_truong, tmp_path):
    """⚠️ Neu bai nay xanh ma `test_giai_doan_ban_dung_CHUYEN_lop_phu` do thi ta
    dang o dung ca `vung_che` da mac: **luu duoc, khong thi hanh duoc**."""
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
             lop_phu=json.dumps([_lop(chu="Dang ky kenh")]))
    assert "/run/" in str(r.url), r.text[:400]
    run_id = str(r.url).rsplit("/run/", 1)[1].split("/")[0]
    ds = _settings(run_id)["lop_phu"]
    assert len(ds) == 1 and ds[0]["chu"] == "Dang ky kenh"


def test_KHONG_co_lop_phu_thi_settings_KHONG_mang_khoa(moi_truong, tmp_path):
    """L4 o tang HTTP: mot lan chay binh thuong khong duoc mang them mot truong
    ma khong lan nao dung toi."""
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH)
    run_id = str(r.url).rsplit("/run/", 1)[1].split("/")[0]
    assert "lop_phu" not in _settings(run_id)


def test_chu_NHIEU_DONG_bi_tu_choi_o_CUA_bang_cau_tieng_Viet(moi_truong,
                                                             tmp_path):
    """🔑 Ranh gioi voi `subtitle_burn` phai dung o **cua vao HTTP**, khong chi
    trong mot ham. Mot client tu viet khong chay JavaScript cua ta."""
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
             lop_phu=json.dumps([_lop(chu="dong mot\ndong hai")]))
    assert r.status_code == 400
    assert "/run/" not in str(r.url), "chu nhieu dong van tao duoc lan chay"
    assert "phụ đề" in r.text


def test_JSON_hong_bi_tu_choi_chu_khong_no_500(moi_truong, tmp_path):
    """⛔ `json.loads` nem `ValueError`, khong nem `LopPhuLoi`. Khong bat rieng
    thi mot chuoi rac tu client thanh mot loi 500 — tuc ta bao "may chu hong"
    cho mot yeu cau sai cua khach."""
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
             lop_phu="{khong-phai-json")
    assert r.status_code == 400
    assert "/run/" not in str(r.url)


def test_ban_ghi_van_tay_doc_duoc():
    """Chot nho: van tay la mot chuoi hex on dinh, khong phai mot dict lo ra."""
    vt = _vt(lop_phu=lp.chuan_hoa([_lop()]))
    assert isinstance(vt, str) and len(vt) == 32
    assert json.dumps({"vt": vt})
