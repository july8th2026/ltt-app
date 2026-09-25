"""V5 — DIEN NEN (`vung_che.LOAI_DIEN_NEN`) di het duong, va **van tay phai doi**.

## 🔴 Cau hoi that cua tep nay

⛔ Khong phai *"chuoi loc co sinh ra khong"*. Cau that la: **mot cau hinh khac
co cho mot van tay khac khong.** Neu khong, khach bat dien nen, tra tien, va lan
chay lai **tra ve tep CU** — khong loi, khong canh bao, chi mot luot chay "nhanh
bat thuong". `assets.py` goi ten cai bay do: *"sot tham so = serve nham"*.

⚠️ Van tay cua giai doan RENDER co **hai** nguon doc lap, nen bai nay ghim ca
hai — khuon lay cua `test_3801` (lan `asv-gui`):

| nguon | doi khi nao | ai giu |
|---|---|---|
| checksum ban dung | khach doi **ho so** (`vung[i].loai`) | `ban_dung` |
| `PHIEN_BAN_CHE_DO` | ta doi **ma sinh lenh** | `che_do_render` |

⛔ Chi ghim mot cai la de ho cai kia.

## ⛔ Va bai nay dung ban dung THAT

`ban_dung.dung()` chu khong phai mot `dict` go tay: mot bai bam ho so truc tiep
van **xanh** ke ca khi `dung()` danh roi `loai` tren duong vao ban dung.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from apps.auto_scan_video import ban_dung as bd
from apps.auto_scan_video import che_do_render as cdr
from apps.auto_scan_video import hop_dong_v4
from apps.auto_scan_video import vung_che as vc

#: 1024x576 — khung cua mot trong hai phim that, de hinh hoc trong bai nay la
#: hinh hoc that chu khong phai mot con so tron.
RONG, CAO = 1024, 576

KHOANG = [(0.0, 5.0)]


def _hop(loai: str, **them) -> dict:
    ra = {"loai": loai, "y0": 0.82, "y1": 0.96, "x0": 0.0, "x1": 1.0}
    ra.update(them)
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  1. Van tay — cau hoi cuoi
# ══════════════════════════════════════════════════════════════════════════════

def _ban(vung) -> dict:
    """Ban dung toi thieu qua DUNG ham san pham.

    ⚠️ `ban_dung.dung` goi `kiem()` o dong cuoi, nen mot ban dung khong thi hanh
       duoc **khong bao gio ton tai** — no chet ngay luc dung.
    """
    return bd.dung(
        khoa_video="v/1.mp4", khoa_nen="a/nen.wav", khoa_master="a/master.wav",
        ke_hoach={"doan": [], "tong_ms": 5000}, ban_ke_tieng={"doan": []},
        phien_ban_ffmpeg="n7.0", tong_giay=5.0,
        che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
        khoang_giu=list(KHOANG), preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
        rong_khung=RONG, cao_khung=CAO, vung=vung)


def _van_tay(vung) -> str:
    return hashlib.sha256(
        json.dumps(_ban(vung), sort_keys=True).encode("utf-8")).hexdigest()


def test_doi_lam_mo_SANG_dien_nen_thi_van_tay_PHAI_doi():
    """🔴 Bai quan trong nhat cua tep. Hong bai nay = khach tra tien, nhan tep cu.

    Hai lan chay khac nhau **chi o mot chu** (`lam_mo` -> `dien_nen`) cho ra hai
    tep hoan toan khac nhau — mot ben con vet mo, mot ben da xoa han chu.
    """
    mo = _van_tay([_hop(vc.LOAI_LAM_MO)])
    nen = _van_tay([_hop(vc.LOAI_DIEN_NEN)])
    assert mo != nen, (
        "doi lam_mo -> dien_nen ma van tay KHONG doi: mot lan chay lai se tra "
        "ve tep cu, va no khong bao gio no")


def test_BA_cau_hinh_cho_BA_van_tay_khac_nhau():
    """⚠️ Đoi chung cho bai tren: neu `vung` bi nuot o dau do tren duong vao ban
    dung thi ca ba se bang nhau, va bai tren van co the xanh nho mot khac biet
    tinh co khac.
    """
    vt = {ten: _van_tay(v) for ten, v in (
        ("khong", []),
        ("lam_mo", [_hop(vc.LOAI_LAM_MO)]),
        ("dien_nen", [_hop(vc.LOAI_DIEN_NEN)]))}
    assert len(set(vt.values())) == 3, f"co van tay trung nhau: {vt}"


def test_van_tay_che_do_BAM_loai_vung():
    """Nua ky thuat cua bai tren, o dung ham giu cache."""
    chung = {"che_do": cdr.CAT_MA_HOA_LAI, "bo_ma_hoa": "libx264",
             "khoang": KHOANG}
    assert (cdr.van_tay_che_do(vung=[_hop(vc.LOAI_LAM_MO)], **chung)
            != cdr.van_tay_che_do(vung=[_hop(vc.LOAI_DIEN_NEN)], **chung))


def test_PHIEN_BAN_CHE_DO_da_len_khi_chuoi_loc_doi():
    """🔑 Nua thu hai cua van tay, va la nua **khong** phu thuoc ho so khach.

    Chang VUNG gio di qua `_loc_vung` thay vi `_loc_lam_mo` goi thang. Mot lan
    chay **khong** co vung dien nen nao van di qua ma sinh lenh MOI, va ban dung
    cua no khong doi mot byte — nen thu DUY NHAT noi ra dieu do la con so nay.

    ⛔ Ghim `>= 9` chu khong `== 9`: chot rang so da di qua moc cua lan
       `asv-vung`, khong khoa cung mot gia tri ma lan sau phai sua.
    """
    assert cdr.PHIEN_BAN_CHE_DO >= 9


# ══════════════════════════════════════════════════════════════════════════════
#  2. Chuoi loc — lam mo giu NGUYEN, dien nen la mot nhanh KHAC
# ══════════════════════════════════════════════════════════════════════════════

def test_chuoi_LAM_MO_khong_doi_mot_ky_tu():
    """⛔ Bo dieu phoi moi ⛔ khong duoc lam xe dich duong cu.

    Mot ky tu lech o day la mot van tay lech cho **moi ban render cu** — tuc
    toan bo cache render bi pha ma khong ai co y do.
    """
    cho_doi = (
        "[0:v]trim=start=0.000000:end=5.000000,setpts=PTS-STARTPTS[v0];"
        "[v0]concat=n=1:v=1:a=0[noi];"
        "[noi]split[c0][g0];"
        "[c0]crop=trunc(iw*1.000000/2)*2:trunc(ih*0.140000/2)*2:"
        "trunc(iw*0.000000/2)*2:trunc(ih*0.820000/2)*2,"
        "boxblur=luma_radius=min(w\\,h)/8:luma_power=2[m0];"
        "[g0][m0]overlay=trunc(W*0.000000/2)*2:trunc(H*0.820000/2)*2[ra]")
    assert cdr.loc_cat_noi(KHOANG, vung=[_hop(vc.LOAI_LAM_MO)]) == cho_doi


def test_dien_nen_dung_CROP_VFLIP_SCALE_chu_khong_boxblur():
    """Nhanh dien nen la mot ky thuat KHAC han, ⛔ khong phai mot tham so khac."""
    loc = cdr.loc_cat_noi(KHOANG, vung=[_hop(vc.LOAI_DIEN_NEN)],
                          rong_nguon=RONG, cao_nguon=CAO)
    assert "boxblur" not in loc
    for manh in ("crop=", "vflip", "scale=", "setsar=1", "alphamerge",
                 "overlay="):
        assert manh in loc, manh


def test_hai_vung_HAI_loai_deu_chay_va_giu_thu_tu():
    """Chuoi nhan phai noi lien: vung 1 doc dau ra cua vung 0."""
    loc = cdr.loc_cat_noi(
        KHOANG, vung=[_hop(vc.LOAI_LAM_MO, y0=0.05, y1=0.20),
                      _hop(vc.LOAI_DIEN_NEN)],
        rong_nguon=RONG, cao_nguon=CAO)
    assert "[g0][m0]overlay=" in loc and "[o0]" in loc
    assert "[o0]split[dg1][dk1]" in loc
    assert loc.endswith("[ra]")


def test_danh_dau_phu_de_VAN_di_duong_lam_mo():
    """⚠️ `danh_dau_phu_de` mang nghia AM nhung van bi lam mo — hanh vi co tu V5
    (`phu_de.py:280`). Bo dieu phoi ⛔ khong duoc nhan tien "sua" no.
    """
    a = cdr.loc_cat_noi(KHOANG, vung=[_hop(vc.LOAI_DANH_DAU_PHU_DE)])
    b = cdr.loc_cat_noi(KHOANG, vung=[_hop(vc.LOAI_LAM_MO)])
    assert "boxblur" in a and a == b


# ══════════════════════════════════════════════════════════════════════════════
#  3. ⛔ KHONG CO DUONG LUI IM LANG
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_biet_kich_thuoc_nguon_thi_NEM():
    """Hinh hoc dien nen tinh bang PIXEL. ⛔ Khong biet khung thi ⛔ khong doan."""
    with pytest.raises(cdr.CheDoError):
        cdr.loc_cat_noi(KHOANG, vung=[_hop(vc.LOAI_DIEN_NEN)])


def test_vung_trum_CA_HAI_mep_thi_NEM_chu_khong_lui_ve_lam_mo():
    """🔴 He tham chieu lui ve LAM MO khi hinh hoc hong (`localize.py:6588`), va
    chinh ho ghi cai gia: *"khach chon Keo mep nhan ve Lam mo, ton 2 luot ffmpeg
    vo ich, va KHONG co gi bao cho khach"*.

    ⇒ O ta: nem, kem mot cau khach doc duoc.
    """
    with pytest.raises(cdr.CheDoError) as e:
        cdr.hinh_hoc_dien_nen(_hop(vc.LOAI_DIEN_NEN, y0=0.0, y1=1.0),
                              RONG, CAO)
    assert "làm mờ" in str(e.value)


def test_ban_dung_CHAN_TRUOC_khi_ton_tai():
    """⛔ Nem o `kiem()` chu khong o phut thu muoi sau khi da chiem suat ffmpeg.

    ⚠️ Cung hinh dang voi chot `cao_khung` cua lop phu ngay canh no.
    """
    with pytest.raises(bd.BanDungError):
        bd.dung(khoa_video="v/1.mp4", khoa_nen="a/nen.wav",
                khoa_master="a/master.wav",
                ke_hoach={"doan": [], "tong_ms": 5000},
                ban_ke_tieng={"doan": []}, phien_ban_ffmpeg="n7.0",
                tong_giay=5.0, che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
                khoang_giu=list(KHOANG),
                preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
                vung=[_hop(vc.LOAI_DIEN_NEN)])   # ⛔ khong khai khung nguon


def test_lam_mo_VAN_chay_khi_khong_biet_khung():
    """Đoi chung: hai bai tren phai la luat cua RIENG dien nen. Lam mo tinh bang
    bieu thuc `iw`/`ih` nen no chua bao gio can biet khung — ⛔ dung siet nham no.
    """
    assert "boxblur" in cdr.loc_cat_noi(KHOANG, vung=[_hop(vc.LOAI_LAM_MO)])


# ══════════════════════════════════════════════════════════════════════════════
#  4. Ba BAT BIEN cua `che_keo` — Viral da tra gia, ta ⛔ dung tra lai
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("y0,y1", [
    (0.82, 0.96), (0.0, 0.14), (0.50, 0.999), (0.001, 0.30), (0.40, 0.60)])
def test_dai_nguon_LUON_chan_va_it_nhat_2px(y0, y1):
    """🔴 BAT BIEN 1 — `yuv420p` lay mau chroma **2:1 theo chieu DOC**, nen mot
    dai nguon cao 1 px cho ra **0 hang** chroma va ffmpeg chet `-22` o **ca**
    `h264_nvenc` **lan** `libx264`. Do that cua ho: `hs=1` LOI, `hs=2` OK.
    """
    hh = cdr.hinh_hoc_dien_nen(_hop(vc.LOAI_DIEN_NEN, y0=y0, y1=y1), RONG, CAO)
    assert hh["day_nguon"] % 2 == 0 and hh["day_nguon"] >= 2
    assert hh["day_nguon"] <= cdr.CHE_KEO_HS_MAX


@pytest.mark.parametrize("y0,y1", [
    (0.82, 0.96), (0.0, 0.14), (0.50, 0.999), (0.30, 0.55)])
def test_dai_nguon_nam_TRONG_khung_va_NGOAI_vung(y0, y1):
    """🔴 BAT BIEN 2 — noi het cho thi crop nguon roi ra ngoai khung => ffmpeg
    chet. Ma chua **ca hai ben vo dieu kien** cung sai: dai sat day ⛔ khong co
    nguon duoi ma van bi tru 4 px => loi duc **hut 3 px o day, dung cho chu nam**.
    """
    v = _hop(vc.LOAI_DIEN_NEN, y0=y0, y1=y1)
    hh = cdr.hinh_hoc_dien_nen(v, RONG, CAO)
    ny, day = hh["nguon_y"], hh["day_nguon"]
    assert 0 <= ny and ny + day <= CAO, "dai nguon roi ra ngoai khung"
    # ⛔ NGOAI loi duc: chong len loi la chep lai chinh chu can xoa.
    assert ny + day <= hh["y"] or ny >= hh["y"] + hh["cao"]
    # Loi duc phai PHU TRON dai goc — hut 1 px la ho chu.
    assert hh["y"] <= round(y0 * CAO) and hh["y"] + hh["cao"] >= round(y1 * CAO)


def test_vung_tan_nam_HAN_NGOAI_dai_goc():
    """🔴 BAT BIEN 3 — *"Tan an vao trong = LO CHU"*. Vung tan phai nam trong
    phan **da noi ra**, ⛔ khong an vao dai khach ve.
    """
    y0, y1 = 0.82, 0.96
    hh = cdr.hinh_hoc_dien_nen(_hop(vc.LOAI_DIEN_NEN, y0=y0, y1=y1), RONG, CAO)
    fl, fr, ft, fd = hh["tan"]
    assert hh["y"] + ft <= round(y0 * CAO), "tan tren an vao dai goc"
    assert hh["y"] + hh["cao"] - fd >= round(y1 * CAO), "tan duoi an vao dai goc"


def test_alpha_canh_KHONG_noi_duoc_thi_DUC_HAN():
    """🔴 `max(1, f)` "cho chac khoi chia 0" bien canh `f=0` thanh ramp tren DUNG
    1 pixel => hang/cot ngoai cung alpha = 0 => **HO 1 px hinh goc ngay tai mep**.
    Luoi cua ho bat 4/15 ca, toan o SAT MEP KHUNG.
    """
    assert cdr._alpha_hinh_thang(100, 50, 0, 0, 0, 0) == ""
    chi_tren = cdr._alpha_hinh_thang(100, 50, 0, 0, 8, 0)
    assert "Y/8" in chi_tren
    assert "X/" not in chi_tren and "-X)/" not in chi_tren


def test_min_long_thoat_dau_phay():
    """⛔ ffmpeg ⛔ khong co `min` ba tham so, va `,` tran ngan hai BO LOC."""
    assert cdr._min_long(["a"]) == "a"
    assert cdr._min_long(["a", "b", "c"]) == "min(min(a\\,b)\\,c)"


@pytest.mark.parametrize("v0,dai,f,san,tran", [
    (448, 124, 37, 4, 572), (0, 80, 24, 0, 576), (496, 80, 24, 4, 576),
    (10, 9, 3, 0, 577), (2, 500, 150, 4, 572)])
def test_noi_cho_tan_LUON_chan_va_o_TRONG_khoang(v0, dai, f, san, tran):
    """🔴 Ban dau cua ho viet `min(<da lam chan>, tran - v0n)` — ve thu hai co the
    LE va `min` chon dung no (do that: dai sat day ra cao **71**). So le la ca
    chia-le cua `yuv420p`: hong heap IM LANG, va sap **khong deu** nen chay mot
    luot rat de tuong lanh.

    ⚠️ "Phu tron doan goc" ⛔ **khong** phai bat bien cua ham NAY: `[san, tran]`
       co the hep hon chinh doan goc (ca cuoi trong bang). Ham chi hua *chan* va
       *nam trong khoang*; viec phu tron do `hinh_hoc_dien_nen` kiem tuong minh
       roi **bo tan bien** khi khong dat — xem bai ngay duoi.
    """
    a, n, td, tc = cdr._noi_cho_tan(v0, dai, f, san, tran)
    assert n % 2 == 0, "do dai LE — xem `_chan2`"
    assert a >= san and a + n <= tran
    assert td >= 0 and tc >= 0
    if san <= v0 and tran >= v0 + dai:
        assert a <= v0 and a + n >= v0 + dai, "khong phu tron doan goc"


def test_khong_du_cho_NOI_thi_bo_tan_bien_chu_khong_bo_loi_duc():
    """⛔ Đieu kien dung la PHU TRON dai goc, ⛔ KHONG phai "cao hon dai goc": mot
    dai bi day LEN roi cat cut o day van "cao hon" ma day lai **ho chu**.

    Khung 1024x20 (rat thap): sau khi chua 4 px dai nguon moi ben thi ⛔ khong
    con mot px nao de tan => mep cung, dung hanh vi truoc V5 — ma loi duc van
    trum khit dai goc.
    """
    hh = cdr.hinh_hoc_dien_nen(_hop(vc.LOAI_DIEN_NEN, y0=0.2, y1=0.8), 1024, 20)
    assert hh["tan"] == (0, 0, 0, 0)
    assert hh["y"] <= 4 and hh["y"] + hh["cao"] >= 16
    # Đoi chung: khung cao hon thi co tan bien that — bai tren ⛔ khong xanh vi
    # `tan` bi tat o dau do.
    cao_hon = cdr.hinh_hoc_dien_nen(
        _hop(vc.LOAI_DIEN_NEN, y0=0.2, y1=0.8), 1024, 576)
    assert cao_hon["tan"][2] > 0 and cao_hon["tan"][3] > 0


# ══════════════════════════════════════════════════════════════════════════════
#  5. Hai cho khai cung mot chuoi loc thi phai BANG NHAU
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_tham_chieu_VMAF_dung_DUNG_chuoi_loc_cua_render():
    """⛔ `qc.loc_tham_chieu` thieu `rong_nguon`/`cao_nguon` cho toi 25/09, va
    docstring cua no van khai la *"dung DUNG tham so"*. Voi dien_nen thi cai
    lech do ⛔ khong con am: no cho ra mot diem VMAF cua mot chuoi loc KHAC.
    """
    from apps.auto_scan_video import qc

    hinh = {"khoang_giu": KHOANG, "vung": [_hop(vc.LOAI_DIEN_NEN)],
            "rong_khung": RONG, "cao_khung": CAO}
    assert qc.loc_tham_chieu(hinh, duong_chu=[], duong_ass="") == (
        cdr.loc_cat_noi(KHOANG, vung=hinh["vung"], cao_khung=CAO,
                        rong_khung=RONG, chi_so_logo_dau=qc.CHI_SO_LOGO_DAU,
                        rong_nguon=RONG, cao_nguon=CAO))
