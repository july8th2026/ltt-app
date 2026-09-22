"""Auto Scan Video V4 — the product contract, as something a machine can check.

`docs/auto_scan_video/MVP_CONTRACT.md` froze a **dubbing-only** product and said so in
plain words: *"It is not an editor."* V4 supersedes that with a two-preset
smart-localization editor (`ADR-V4-001`).

A superseded document does not stay superseded on its own. The failure mode this file
exists to prevent is not someone arguing against V4 — it is a later session reading the
older, longer, more confident document, finding no machine-checkable trace of the newer
decision, and quietly restoring the narrower behaviour. Phase 01's brief calls this out
by name: *"Add contract tests so old dubbing-only restriction cannot silently reassert
itself."*

Three layers, deliberately different in kind:

**§1** pins the declaration itself (`apps/auto_scan_video/hop_dong_v4.py`).
**§2** pins the *link between documents*, which is the part a code-only test cannot see.
**§3** is a strict-xfail RED target: the contract promises two presets, and the executable
       pipeline currently knows about none. It goes green in Phase 12 and must be un-marked
       there, or the gate says so.

⚠️ §1 alone would be close to a tautology — constants asserting their own values. It earns
   its place only because §2 and §3 tie those constants to things outside this file.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from apps.auto_scan_video import hop_dong_v4 as hd

GOC = Path(__file__).resolve().parent.parent
CONTRACT_V2 = GOC / "docs" / "auto_scan_video" / "MVP_CONTRACT.md"
ADR_V4 = (GOC / "docs" / "auto_scan_video_v4" / "adr"
          / "ADR-V4-001-hop-dong-san-pham.md")


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Ban khai — hai preset, mot ngon ngu, hai che do giong
# ══════════════════════════════════════════════════════════════════════════════

def test_dung_HAI_preset_va_ten_dung_nhu_hop_dong():
    """G16 doi giao dien lo dung hai preset. Ten la hop dong, khong phai nhan."""
    assert hd.PRESET == ("localize_preserve_picture", "smart_localize")
    assert hd.PRESET_MAC_DINH == "localize_preserve_picture"


def test_preset_giu_hinh_KHONG_duoc_phep_cat():
    """G10: *"`localize_preserve_picture` cannot cut"*.

    ⭐ Chot vao tuple RONG chu khong vao `not in`. Neu bang thao tac vang han
       khoa nay, `THAO_TAC_CHO_PHEP[...]` nem KeyError va phep kiem do vi ly do
       khac — nhung no van do, va do la dieu quan trong: "chua khai" khong duoc
       phep im lang tro thanh "duoc phep".
    """
    assert hd.THAO_TAC_CHO_PHEP[hd.PRESET_GIU_HINH] == ()


def test_preset_thong_minh_CHI_giu_hoac_cat():
    """MVP smart editing bi rang buoc co y: khong reorder, khong reframe."""
    assert set(hd.THAO_TAC_CHO_PHEP[hd.PRESET_CAT_THONG_MINH]) == {"keep", "cut"}


@pytest.mark.parametrize("thao_tac", ["reorder", "reframe", "crop", "zoom",
                                      "broll", "transition"])
def test_thao_tac_bi_cam_khong_xuat_hien_o_bat_ky_preset_nao(thao_tac):
    """`reorder` nam trong danh sach CAM chu khong chi vang mat.

    🔑 Vang mat va bi cam trong giong het nhau tu ben ngoai. Chi cai thu hai
       song sot qua mot phien sau "them thao tac con thieu".
    """
    assert thao_tac in hd.CAM_TRONG_MVP
    for ten, duoc_phep in hd.THAO_TAC_CHO_PHEP.items():
        assert thao_tac not in duoc_phep, ten


def test_ngon_ngu_dich_la_vi_va_en_mac_dinh_vi():
    """Chu du an chot 22/09 (asv-final): dich {vi, en}; ho so cu = `vi`."""
    assert hd.NGON_NGU_DICH == "vi"
    assert hd.NGON_NGU_DICH_HOP_LE == ("vi", "en")


def test_tap_dich_CHINH_LA_tap_lan_giong_cua_ltt_voice():
    """🔑 Truoc 22/09 phep kiem nay chot dieu nguoc lai: *"TTS lam duoc, ta van
    co y khong lam"* (D-V4-02), vi chuoi hieu-va-dich chua co bang chung `en`.

    Chu du an mo `en` ngay 22/09. Bang chung ma D-V4-02 doi — mot lan chay THAT
    `vi→en` qua ASR, dich, giong, QC — la muc bat buoc cua cong ra
    `docs/auto_scan_video_final/` (FINAL_REAL_JOB_REPORT), khong phai o day.

    ⇒ Nay phep kiem chot: dich KHONG vuot tap lan giong. Mot dich khong co lan
      giong la mot ban long tieng khong ai doc duoc.
    """
    from apps.ltt_voice.lan_ngon_ngu import NHAN_LAN

    assert set(NHAN_LAN) == {"vi", "en"}, (
        "LTT Voice doi lan ngon ngu — doc lai ngon_ngu.py truoc khi sua so nay")
    assert set(hd.NGON_NGU_DICH_HOP_LE) <= set(NHAN_LAN)


def test_hai_che_do_giong_va_auto_match_khong_phai_gia_tri_mac_dinh():
    """AUTO_MATCH phai doc dac diem nguoi noi, khong phai bo trong o form.

    V2 lo `giong_id: str = Form("")` va coi rong = giong mac dinh nen tang. Do
    la mot thu KHAC: mot gia tri mac dinh khong doc gi tu video ca.
    """
    assert hd.CHE_DO_GIONG == ("USER_SELECTED", "AUTO_MATCH")
    assert hd.CHE_DO_GIONG_MAC_DINH == "USER_SELECTED"
    assert "" not in hd.CHE_DO_GIONG


def test_qc_chan_duoc_viec_giao_hang():
    """Mot cong khong chan duoc thi te hon khong co cong — no trong giong co.

    V2 pha 18 ship dung loi do (`danh_dau_xong` chay truoc `raise`) va tu bat
    duoc trong bao cao cua chinh no.
    """
    assert hd.GIAO_KHI_QC_HONG is False


def test_khong_preset_nao_duoc_lam_video_dai_ra():
    assert hd.DUNG_SAI_DO_DAI_S == 0.50


def test_hop_dong_tu_no_luc_nap_neu_mau_thuan(monkeypatch):
    """Chot noi tai phai THAT SU no, khong chi ton tai.

    ⭐ Khong co phep kiem nay thi `_kiem_tra_hop_dong()` co the la mot ham rong
       va moi thu van xanh. Day la phien ban "tu kiem tra do bat duoc" ma
       `test_401` dung cho cac guard cua no.
    """
    monkeypatch.setattr(hd, "THAO_TAC_CHO_PHEP",
                        {hd.PRESET_GIU_HINH: ("cut",),
                         hd.PRESET_CAT_THONG_MINH: ("keep", "cut")})
    with pytest.raises(ValueError, match="khong duoc phep co thao tac"):
        hd._kiem_tra_hop_dong()


def test_hau_mvp_khong_rong_va_khong_chan_release():
    """Danh sach hoan phai la mot DANH SACH, khong phai mot cam giac."""
    assert hd.HAU_MVP
    assert "reframe" in hd.HAU_MVP
    assert "multilingual_target" in hd.HAU_MVP
    # Thu da hoan thi khong duoc dong thoi la thu bat buoc.
    for muc in hd.HAU_MVP:
        for duoc_phep in hd.THAO_TAC_CHO_PHEP.values():
            assert muc not in duoc_phep


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Rang buoc GIUA HAI TAI LIEU — phan mot phep kiem tren code khong thay
# ══════════════════════════════════════════════════════════════════════════════

def test_hop_dong_V2_mang_bang_chi_duong_toi_ADR_V4():
    """⛔ Phep kiem quan trong nhat trong tep nay.

    `MVP_CONTRACT.md` dai 245 dong, tu tin, va noi "It is not an editor". Mot
    phien sau doc no truoc — no la tai lieu duy nhat trong `docs/auto_scan_video/`
    tu goi minh la FROZEN.

    Neu ban ADR V4 bi go, bi doi ten, hoac bang chi duong bi xoa "cho gon", phep
    kiem nay do **truoc khi** ai do bat dau viet lai code theo hop dong cu.
    """
    assert CONTRACT_V2.exists()
    van_ban = CONTRACT_V2.read_text(encoding="utf-8")
    assert "ADR-V4-001" in van_ban, (
        "MVP_CONTRACT.md mat bang chi duong toi ADR-V4-001 — hop dong cu dang "
        "tu khang dinh lai")
    assert "SUPERSEDED" in van_ban


def test_ADR_V4_ton_tai_va_khai_ro_no_thay_the_cai_gi():
    assert ADR_V4.exists(), "ADR-V4-001 bien mat"
    van_ban = ADR_V4.read_text(encoding="utf-8")
    assert "auto_scan_mvp_v1" in van_ban
    assert "smart_localize" in van_ban
    assert "localize_preserve_picture" in van_ban


def test_van_giu_nguyen_phan_KHONG_bi_thay_the_cua_hop_dong_cu():
    """V4 thay the muc 1 va 4, KHONG thay the phan con lai.

    ⚠️ Chieu nay de bi bo quen. Danh sach dung sai T1–T12, chinh sach dau vao va
       mo hinh thoi gian ADR-003 deu duoc ke thua nguyen ven — mat chung di thi
       pha 18/19 phai phat minh lai nguong, va "phat minh lai nguong" la cach
       mot QC gate mat rang.
    """
    van_ban = CONTRACT_V2.read_text(encoding="utf-8")
    for moc in ("T1", "T12", "ADR-003", "−14 LUFS", "±0.50 s"):
        assert moc in van_ban, f"hop dong cu mat muc con hieu luc: {moc}"


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Muc tieu DO co chu y — pha 12 phai lam xanh VA go nhan nay
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.xfail(strict=True, reason=(
    "Pha 12 so huu. Hop dong khai hai preset; `pipeline.CHUOI` chua biet preset "
    "nao ca. Khi pha 12 lam xanh, PHAI go nhan xfail nay — strict=True lam gate "
    "do neu khong go, nen loi hua khong the nam yen o dang mot dong tai lieu."))
def test_chuoi_thi_hanh_biet_den_preset():
    """Hop dong khong tu chay. Mot ban khai khong co duong thi hanh la mot loi hua.

    Hom nay `pipeline.py` khong nhac toi preset o bat ky dau — no la chuoi 9 giai
    doan co dinh cua V2, va ca hai preset se di qua no khac nhau (giu hinh thi
    `render` sao chep; cat thong minh thi `render` ma hoa lai tai diem cat).
    """
    from apps.auto_scan_video import pipeline

    nguon = Path(pipeline.__file__).read_text(encoding="utf-8")
    assert hd.PRESET_CAT_THONG_MINH in nguon
