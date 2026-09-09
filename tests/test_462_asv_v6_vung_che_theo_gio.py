"""V6 pha 12 — vung che theo GIO: hai khiem khuyet, va vi sao chung phai di doi.

## Hai lo hong V5 de lai, va cai thu hai bi cai thu nhat CHE

`vung_che.chuan_hoa_mot` nhan, **kiem** va **giu** `tu_giay`/`den_giay` tu V5.
`ban_dung.dung` luu chung. Roi:

  V6-01  `che_do_render._loc_lam_mo` khong doc chung LAN NAO
         -> mot vung ke gio van bi lam mo suot ca video
  V6-02  `van_tay_che_do` khong bam chung
         -> hai cau hinh khac gio dung CHUNG mot van tay -> phuc vu nham tep

⛔ V6-02 khong bao gio no, vi V6-01 lam hai ket qua **trung nhau that**. Sua
   rieng V6-01 se **kich hoat** V6-02: tu luc gio co tac dung, hai lan chay khac
   gio cho hai video khac nhau ma van dung chung mot khoa.

⇒ Hai viec MOT luot, va `PHIEN_BAN_CHE_DO` len mot bac.

## Vi sao `test_456` xanh suot ma khong thay gi

Ba bai o do chot `tu_giay` **duoc giu qua chuan hoa**. Ca ba dung, ca ba xanh,
va khong bai nao hoi *"giu de lam gi"*. Do la hinh dang loi kho nay da dat ten:
**moi tang lam dung phan cua no, cai sai nam o khoang giua**.

⇒ Nen tep nay hoi bang **dau ra**, khong hoi bang gia tri duoc giu.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess

import pytest

from apps.auto_scan_video import che_do_render as cdr
from apps.auto_scan_video import vung_che
from apps.auto_scan_video.ban_do_thoi_gian import BanDoThoiGian
from tests import rao_chan_nang


def _hop(**them):
    ra = {"loai": "lam_mo", "y0": 0.60, "y1": 0.95, "x0": 0.10, "x1": 0.90}
    ra.update(them)
    return ra


#: Giu [5,15] va [30,40] cua mot nguon 60s -> ban ra dai 20s, mot cho noi o
#: moc 10s cua ban ra.
KHOANG = [(5.0, 15.0), (30.0, 40.0)]


# ══════════════════════════════════════════════════════════════════════════════
#  §1  `BanDoThoiGian.ra_khoang` — moc NGUON -> khoang tren BAN RA
# ══════════════════════════════════════════════════════════════════════════════

def _ban_do():
    return BanDoThoiGian(tuple(KHOANG), 60.0)


def test_khoang_nam_gon_trong_MOT_vung_giu():
    assert _ban_do().ra_khoang(10.0, 12.0) == [(5.0, 7.0)]


def test_khoang_bat_qua_cho_cat_thi_GOP_vi_ban_ra_lien_tuc():
    """⭐ `concat` noi khong ke ho, nen hai manh nguon hai ben mot cho cat tro
    thanh LIEN TUC tren ban ra. Gop lai bot mot bo loc ma khong doi mot khung
    hinh nao.

    Nguon [10,35] -> manh 1 cho src 10..15 = ra 5..10; manh 2 cho src 30..35 =
    ra 10..15. Hai khoang dinh nhau o 10 ⇒ mot khoang 5..15.
    """
    assert _ban_do().ra_khoang(10.0, 35.0) == [(5.0, 15.0)]


def test_khoang_nam_TRON_trong_phan_da_cat_thi_RONG():
    """Src 16..29 khong cham khoang giu nao — khong con cho nao de che."""
    assert _ban_do().ra_khoang(16.0, 29.0) == []


def test_MOT_khoang_nguon_lien_mach_luon_cho_TOI_DA_mot_khoang_ra():
    """🔑 Bai quan trong nhat cua §1 — va no khang dinh mot **dinh ly**, khong
    phai mot vi du.

    ⭐ Ban dau toi viet mot bai nguoc lai: *"hai manh roi nhau khong duoc ep
       thanh mot cap"*, va no DO. Doc lai ket qua thay ly do — va ly do ay dang
       hon ca bai kiem:

         mot khoang nguon LIEN MACH bat qua mot cho cat thi tat yeu phu **den
         het** vung giu truoc do va **tu dau** vung giu ke tiep (cho cat bat dau
         dung o cuoi vung truoc). Tren ban ra hai manh ay **dinh nhau**, luon
         luon. Nen chung gop lai — khong phai vi ta chon gop, ma vi khong co cho
         nao de ho.

    ⇒ Nhanh "nhieu khoang" trong `_bat_khi` la mot nhanh **khong the toi** voi
      mot vung che. Giu no vi `ra_khoang` la ham cua ban do chu khong rieng cua
      vung che; nhung ghi ro o day rang no khong the toi, de mot phien sau khong
      di tim mot ca thu de "kiem tra cho du".
    """
    import random

    rnd = random.Random(20260910)
    for _ in range(300):
        moc = sorted(rnd.sample(range(0, 200), 8))
        giu = tuple((float(moc[i]), float(moc[i + 1])) for i in range(0, 8, 2))
        bd = BanDoThoiGian(giu, 200.0)
        a, b = sorted(rnd.sample(range(0, 200), 2))
        ra = bd.ra_khoang(float(a), float(b))
        assert len(ra) <= 1, f"giu={giu} khoang=({a},{b}) -> {ra}"


def test_ra_khoang_KHONG_phai_hai_lan_goi_ra():
    """⛔ Vi sao khong dung `ra()` hai lan cho hai dau.

    `ra()` tra `None` cho moc nam trong phan bi cat. Voi khoang [16,29] thi CA
    HAI dau deu `None`, va mot cap `(None, None)` khong con noi gi — trong khi
    `ra_khoang` noi dung dieu can noi: **rong**.
    """
    bd = _ban_do()
    assert bd.ra(16.0) is None and bd.ra(29.0) is None
    assert bd.ra_khoang(16.0, 29.0) == []


# ══════════════════════════════════════════════════════════════════════════════
#  §2  `cua_so_ra` — vung nao ap luc nao
# ══════════════════════════════════════════════════════════════════════════════

def test_vung_KHONG_khai_gio_thi_ap_ca_video():
    assert cdr.cua_so_ra(KHOANG, [_hop()]) == [None]


def test_vung_co_gio_cho_ra_khoang_cua_BAN_RA():
    assert cdr.cua_so_ra(KHOANG, [_hop(tu_giay=10.0, den_giay=12.0)]) == [[(5.0, 7.0)]]


def test_vung_mat_het_cho_ap_thi_NEM_chu_khong_bo_qua():
    """⛔ Bo qua im lang la giao mot video khong che gi o cho khach da ve — va
    ho chi biet khi xem tep da nhan."""
    with pytest.raises(cdr.CheDoError) as e:
        cdr.cua_so_ra(KHOANG, [_hop(tu_giay=16.0, den_giay=29.0)])
    assert "vùng che" in str(e.value).lower()


def test_chi_khai_MOT_dau_van_hop_le():
    """`tu_giay` khong kem `den_giay` = "tu day toi het". `vung_che` cho phep,
    nen day phai nhan."""
    assert cdr.cua_so_ra(KHOANG, [_hop(tu_giay=12.0)]) == [[(7.0, 20.0)]]


def test_cua_so_ra_DUNG_ban_do_thay_vi_tu_tinh():
    """🔑 Mot phep anh xa thu hai la mot phep se lech.

    Chot bang **hanh vi**: ket qua cua `cua_so_ra` phai bang ket qua cua
    `BanDoThoiGian.ra_khoang` tren cung dau vao. Neu ai do viet lai phep tinh o
    `che_do_render`, bai nay chi do khi hai ban da lech — nen no con chot them
    rang loi goi CO ton tai (xem `test_ma_nguon_khong_tu_tinh_anh_xa`).
    """
    v = _hop(tu_giay=8.0, den_giay=33.0)
    assert cdr.cua_so_ra(KHOANG, [v]) == [_ban_do().ra_khoang(8.0, 33.0)]


def test_ma_nguon_khong_tu_tinh_anh_xa():
    """Doc AST: `cua_so_ra` phai GOI `ra_khoang`, khong tu cong don."""
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(cdr.cua_so_ra))
    goi = {n.func.attr for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "ra_khoang" in goi


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Chuoi bo loc — V6-01
# ══════════════════════════════════════════════════════════════════════════════

def test_vung_khong_gio_thi_KHONG_co_enable():
    """Duong cu phai giong het truoc pha 12 — khong them mot ky tu nao."""
    assert "enable=" not in cdr.loc_cat_noi(KHOANG, [_hop()])


def test_vung_co_gio_thi_CO_enable_dung_khoang_cua_ban_ra():
    loc = cdr.loc_cat_noi(KHOANG, [_hop(tu_giay=10.0, den_giay=12.0)])
    assert "enable=between(t" in loc
    assert "5.0000" in loc and "7.0000" in loc


def test_dau_phay_trong_enable_duoc_THOAT():
    r"""🔴 Trong cu phap filter, `,` ngan hai BO LOC va `:` ngan hai THAM SO.

    Mot `between(t,5,7)` khong thoat lam ffmpeg doc `5` va `7` thanh hai bo loc
    moi. Cung cai bay da lam `min(iw,ih)` do o V5, va thong bao cua ffmpeg khi
    do khong nhac gi toi dau phay.
    """
    loc = cdr.loc_cat_noi(KHOANG, [_hop(tu_giay=10.0, den_giay=12.0)])
    m = re.search(r"enable=([^\[\];]+)", loc)
    assert m, loc
    ve = m.group(1)
    assert "\\," in ve, f"dau phay chua thoat: {ve}"
    # Khong con mot dau phay TRAN nao
    assert not re.search(r"(?<!\\),", ve), f"con dau phay tran: {ve}"


def test_mot_vung_cho_ra_DUNG_MOT_between():
    """He qua truc tiep cua dinh ly o §1: mot vung che khong bao gio can hai ve.

    ⚠️ `_bat_khi` VAN cong nhieu ve lai duoc (`between()` tra 1/0, va `enable`
       chi hoi "khac 0 khong", nen tong la phep HOAC dung cu phap ffmpeg). Nhanh
       ay khong the toi tu vung che — bai nay chot dieu do thay vi gia vo dung
       no bang mot ca khong ton tai.
    """
    loc = cdr.loc_cat_noi([(0.0, 5.0), (50.0, 60.0)],
                          [_hop(tu_giay=1.0, den_giay=51.0)])
    ve = re.search(r"enable=([^\[\];]+)", loc).group(1)
    assert ve.count("between(") == 1, ve


def test_bat_khi_CONG_duoc_nhieu_ve_khi_that_su_co_nhieu():
    """Chot rieng ham dung bieu thuc, vi duong tu vung che khong toi duoc no.

    ⛔ Neu khong chot o day thi nhanh nay la ma **khong ai do**, va no se hong
       im lang vao ngay dau tien co mot nguoi goi khac.
    """
    ve = cdr._bat_khi([(1.0, 2.0), (5.0, 6.0)])
    assert ve.count("between(") == 2 and "+" in ve, ve
    assert cdr._bat_khi(None) == "" and cdr._bat_khi([]) == ""


def test_moi_vung_co_enable_RIENG_cua_no():
    """Hai vung, mot co gio mot khong: vung khong gio phai KHONG bi gan enable
    cua vung kia."""
    loc = cdr.loc_cat_noi(KHOANG, [_hop(tu_giay=10.0, den_giay=12.0), _hop(y0=0.1, y1=0.2)])
    assert loc.count("enable=") == 1, loc


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Van tay — V6-02, ve nguy hiem hon
# ══════════════════════════════════════════════════════════════════════════════

def _vt(vung):
    return cdr.van_tay_che_do(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
                              khoang=KHOANG, vung=vung)


def test_doi_KHOANG_THOI_GIAN_thi_van_tay_DOI():
    """🔴 Day la lo hong V5 de lai, va no la ve nguy hiem hon trong hai ve.

    `test_457::test_doi_VUNG_thi_van_tay_DOI` chot toa do — dung, va van dung.
    No khong chot **gio**, vi luc no duoc viet gio chua co tac dung nao. Mot
    phep kiem dung van co the co mot chieu khong ai hoi.
    """
    a = _vt([_hop(tu_giay=10.0, den_giay=12.0)])
    b = _vt([_hop(tu_giay=10.0, den_giay=13.0)])
    assert a != b, "doi `den_giay` ma van tay khong doi — se phuc vu nham tep"


def test_them_gio_vao_mot_vung_KHONG_gio_cung_doi_van_tay():
    assert _vt([_hop()]) != _vt([_hop(tu_giay=1.0)])


def test_VANG_MAT_va_None_bam_GIONG_nhau():
    """⭐ Chieu nguoc lai, va no cung dat: neu `{}` va `{"tu_giay": None}` bam
    khac nhau thi moi lan chay khong ke gio bong doi van tay tuy theo client co
    gui khoa rong hay khong."""
    assert _vt([_hop()]) == _vt([_hop(tu_giay=None, den_giay=None)])


def test_PHIEN_BAN_CHE_DO_da_len_bac():
    """⛔ Khong bump thi moi ban render tinh o thoi V5 — khi gio la mot truong
    CHET — van duoc dung lai cho mot cau hoi nay da khac."""
    assert cdr.PHIEN_BAN_CHE_DO >= 3


# ══════════════════════════════════════════════════════════════════════════════
#  §5  `vung_che` van la cua vao duy nhat
# ══════════════════════════════════════════════════════════════════════════════

def test_gio_van_di_qua_chuan_hoa_va_van_bi_kiem():
    """Pha 12 khong duoc noi long cua vao: gio nguoc van phai bi tu choi."""
    with pytest.raises(vung_che.VungLoi):
        vung_che.chuan_hoa_mot(_hop(tu_giay=10.0, den_giay=4.0))
    ra = vung_che.chuan_hoa_mot(_hop(tu_giay=2.5, den_giay=9.0))
    assert (ra["tu_giay"], ra["den_giay"]) == (2.5, 9.0)


# ══════════════════════════════════════════════════════════════════════════════
#  §6  Bang chung ENGINE THAT — ffmpeg co nhan, va vung co mo DUNG cho
# ══════════════════════════════════════════════════════════════════════════════

_CAT_DO = "crop=iw*0.80:ih*0.35:iw*0.10:ih*0.60"


def _psnr(a, b) -> float:
    r = subprocess.run(["ffmpeg", "-i", str(a), "-i", str(b), "-lavfi", "psnr",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"average:([0-9.]+|inf)", r.stderr)
    assert m, r.stderr[-1500:]
    return float("inf") if m.group(1) == "inf" else float(m.group(1))


@rao_chan_nang.NANG
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="khong co ffmpeg")
@pytest.mark.skipif(os.environ.get(rao_chan_nang.BIEN) != "1",
                    reason=rao_chan_nang.LY_DO)
def test_ENGINE_vung_chi_mo_TRONG_cua_so(tmp_path):
    """🔑 Phep do nay khong hoi "chuoi loc co dung khong" — mot bai doc chuoi da
    hoi roi. No hoi hai cau chi ffmpeg tra loi duoc:

      ffmpeg co NHAN chuoi ay khong, va vung co mo DUNG trong khoang roi thoi.

    ⛔ VA NO CAN MOT DOI CHUNG. Hai ban do dau tien cua phep do nay deu SAI:

      ban 1  so hai khung KHAC NHAU cua cung mot ban render -> chenh lech noi ve
             NOI DUNG, khong ve do mo (23.017 vs 8.932 byte, nguoc chieu)
      ban 2  sua doi chung nhung giu proxy "anh mo thi PNG nho hon" — sai voi
             anh mau THU: no gan nhu toan mang phang, PNG nen cuc tot, va lam mo
             mot mang phang lam tep TO RA (ti le 2,81)

    ⇒ Ban nay hoi bang PSNR va hoi CA HAI CHIEU. Chieu thu hai moi la chieu hay
      bi bo quen: thieu no thi mot ban lam mo SUOT CA VIDEO — dung lo hong dang
      sua — van cho ra PASS.
    """
    from tests.fixtures.asv_media import tiny_mp4

    nguon = tmp_path / "nguon.mp4"
    tiny_mp4(nguon, duration_s=40.0)
    vung = [_hop(tu_giay=10.0, den_giay=12.0)]

    ra = {}
    for ten, v in (("co", vung), ("khong", ())):
        ra[ten] = tmp_path / f"{ten}.mp4"
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", str(nguon), "-filter_complex",
             cdr.loc_cat_noi(KHOANG, v), "-map", "[ra]", "-an",
             "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", str(ra[ten])],
            capture_output=True, text=True)
        assert r.returncode == 0, f"ffmpeg tu choi chuoi loc:\n{r.stderr[-2000:]}"

    mo = f"boxblur=luma_radius=min(w{chr(92)},h)/{cdr._MAU_BAN_KINH}:luma_power=2"

    def khung(video, moc, ten, them=""):
        p = tmp_path / f"{ten}.png"
        vf = _CAT_DO + (("," + them) if them else "")
        r = subprocess.run(["ffmpeg", "-y", "-ss", str(moc), "-i", str(video),
                            "-vf", vf, "-frames:v", "1", str(p)],
                           capture_output=True, text=True)
        assert r.returncode == 0 and p.exists(), r.stderr[-1500:]
        return p

    # TRONG cua so (moc 6s cua ban ra): ban co vung phai TRUNG ban da tu lam mo.
    x = khung(ra["co"], 6.0, "trong_co")
    y_mo = khung(ra["khong"], 6.0, "trong_khong_mo", them=mo)
    y = khung(ra["khong"], 6.0, "trong_khong")
    assert _psnr(x, y_mo) > _psnr(x, y) + 6.0, "trong cua so: vung KHONG bi lam mo"

    # NGOAI cua so (moc 15s): hai ban phai y het nhau.
    x2 = khung(ra["co"], 15.0, "ngoai_co")
    y2 = khung(ra["khong"], 15.0, "ngoai_khong")
    assert _psnr(x2, y2) == float("inf"), "ngoai cua so: vung VAN bi lam mo"
