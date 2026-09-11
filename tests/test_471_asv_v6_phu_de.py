"""ASV V6 pha 14 — phu de: HAI TRUC, TRUC THOI GIAN, va mot be mat lien-app.

🔑 **Ba menh de tep nay chot, va ca ba deu DUONG (khang dinh, khong phu dinh):**

  1. Ho so phu de co HAI truc doc lap — *dot vao hinh* va *xuat `.srt`* — va
     truc thu hai chay duoc o preset giu hinh. Chot bang mot ca CHAY DUOC, chu
     khong bang mot ca bi tu choi: `banh-coc-do-su-vang-mat-thi-xoa-cung-xanh`.

  2. Su kien phu de dung moc cua **ban ra**, khong phai moc cua nguon. Chot
     bang cach doi chieu tung su kien voi `ke_hoach["doan"][i]["dat_tai_ms"]`.

  3. `burn.burn()` KHONG nam trong be mat lien-app duoc phep. Do la lop cuong
     che duy nhat cho quyet dinh *"muon tang tac gia, khong muon tang ma hoa"*.

⛔ **Khong bai nao cham ffmpeg.** Bang chung may that nam o
   `docs/auto_scan_video_v6/bang_chung/phu_de_ass_20260911.json` — no tra loi
   mot cau hoi khac (*"binary co nhan `ass=` khong"*) va no khong thuoc ve mot
   bo test chay hang tram lan mot ngay.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ban_dung, cai_dat, che_do_render as cdr,
                                  hop_dong_v4 as hd, ket_xuat, loi, phu_de,
                                  thoi_gian, van_ban)

PRESET_CAT = hd.PRESET_CAT_THONG_MINH
PRESET_GIU = hd.PRESET_GIU_HINH


# ── Du lieu do CHINH nguoi san xuat sinh ra ─────────────────────────────────
#
# ⚠️ `van_ban.kiem` va `thoi_gian.kiem` duyet chung o duoi. Mot dict ta tu bia
#    ra chi do duoc su nhat quan cua ta voi chinh ta — ban dau cua cau noi da
#    xanh dung nhu the trong khi no doc **nguoc** ca hai khoa.

MUC = [
    {"ma": "s1", "bat": 0.0, "ket": 4.0,
     "chu": "Xin chao cac ban, hom nay chung ta noi ve mot chu de rat thu vi"},
    {"ma": "s2", "bat": 5.0, "ket": 9.0, "chu": "Doan hai ngan hon"},
    {"ma": "s3", "bat": 10.0, "ket": 14.0, "chu": "Doan ba"},
]


@pytest.fixture(scope="module")
def tai_lieu() -> dict:
    tl = {"schema": van_ban.SCHEMA_VAN_BAN, "muc": MUC}
    van_ban.kiem(tl)
    return tl


@pytest.fixture(scope="module")
def ke_hoach() -> dict:
    kh = thoi_gian.lap_ke_hoach(
        MUC, {"s1": 3.0, "s2": 3.5, "s3": 2.0}, tong_giay=15.0)
    thoi_gian.kiem(kh)
    return kh


def _ho_so(**kw) -> dict:
    return phu_de.chuan_hoa(kw)


# ══ 1. HAI TRUC ═════════════════════════════════════════════════════════════

def test_chi_xuat_srt_la_mot_ho_so_HOP_LE_khong_phai_None():
    """⭐ Menh de DUONG: to hop *chi xuat SRT* dien dat duoc.

    Ban nhap dau tra `None` ngay khi `che_do == tat`, **truoc khi** doc
    `xuat_srt` — nen to hop nay khong ton tai. Cai bi mat khong bao loi.
    """
    ho = _ho_so(che_do="tat", xuat_srt=True)
    assert ho is not None
    assert ho["xuat_srt"] is True
    assert phu_de.co_dot_vao_hinh(ho) is False


def test_khong_dot_va_khong_srt_thi_KHONG_ghi_khoa_nao():
    """⛔ Cung luat `cat_dau_cuoi` L4: khong dung gi thi khong ghi gi."""
    assert _ho_so(che_do="tat") is None
    assert _ho_so() is None
    assert phu_de.chuan_hoa(None) is None


def test_ho_so_chi_srt_KHONG_lam_ban_dung_doi_diem_anh():
    c = cai_dat.tu_ho_so({"phu_de": _ho_so(che_do="tat", xuat_srt=True)})
    assert c.co_sua_diem_anh is False, (
        "mot ho so chi xuat SRT bi doi xu nhu mot bien doi diem anh — no se bi "
        "cam o preset giu hinh, dung noi ma no la lua chon DUY NHAT con lai")


def test_ho_so_dot_thi_CO_doi_diem_anh():
    c = cai_dat.tu_ho_so({"phu_de": _ho_so(che_do="tu_dong", kieu="default")})
    assert c.co_sua_diem_anh is True


@pytest.mark.parametrize("che_do", [phu_de.CHE_DO_TU_DONG,
                                    phu_de.CHE_DO_TU_CHON])
def test_ha_ve_srt_giu_truc_srt_va_bo_truc_dot(che_do):
    ho = _ho_so(che_do=che_do, kieu="default", xuat_srt=True)
    ra = phu_de.ha_ve_srt(ho)
    assert ra is not None, "ca ho so bi vut — truc `.srt` da bi go theo"
    assert ra["xuat_srt"] is True
    assert phu_de.co_dot_vao_hinh(ra) is False
    assert "kieu" not in ra, "`.srt` khong mang kieu chu nao"


def test_ha_ve_srt_luy_dang():
    ho = _ho_so(che_do="tu_dong", kieu="default", xuat_srt=True)
    mot = phu_de.ha_ve_srt(ho)
    assert phu_de.ha_ve_srt(mot) == mot


def test_ha_ve_srt_tra_None_khi_chi_xin_dot():
    assert phu_de.ha_ve_srt(_ho_so(che_do="tu_dong", kieu="default")) is None


# ══ 2. CUA HTTP ═════════════════════════════════════════════════════════════

def test_tu_form_chan_DOT_o_preset_giu_hinh():
    with pytest.raises(phu_de.PhuDeLoi):
        phu_de.tu_form(json.dumps({"che_do": "tu_dong", "kieu": "default"}),
                       preset=PRESET_GIU)


def test_tu_form_NHAN_srt_o_preset_giu_hinh():
    """⭐ Ca CHAY DUOC — day moi la bai chot menh de hai truc.

    Mot bai chi kiem *"dot bi tu choi"* van xanh khi ai do sua thanh tu choi
    TAT CA phu de o preset nay. Bai nay do se khong.
    """
    ra = phu_de.tu_form(json.dumps({"che_do": "tat", "xuat_srt": True}),
                        preset=PRESET_GIU)
    assert ra and ra["xuat_srt"] is True


@pytest.mark.parametrize("goi,cum", [
    ({"che_do": "khong-co"}, "Chế độ"),
    ({"che_do": "tu_dong", "kieu": "khong-co"}, "Kiểu"),
    ({"che_do": "tu_dong", "phan_doan": "khong-co"}, "chia dòng"),
])
def test_moi_loi_co_cau_tra_loi_RIENG(goi, cum):
    """🔴 `PhuDeLoi` ke thua `ValueError`.

    Mot `except (ValueError, TypeError)` bao quanh ca doc lan duyet se nuot cau
    tra loi cu the roi boc lai thanh *"khong doc duoc"* — khach go sai mot id
    kieu chu se khong biet minh vua lam gi sai.
    """
    with pytest.raises(phu_de.PhuDeLoi) as e:
        phu_de.tu_form(json.dumps(goi), preset=PRESET_CAT)
    assert cum in str(e.value), str(e.value)


def test_tu_form_rong_tra_None():
    assert phu_de.tu_form("", preset=PRESET_CAT) is None
    assert phu_de.tu_form("   ", preset=PRESET_GIU) is None


def test_PhuDeLoi_xep_loai_NGUOI_DUNG():
    """⛔ `NGUOI_DUNG` = **that bai cuoi cung, dung thu lai**.

    Mot kieu chu khong con ton tai se nem giua giai doan ket xuat; ba luot
    `retry` deu hong y het, moi luot ton mot suat render.
    """
    assert loi.phan_loai(phu_de.PhuDeLoi("x")) == loi.NGUOI_DUNG


# ══ 3. TRUC THOI GIAN ═══════════════════════════════════════════════════════

def test_su_kien_dung_moc_cua_BAN_RA_khong_phai_cua_NGUON(ke_hoach, tai_lieu):
    """🔴 Bai quan trong nhat cua tep nay.

    `loc_cat_noi` CAT cac khoang giu roi NOI chung, nen giay 180 cua nguon co
    the la giay 74 cua ban ra — hoac khong ton tai. Bo loc `ass=` doc moc TUYET
    DOI, nen `.ass` phai dung tu `ke_hoach`, noi `dat_tai_ms` DA di qua
    `ban_do.ra()`.
    """
    sk = phu_de.su_kien_tu_ke_hoach(ke_hoach, tai_lieu)
    assert len(sk) == len(ke_hoach["doan"]) > 0
    for e, d in zip(sk, ke_hoach["doan"], strict=True):
        assert e.scene_id == d["ma"]
        assert e.start == pytest.approx(d["dat_tai_ms"] / 1000.0)
        assert e.end == pytest.approx(
            (d["dat_tai_ms"] + d["dai_ms"]) / 1000.0)


def test_moc_cua_ke_hoach_KHAC_moc_cua_nguon(ke_hoach, tai_lieu):
    """⭐ Doi chung cho bai tren: neu hai truc trung nhau thi bai kia vo nghia.

    Doan `s2` bat o giay 5,0 cua nguon nhung tieng cua no chi dai 3,5 giay, nen
    ke hoach dat no o mot moc khac. Neu mot ngay nao do hai truc trung khop het
    thi bai tren khong con phan biet duoc gi — va bai nay se DO de noi dieu do.
    """
    sk = phu_de.su_kien_tu_ke_hoach(ke_hoach, tai_lieu)
    theo_nguon = [m["ket"] - m["bat"] for m in MUC]
    theo_ra = [e.end - e.start for e in sk]
    assert theo_ra != pytest.approx(theo_nguon), (
        "do dai tren hai truc trung khop het — bai `dung_moc_cua_BAN_RA` khong "
        "con phan biet duoc gi")


def test_doi_hai_tai_lieu_cho_nhau_thi_KHONG_su_kien_nao(ke_hoach, tai_lieu):
    """⚠️ Ke hoach dung khoa `doan`, van ban dung khoa `muc` — khong phai loi
       danh may. Ban dau doc **nguoc ca hai** va van xanh, vi phep kiem khi do
       dung mot dict do chinh no bia ra.
    """
    assert phu_de.su_kien_tu_ke_hoach(tai_lieu, ke_hoach) == []


def test_muc_khong_co_chu_bi_bo_qua(ke_hoach):
    """Mot doan chua dich xong khong duoc thanh mot o phu de rong nhap nhay."""
    assert phu_de.su_kien_tu_ke_hoach(ke_hoach, {"muc": []}) == []


def test_goi_va_su_kien_di_ve_BAT_DONG(ke_hoach, tai_lieu):
    goi = phu_de.su_kien_ra_goi(
        phu_de.su_kien_tu_ke_hoach(ke_hoach, tai_lieu))
    assert phu_de.su_kien_ra_goi(phu_de.goi_ra_su_kien(goi)) == goi


def test_ngat_toi_da_hai_dong(ke_hoach, tai_lieu):
    sk = phu_de.su_kien_tu_ke_hoach(ke_hoach, tai_lieu)
    assert max(e.line_count for e in sk) <= phu_de.SO_DONG_TOI_DA
    assert any(e.line_count == 2 for e in sk), (
        "khong su kien nao bi ngat dong — bai kiem tran dong dang xanh-rong")


# ══ 4. SINH TEP ═════════════════════════════════════════════════════════════

def _goi(ke_hoach, tai_lieu):
    return phu_de.su_kien_ra_goi(
        phu_de.su_kien_tu_ke_hoach(ke_hoach, tai_lieu))


def test_hai_truc_sinh_hai_tep_DOC_LAP(tmp_path, ke_hoach, tai_lieu):
    goi = _goi(ke_hoach, tai_lieu)
    dot = _ho_so(che_do="tu_dong", kieu="default")
    srt = _ho_so(che_do="tat", xuat_srt=True)
    ca_hai = _ho_so(che_do="tu_chon", kieu="default", xuat_srt=True)

    assert phu_de.viet_tep_ass(dot, goi, tmp_path, rong=1920, cao=1080)
    assert not phu_de.viet_tep_srt(dot, goi, tmp_path)
    assert not phu_de.viet_tep_ass(srt, goi, tmp_path)
    assert phu_de.viet_tep_srt(srt, goi, tmp_path)
    assert phu_de.viet_tep_ass(ca_hai, goi, tmp_path, rong=1920, cao=1080)
    assert phu_de.viet_tep_srt(ca_hai, goi, tmp_path)


def test_kich_thuoc_khung_DI_VAO_tep_ass(tmp_path, ke_hoach, tai_lieu):
    """⚠️ `build_ass` tinh co chu va le theo `video_width/height`, mac dinh
       1920x1080. Ap mac dinh do len mot video DOC cho ra phu de nho bang mot
       phan ba va dat sai le — **khong bao mot loi nao**.
    """
    goi = _goi(ke_hoach, tai_lieu)
    ho = _ho_so(che_do="tu_dong", kieu="default")
    doc = Path(phu_de.viet_tep_ass(ho, goi, tmp_path / "d", rong=1080,
                                   cao=1920)).read_text("utf-8")
    assert "PlayResX: 1080" in doc and "PlayResY: 1920" in doc


def test_moc_trong_tep_ass_la_moc_cua_ban_ra(tmp_path, ke_hoach, tai_lieu):
    """Doi chieu tep DA GHI voi ke hoach — khong dung lai o doi tuong Python."""
    goi = _goi(ke_hoach, tai_lieu)
    van = Path(phu_de.viet_tep_ass(_ho_so(che_do="tu_dong", kieu="default"),
                                   goi, tmp_path, rong=1920, cao=1080)
               ).read_text("utf-8")
    dong = [d for d in van.splitlines() if d.startswith("Dialogue:")]
    assert len(dong) == len(ke_hoach["doan"])

    def _giay(ts: str) -> float:
        g, p, s = ts.split(":")
        return int(g) * 3600 + int(p) * 60 + float(s)

    for d, kh in zip(dong, ke_hoach["doan"], strict=True):
        bat = _giay(d.split(",")[1])
        assert bat == pytest.approx(kh["dat_tai_ms"] / 1000.0, abs=0.01)


def test_khong_su_kien_thi_KHONG_sinh_tep(tmp_path):
    """⭐ Mot `.ass` rong van la mot `ass=` hop le: no chay, khong che gi, va
       ton mot vong giai ma. Tra `""` de `ket_xuat` bo han mat xich do.
    """
    ho = _ho_so(che_do="tu_dong", kieu="default")
    assert phu_de.viet_tep_ass(ho, [], tmp_path, rong=1920, cao=1080) == ""
    assert phu_de.viet_tep_srt(_ho_so(che_do="tat", xuat_srt=True), [],
                               tmp_path) == ""


def test_kieu_khong_ton_tai_bi_NEM_o_tang_sinh_tep(tmp_path, ke_hoach,
                                                   tai_lieu):
    """🔴 `style_registry.get_config` ROI VE `default` khi id la.

    Voi `autosubvideo` do la lua chon hop ly. Voi ASV thi khong: khach chon mot
    kieu, mot id cu di qua, va ho nhan `default` ma khong ai noi gi.
    """
    xau = {"che_do": "tu_dong", "kieu": "kieu-khong-bao-gio-ton-tai",
           "xuat_srt": False, "phan_doan": "sentence"}
    with pytest.raises(phu_de.PhuDeLoi):
        phu_de.viet_tep_ass(xau, _goi(ke_hoach, tai_lieu), tmp_path,
                            rong=1920, cao=1080)


# ══ 5. CHUOI LOC + VAN TAY ══════════════════════════════════════════════════

def test_ass_la_mat_xich_CUOI_cua_chuoi_loc():
    """⭐ Phu de nam tren ca logo va lop phu: no la thu khach doc de HIEU. Mot
       phu de bi che la mot tinh nang khong ton tai.
    """
    chuoi = cdr.loc_cat_noi([(0.0, 5.0)], duong_ass="C:/tam/a.ass")
    cuoi = chuoi.split(";")[-1]
    assert "ass='" in cuoi and cuoi.endswith("[ra]"), chuoi


def test_khong_duong_ass_thi_chuoi_loc_KHONG_co_ass():
    assert "ass=" not in cdr.loc_cat_noi([(0.0, 5.0)])


def test_duong_dan_windows_duoc_THOAT_trong_chuoi_loc():
    """⚠️ `ass=` doc tep truc tiep. Mot `:` chua thoat lam ffmpeg tu choi ca
       chuoi loc — cung ly do `textfile=` phai di qua `lop_phu.thoat_duong`.
    """
    chuoi = cdr.loc_cat_noi([(0.0, 5.0)], duong_ass=r"C:\Temp\asv\phu de.ass")
    assert "C\\:/Temp/asv/phu de.ass" in chuoi, chuoi


def test_doi_ho_so_phu_de_thi_van_tay_che_do_DOI():
    """🔑 Thieu buoc nay thi mot lan chay CO phu de va mot lan KHONG dung chung
       van tay — hai ket qua khac nhau, mot chuoi bam, va lan thu hai duoc phuc
       vu tu cache.
    """
    chung = dict(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
                 khoang=[(0.0, 5.0)])
    khong = cdr.van_tay_che_do(**chung)
    dot = cdr.van_tay_che_do(**chung,
                             phu_de=_ho_so(che_do="tu_dong", kieu="default"))
    srt = cdr.van_tay_che_do(**chung, phu_de=_ho_so(che_do="tat",
                                                    xuat_srt=True))
    assert len({khong, dot, srt}) == 3


def test_phien_ban_che_do_da_len_6():
    """⭐ Phu de dot vao hinh la mot bien doi DIEM ANH moi trong chuoi loc, nen
       moi ban dung cu phai duoc coi la mot quyet dinh render KHAC.
    """
    assert cdr.PHIEN_BAN_CHE_DO >= 6


# ══ 6. BAN DUNG ═════════════════════════════════════════════════════════════

def _ban(preset: str, ho_so):
    cach = (cdr.SAO_CHEP if preset == PRESET_GIU else cdr.CAT_MA_HOA_LAI)
    return ban_dung.dung(
        khoa_video="v/goc.mp4", khoa_nen="nhac/nen.wav",
        khoa_master="mix/master.m4a",
        ke_hoach={"doan": [{"ma": "s1", "dai_ms": 2000, "dat_tai_ms": 0,
                            "he_so_toc": 1.0}]},
        ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "v/s1.wav"}]},
        phien_ban_ffmpeg="n7.1", tong_giay=2.0, che_do=cach,
        bo_ma_hoa="libx264" if cach == cdr.CAT_MA_HOA_LAI else "",
        khoang_giu=[(0.0, 2.0)] if cach == cdr.CAT_MA_HOA_LAI else None,
        preset=preset, rong_khung=1920, cao_khung=1080, phu_de=ho_so)


def test_ban_dung_CHAP_NHAN_dot_o_preset_cat():
    ban = _ban(PRESET_CAT, _ho_so(che_do="tu_dong", kieu="default"))
    ban_dung.kiem(ban)
    assert ban["hinh"]["phu_de"]["che_do"] == "tu_dong"


def test_ban_dung_TU_CHOI_dot_o_preset_giu_hinh():
    with pytest.raises(ban_dung.BanDungError) as e:
        ban_dung.kiem(_ban(PRESET_GIU,
                           _ho_so(che_do="tu_dong", kieu="default")))
    assert "Phụ đề" in str(e.value), (
        "cau tu choi khong noi ve phu de — khach vua bat ba tinh nang se phai "
        "doan minh lam gi sai")


def test_ban_dung_CHAP_NHAN_srt_o_preset_giu_hinh():
    """⭐ Ca CHAY DUOC o preset giu hinh. Doi chung cho bai tren."""
    ban = _ban(PRESET_GIU, _ho_so(che_do="tat", xuat_srt=True))
    ban_dung.kiem(ban)
    assert ban["hinh"]["phu_de"]["xuat_srt"] is True


def test_ban_dung_khong_phu_de_van_hop_le():
    ban_dung.kiem(_ban(PRESET_GIU, None))
    assert _ban(PRESET_GIU, None)["hinh"]["phu_de"] is None


def test_ket_xuat_truyen_duong_ass_vao_lenh():
    ban = _ban(PRESET_CAT, _ho_so(che_do="tu_dong", kieu="default"))
    cmd = ket_xuat.dung_lenh(
        ban, ffmpeg_bin="ffmpeg", duong_video="C:/t/g.mp4",
        duong_master="C:/t/m.wav", duong_lop=["C:/t/0.wav"],
        duong_ra="C:/t/r.mp4", bo_ma_hoa="libx264",
        duong_ass="C:/t/phu_de.ass")
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "ass='C\\:/t/phu_de.ass'" in fc, fc


# ══ 7. HOP DONG + BE MAT LIEN-APP ═══════════════════════════════════════════

def _lint_module():
    import importlib.util

    goc = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "_lint_pha14", goc / "tools" / "lint_app_contract.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_subtitle_burn_da_roi_khoi_vung_cam():
    assert "subtitle_burn" in hd.NANG_LUC_DOI_DIEM_ANH
    assert "subtitle_burn" not in hd.CAM_TRONG_MVP
    assert "subtitle_burn" not in hd.HAU_MVP


def test_subtitle_srt_o_bang_KHONG_doi_diem_anh():
    """⛔ Gop hai bang lam mot se khoa mat lua chon phu de duy nhat con lai o
       preset giu hinh — va cai bi mat khong bao loi, no chi khong ton tai.
    """
    assert "subtitle_srt" in hd.NANG_LUC_KHONG_DOI_DIEM_ANH
    assert "subtitle_srt" not in hd.NANG_LUC_DOI_DIEM_ANH


def test_be_mat_lien_app_KHONG_gom_burn():
    """🔴 Lop cuong che DUY NHAT cho quyet dinh kien truc cua ca pha.

    `burn.burn()` chay mot luot ffmpeg DAY DU cua rieng no — video bi ma hoa
    lai HAI lan. Neu mot phien sau goi no de "tai dung cho nhanh", linter chan
    ngay; khong co dong nay thi khoan no chay im lang toi pha 26.
    """
    cho_phep = _lint_module().APP_DUOC_DUNG_APP[
        ("auto_scan_video", "autosubvideo")]
    ten = {n for _, n in cho_phep}
    assert {"build_ass", "build_srt", "get_config", "list_ids"} <= ten
    assert not any("burn" in str(x).lower() for x in cho_phep), cho_phep


def test_be_mat_duoc_khai_o_CA_HAI_phia():
    """⚠️ Hai phia sua duoc doc lap, nen mot phia thieu la mot cua da mo ma
       chua ai khai — hoac mot ban khai cho mot cua khong ton tai.
    """
    from apps import autosubvideo

    cho_phep = _lint_module().APP_DUOC_DUNG_APP[
        ("auto_scan_video", "autosubvideo")]
    assert cho_phep <= autosubvideo.BE_MAT_CONG_KHAI


# ══ 8. GIAO DIEN ════════════════════════════════════════════════════════════

def test_danh_sach_kieu_den_TU_style_registry():
    """⛔ Khong go danh sach kieu vao template. Mot ban sao trong HTML troi ngay
       lan dau app kia them mot kieu, va troi IM LANG.
    """
    from apps.autosubvideo.style_registry import list_ids

    g = phu_de.cho_giao_dien()
    assert [ma for ma, _t, _d in g["kieu"]] == list(list_ids())
    assert phu_de.KIEU_MAC_DINH in {m for m, _t, _d in g["kieu"]}


def test_che_do_cho_giao_dien_khop_hang_so():
    g = phu_de.cho_giao_dien()
    assert [ma for ma, _t, _d in g["che_do"]] == list(phu_de.CHE_DO)


def test_giao_dien_khong_hien_id_tho_cho_khach():
    """`tiktok_bold` la mot dinh danh cho MA doc, khong phai mot cai ten."""
    for ma, ten, _d in phu_de.cho_giao_dien()["kieu"]:
        assert ten and ten != ma, (ma, ten)


def test_module_js_da_dang_ky_cache_bust():
    """⭐ Them tep tinh MOI ma khong dinh version: nguoi dung nhan ban cu toi khi
       het TTL cua Cloudflare (4 gio), va origin thi da dung.
    """
    from server import templating

    assert "asv/phu_de.js" in templating.ASV_STUDIO_JS
    assert "asv/phu_de.js" in templating.TAI_SAN_CO_VERSION
    assert templating.ASV_STUDIO_JS[0] == "asv/nen.js", (
        "`nen.js` phai nap dau — cac module kia doc `window.ASV`")


def test_o_srt_trong_template_KHONG_bi_an_theo_preset():
    """🔴 O `.srt` la lua chon phu de DUY NHAT con lai o preset giu hinh. An no
       theo preset la khoa mat tinh nang, va khoa **im lang**.
    """
    goc = Path(__file__).resolve().parents[1]
    html = (goc / "apps/auto_scan_video/templates/asv_trang_chinh.html"
            ).read_text("utf-8")
    i_srt = html.index('id="asv-phu-de-srt"')
    nhan = html.rindex("<label", 0, i_srt)
    assert "hidden" not in html[nhan:i_srt], html[nhan:i_srt]
