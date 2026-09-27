"""4880 — LAN C: mot con so tu thuong nguon, ba trang thai, MOT thong diep.

Ba phep kiem dau tai hien dung con bug dat nhat cua 27/09: mot tep tieng **dai
1,44 giay** bi bao la *"Doan seg_0004 chua co tieng"* vi ban ke ghi `giay = 0.0`
(`giai_doan_giong._doan_con_dung` tra `0.0` khi kho ⛔ khong co `local_path` —
kho production la R2). Thong diep ay **chi tay vao doan tieng** trong khi loi nam
o **phep DO** o thuong nguon, va no lam nguoi soat duoi sai ba gia thuyet.

⭐ `timing_align` co **du bang chung trong tay** de noi that: dong ban ke mang
   `khoa` cua tep tieng. `khoa` co ma `giay = 0` thi do la **phep do hong**, ⛔
   khong phai *"chua co tieng"*. Bon phep kiem duoi day ghim dieu do bang may.
"""
from __future__ import annotations

import pytest


# ══════════════════════════════════════════════════════════════════════════════
#  timing_align — `giay = 0` gom BA trang thai vao MOT thong diep
# ══════════════════════════════════════════════════════════════════════════════

MUC = [{"ma": "seg_0004", "bat": 1.0, "ket": 3.0, "chu": "xin chao"}]


def _goi(ban_ke):
    from apps.auto_scan_video import giai_doan_thoi_gian as gd
    return gd.do_dai_tieng(MUC, ban_ke)


def test_CO_tep_ma_giay_0_thi_thong_diep_chi_vao_PHEP_DO():
    """🔴 Con bug 27/09. Dong ban ke CO `khoa` ⇒ tep ton tai ⇒ `0` la loi DO.

    ⛔ Thong diep ⛔ khong duoc noi *"chua co tieng"*: doan CO tieng, chinh phep
       do noi doi. Va no phai goi ten `voice_synthesis` — noi phai sua.
    """
    from apps.auto_scan_video import giai_doan_thoi_gian as gd

    ban_ke = {"doan": [{"ma": "seg_0004", "khoa": "a/b/seg4.wav", "giay": 0.0}]}
    with pytest.raises(gd.ThieuDauVao) as e:
        _goi(ban_ke)
    tin = str(e.value)
    assert "a/b/seg4.wav" in tin, (
        "thong diep ⛔ khong neu KHOA cua tep tieng dang ton tai, nen nguoi doc "
        "⛔ khong the biet tep co that: %r" % tin)
    assert "voice_synthesis" in tin, (
        "thong diep ⛔ khong chi ra noi phep DO hong (`voice_synthesis`): %r" % tin)


def test_THIEU_DONG_va_THIEU_KHOA_va_KHONG_DO_DUOC_la_BA_thong_diep():
    """Ba khiem khuyet khac loai ⇒ ba thong diep khac nhau, ⛔ khong mot cai."""
    from apps.auto_scan_video import giai_doan_thoi_gian as gd

    tin = {}
    for ten, ban_ke in {
        # 1) ⛔ khong co dong nao cho `ma` — ban ke va content.json lech nhau
        "thieu_dong": {"doan": []},
        # 2) co dong, ⛔ khong co khoa — that su chua co tep tieng
        "thieu_khoa": {"doan": [{"ma": "seg_0004", "khoa": "", "giay": 0.0}]},
        # 3) co khoa ma `giay` = 0 — phep DO hong (con bug hom nay)
        "khong_do": {"doan": [{"ma": "seg_0004", "khoa": "k.wav", "giay": 0.0}]},
        # 4) co khoa ma ⛔ khong co khoa `giay` — schema ban ke hong
        "thieu_truong": {"doan": [{"ma": "seg_0004", "khoa": "k.wav"}]},
    }.items():
        with pytest.raises(gd.ThieuDauVao) as e:
            _goi(ban_ke)
        tin[ten] = str(e.value)

    assert len(set(tin.values())) == len(tin), (
        "hai trong bon khiem khuyet khac loai cho CUNG mot thong diep — day dung "
        "la cai bay da lam nguoi soat duoi sai ba gia thuyet: %r" % tin)


def test_doan_CO_Y_IM_LANG_ma_giay_0_duoc_goi_ten_RIENG():
    """Co `im_lang` (Task 25, lan B) la trang thai THU BA, ⛔ khong phai khiem khuyet.

    Task 25 chot: doan im lang van co MOT tep khoang lang dai dung bang khe, tuc
    `giay > 0`. Nen `im_lang` + `giay = 0` la mot **khiem khuyet khac han** hai
    cai kia (khoang lang ⛔ khong duoc sinh), va thong diep phai noi dung the.
    """
    from apps.auto_scan_video import giai_doan_thoi_gian as gd

    ban_ke = {"doan": [{"ma": "seg_0004", "khoa": "im.wav", "giay": 0.0,
                        "im_lang": True}]}
    with pytest.raises(gd.ThieuDauVao) as e:
        _goi(ban_ke)
    assert "im" in str(e.value).lower(), (
        "doan CO Y im lang bi bao giong mot doan thieu tieng: %r" % str(e.value))

    # Va duong BINH THUONG cua `im_lang` (khoang lang dai bang khe) ⛔ khong hong
    ra = _goi({"doan": [{"ma": "seg_0004", "khoa": "im.wav", "giay": 2.0,
                         "im_lang": True}]})
    assert ra["seg_0004"] == 2.0


def test_giay_hop_le_thi_tra_dung_so_va_giu_ca_dong_DI_THEO():
    """⛔ Khong duoc that chat hon ham cu: moi dong ban ke van phai co trong dict."""
    ban_ke = {"doan": [
        {"ma": "seg_0004", "khoa": "k.wav", "giay": 1.44, "gop": ["seg_0004",
                                                                  "seg_0005"]},
        {"ma": "seg_0005", "khoa": "k.wav", "giay": 0.6, "gop_vao": "seg_0004"},
    ]}
    assert _goi(ban_ke) == {"seg_0004": 1.44, "seg_0005": 0.6}


# ══════════════════════════════════════════════════════════════════════════════
#  compose — `(0, 0)` cua khung nguon gom BA ly do, va ⛔ khong mot dong log
# ══════════════════════════════════════════════════════════════════════════════

def test_khung_nguon_phan_biet_BA_ly_do_KHONG_DO_DUOC(monkeypatch):
    """`_co_khung` cu tra `(0, 0)` cho ca ba, va nuot ca ngoai le ⛔ khong log."""
    from apps.auto_scan_video import giai_doan_ban_dung as gd

    def _dat(khoa, ho_so=None, no=None):
        monkeypatch.setattr(gd, "_khoa_json", lambda *a, **k: khoa)
        def _doc(*a, **k):
            if no is not None:
                raise no
            return ho_so
        monkeypatch.setattr(gd, "_doc", _doc)

    # ⚠️ Doc theo TEN, ⛔ khong so sanh ca tuple: mot phep so sanh theo VI TRI
    #    se do moi lan ai do them mot truong — do la do CACH GO chu ⛔ khong do
    #    dieu bai nay chot.
    def _ba(ho_so=None, no=None, khoa="k.json"):
        _dat(khoa, ho_so=ho_so, no=no)
        r = gd._khung_nguon(None, None, None)
        return (r.rong, r.cao, r.ly_do)

    assert _ba(khoa="") == (0, 0, gd.KHUNG_THIEU_HO_SO)          # 1) ⛔ khong ho so
    assert _ba(no=ValueError("json hong")) == (0, 0, gd.KHUNG_HO_SO_HONG)  # 2) hong
    assert _ba(ho_so={"rong": 0, "cao": 0}) == (0, 0, gd.KHUNG_KHONG_KHAI)  # 3) rong
    assert _ba(ho_so={"rong": 1920, "cao": 1080, "xoay": 90}) == (1080, 1920, "")


def test_nhip_that_PHAN_BIET_khong_biet_voi_nhip_bang_khong():
    """⭐ **`nhap_media.nhip_that` — MOT noi tra loi *"video nay bao nhieu fps"*.**

    🔴 **Bai nay o day, ⛔ khong o `giai_doan_ban_dung` (B6, 27/09).** Truoc B6 ba
       truong nhip di kem `NguonHinh` de GD1 khai `-r`; nay `toc_do` ap o cuoi GD2
       va GD2 **tu soi tep vao cua chinh no**, nen cau hoi ve nhip thuoc ve
       `nhap_media` — noi `soi` ghi ba truong ay.

    ⚠️ Va do la dung hai trang thai ma bai nay ton tai de tach: `0.0` = *"⛔ khong
       BIET nhip"* (ho so thieu/hong), KHAC han *"nhip bang 0"*. Noi goi phai
       ⛔ KHONG khai `-r` khi ⛔ khong biet — ep video cua khach ve mot nhip ta bia
       ra thi te hon la de bo ma hoa tu chon.

    ⭐ Nguon VFR lay `fps_tb`, ⛔ khong `fps`: `r_frame_rate` la nhip DANH DINH va
       voi VFR no thuong CAO hon nhip that, nen khai no se bat bo ma hoa NHAN BAN
       khung. Chinh `soi` da canh bao dieu nay trong chu thich cua no.
    """
    from apps.auto_scan_video import nhap_media

    assert nhap_media.nhip_that({}) == 0.0, "ho so rong phai la ⛔ khong biet"
    assert nhap_media.nhip_that({"fps": 0.0, "fps_tb": 0.0}) == 0.0
    assert nhap_media.nhip_that({"fps": "hong"}) == 0.0, "ma rac ⇒ ⛔ khong biet"
    assert nhap_media.nhip_that({"fps": -5.0}) == 0.0, "nhip am ⇒ ⛔ khong biet"
    # CFR: lay nhip danh dinh.
    assert nhap_media.nhip_that(
        {"fps": 30.0, "fps_tb": 30.0, "vfr": False}) == 30.0
    # VFR: lay nhip THAT, ⛔ khong nhip danh dinh.
    assert nhap_media.nhip_that(
        {"fps": 60.0, "fps_tb": 24.5, "vfr": True}) == 24.5, (
        "nguon VFR ma lay nhip DANH DINH thi bo ma hoa se NHAN BAN khung")


def test_vung_dien_nen_ma_chua_do_duoc_khung_thi_noi_dung_LY_DO():
    """⛔ Khong de `ban_dung.kiem` bao *"ban dung khong khai no"* — do la HAU QUA.

    Nguyen nhan la ho so soi cua `media_prepare` thieu/hong, va chi COMPOSE biet
    dieu do. Noi sai cho o day la mot lan nua bat nguoi soat duoi di sai huong.
    """
    from apps.auto_scan_video import giai_doan_ban_dung as gd
    from apps.auto_scan_video.vung_che import LOAI_DIEN_NEN, LOAI_LAM_MO

    v_nen = ({"loai": LOAI_DIEN_NEN, "x0": 0.1, "y0": 0.1,
              "x1": 0.4, "y1": 0.3},)
    with pytest.raises(gd.ThieuDauVao) as e:
        gd._doi_khung_cho_vung(v_nen, 0, 0, gd.KHUNG_HO_SO_HONG)
    assert gd.KHUNG_HO_SO_HONG in str(e.value), (
        "thong diep ⛔ khong mang ly do THAT: %r" % str(e.value))

    # Khung do duoc ⇒ ⛔ khong nem. Vung khac loai ⇒ cung ⛔ khong nem.
    gd._doi_khung_cho_vung(v_nen, 1920, 1080, "")
    gd._doi_khung_cho_vung(({"loai": LOAI_LAM_MO},), 0, 0, gd.KHUNG_THIEU_HO_SO)


# ══════════════════════════════════════════════════════════════════════════════

def test_tong_ms_bang_0_KHONG_duoc_lang_le_mo_HAI_cong():
    """`tong_ms = 0` la mot so KHONG duoc kiem, va no mo HAI cong fail-open.

    1. `thoi_gian.kiem`: `if tong and int(ke_hoach["ket_cuoi_ms"]) > tong` —
       cong *"ban long tieng ⛔ khong bao gio dai hon video nguon"* (T2 /
       D-ASV-03) **tat** khi `tong == 0`.
    2. `ket_xuat.kiem_tep_ra`: `if mong > 0 and abs(that - mong) > ...` — cong
       ma chinh no goi la *"phep kiem co y nghia nhat"* (tep ra dai sai = tieng
       va hinh lech nhau) **tat** khi `ra.thoi_luong_giay == 0`, va gia tri do
       chinh la `tong_ms / 1000`.

    ⛔ `ban_dung.kiem` ⛔ khong dat mot rang buoc nao tren
       `ra.thoi_luong_giay`, nen COMPOSE la cho duy nhat con lai.
    """
    from apps.auto_scan_video import giai_doan_ban_dung as gd

    assert gd._tong_giay_ke_hoach({"tong_ms": 179200}) == 179.2
    for xau in ({"tong_ms": 0}, {"tong_ms": None}, {}):
        with pytest.raises(gd.ThieuDauVao):
            gd._tong_giay_ke_hoach(xau)

# ══════════════════════════════════════════════════════════════════════════════
#  render — nvenc duoc KHAI, bi HA, va ⛔ khong ban ghi nao phan biet duoc
# ══════════════════════════════════════════════════════════════════════════════

def test_tom_tat_render_ghi_CA_bo_ma_hoa_KHAI_va_bo_ma_hoa_THUC():
    """`codec_video` cua ffprobe la `h264` cho CA `h264_nvenc` va `libx264`.

    ⇒ `outputs` (thu duy nhat `thi_hanh.py` giu lai) ⛔ khong phan biet duoc
      *"da render tren GPU nhu da khai"* voi *"da lang le lui ve CPU"*. Mot
      `log.info` ⛔ khong phai mot ban ghi: no ⛔ khong vao `asv_stage.outputs`.
    """
    from apps.auto_scan_video import giai_doan_ket_xuat as gd

    tt = {"thoi_luong": 179.2, "co_byte": 12345, "codec_video": "h264",
          "codec_tieng": "aac"}
    ra = gd._tom_tat(tt, so_lop_tieng=3, bo_ma_hoa_khai="h264_nvenc",
                     bo_ma_hoa_thuc="libx264", chan_doan="x | y")
    assert ra["bo_ma_hoa_khai"] == "h264_nvenc"
    assert ra["bo_ma_hoa_thuc"] == "libx264"
    assert ra["bo_ma_hoa_bi_ha"] is True, (
        "mot lan HA bo ma hoa ⛔ khong doc duoc tu `outputs`")

    ra2 = gd._tom_tat(tt, so_lop_tieng=3, bo_ma_hoa_khai="h264_nvenc",
                      bo_ma_hoa_thuc="h264_nvenc", chan_doan="")
    assert ra2["bo_ma_hoa_bi_ha"] is False
    # Cac khoa cu ⛔ khong duoc mat
    for k in ("thoi_luong_giay", "co_byte", "codec_video", "codec_tieng",
              "so_lop_tieng", "chan_doan"):
        assert k in ra2, k
