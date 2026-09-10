"""Pha 19 — QC bang AI va ke hoach sua nham dung pham vi nho nhat.

Nam nhom:

  A. Anh xa loai -> giai doan  — "som nhat CO THE", ca hai chieu
  B. Pham vi nho nhat          — mot doan chi duoc lam lai o MOT cho
  C. Do tin                    — model khong chac chan khong sinh viec sua
  D. Tran vong sua             — mot vong tren dich vu tra tien phai co day
  E. Loi nhac / phan hoi       — ghep theo MA, im lang = DAT
"""
from __future__ import annotations

import json

import pytest

from apps.auto_scan_video import qc_ai, sua_chua as sc


# ══════════════════════════════════════════════════════════════════════════════
#  A. Anh xa loai khiem khuyet -> giai doan sua
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_loai_khiem_khuyet_deu_co_giai_doan_sua():
    """Chot theo TAP HOP: them mot loai ma quen anh xa la mo mot duong khong ai
    sua duoc, va no chi lo ra khi mot khach gap dung loai do."""
    assert set(sc.GIAI_DOAN_SUA) == set(sc.LOAI)


def test_doc_sai_sua_o_VOICE_khong_day_nguoc_ve_CONTENT():
    """🔴 Chieu de sai nhat.

    Mot cau bi may doc sai (TTS nuot mot tu) thi **van ban do dang DUNG**. Viet
    lai no la tra tien de doi mot cau dung lay mot cau khac cung dung — roi van
    co the bi doc sai lan nua.
    """
    assert sc.GIAI_DOAN_SUA[sc.DOC_SAI] == "voice_synthesis"
    assert sc.GIAI_DOAN_SUA[sc.KHONG_VUA] == "voice_synthesis"


def test_dich_sai_PHAI_ve_CONTENT_vi_doc_lai_khong_cuu_duoc():
    """Doc lai mot cau dich sai bao nhieu lan cung ra cung mot y sai."""
    assert sc.GIAI_DOAN_SUA[sc.DICH_SAI] == "content_process"


def test_cat_sai_ve_EDIT_PLAN_va_hinh_hong_ve_RENDER():
    assert sc.GIAI_DOAN_SUA[sc.CAT_SAI] == "edit_plan"
    assert sc.GIAI_DOAN_SUA[sc.HINH_HONG] == "render"


def test_loai_khong_co_that_bi_TU_CHOI():
    with pytest.raises(sc.SuaChuaError):
        sc.KhiemKhuyet("loai bia dat", ma="seg_0001")


# ══════════════════════════════════════════════════════════════════════════════
#  B. Pham vi nho nhat an toan
# ══════════════════════════════════════════════════════════════════════════════

def test_mot_doan_bi_HAI_loi_thi_sua_o_giai_doan_SOM_HON():
    """🔴 Menh de trung tam cua nhom B.

    `seg_0001` vua bi bao doc sai (sua o `voice_synthesis`) vua bi bao dich sai
    (sua o `content_process`). Sua o `voice_synthesis` la vo ich: doc lai mot cau
    dich sai van ra mot cau dich sai. Phai sua o cho som hon, va lan doc lai se
    tu den sau no.
    """
    ke = sc.lap_ke_hoach(
        qc_giong=[{"ma": "seg_0001", "chu": "mot hai ba bon", "doc_ra": "mot"}],
        qc_ngu_nghia=[{"ma": "seg_0001", "dat": False, "ly_do": "lech",
                       "do_tin": 0.95}])
    assert sc.gon_theo_don_vi(ke) == {"seg_0001": "content_process"}


def test_doan_CHI_bi_doc_sai_thi_KHONG_bi_day_ve_content():
    """⛔ Chieu nguoc lai. Mot chinh sach chi dung mot chieu la mot chinh sach se
    lam lai viec dung."""
    ke = sc.lap_ke_hoach(
        qc_giong=[{"ma": "seg_0002", "chu": "mot hai ba bon", "doc_ra": "mot"}])
    assert sc.gon_theo_don_vi(ke) == {"seg_0002": "voice_synthesis"}


def test_moi_don_vi_chi_xuat_hien_MOT_lan_trong_ke_hoach_gon():
    ke = sc.lap_ke_hoach(
        qc_giong=[{"ma": "seg_0001", "chu": "a b c", "doc_ra": ""}],
        qc_ngu_nghia=[{"ma": "seg_0001", "dat": False, "do_tin": 0.9},
                      {"ma": "seg_0003", "dat": False, "do_tin": 0.9}],
        qc_hinh=[{"ma_canh": "canh_0002", "dat": False, "do_tin": 0.9}])
    gon = sc.gon_theo_don_vi(ke)
    assert len(gon) == len(set(gon)), "mot don vi bi lam lai o hai cho"
    assert gon["canh_0002"] == "edit_plan"


def test_khong_khiem_khuyet_nao_thi_KHONG_sua_gi():
    ke = sc.lap_ke_hoach()
    assert not ke.can_sua
    assert sc.gon_theo_don_vi(ke) == {}


# ══════════════════════════════════════════════════════════════════════════════
#  C. Do tin
# ══════════════════════════════════════════════════════════════════════════════

def test_do_tin_THAP_thi_GHI_LAI_nhung_KHONG_sinh_viec_sua():
    """⭐ Mot model khong chac chan khong phai mot ly do de tra tien lam lai —
    nhung cung khong phai mot ly do de giau di."""
    ke = sc.lap_ke_hoach(
        qc_ngu_nghia=[{"ma": "seg_0001", "dat": False, "ly_do": "co the lech",
                       "do_tin": 0.3}])
    assert not ke.can_sua
    assert sc.gon_theo_don_vi(ke) == {}
    # ... nhung van co trong ho so.
    d = ke.sang_dict()
    assert len(d["khiem_khuyet"]) == 1
    assert d["khiem_khuyet"][0]["dang_tin"] is False


def test_thieu_do_tin_thi_coi_la_KHONG_dang_tin():
    """⛔ Mac dinh phai la 0, khong phai 1: mot model khong noi no chac chan bao
    nhieu thi ta khong duoc tu gan cho no su chac chan."""
    assert qc_ai._do_tin(None) == 0.0
    assert qc_ai._do_tin("khong phai so") == 0.0
    assert qc_ai._do_tin(1.7) == 1.0
    assert qc_ai._do_tin(-3) == 0.0


def test_phep_DO_co_do_tin_TUYET_DOI_khac_han_phan_doan():
    """QC giong noi la hai chuoi va mot ty le khop — ta khong doan gi ca."""
    ke = sc.lap_ke_hoach(
        qc_giong=[{"ma": "seg_0001", "chu": "mot hai ba", "doc_ra": ""}])
    assert ke.khiem_khuyet[0].do_tin == 1.0
    assert ke.can_sua


# ══════════════════════════════════════════════════════════════════════════════
#  D. Tran vong sua
# ══════════════════════════════════════════════════════════════════════════════

def test_vong_sua_co_TRAN():
    """⛔ Mot vong "sua roi kiem lai" tren nhung dich vu tra tien la mot hoa don
    khong co day."""
    assert sc.VONG_SUA_TOI_DA >= 1
    assert sc.lap_ke_hoach(vong=0).con_vong()
    assert not sc.lap_ke_hoach(vong=sc.VONG_SUA_TOI_DA).con_vong()


def test_tran_vong_sua_CHAT_HON_vong_nan_cua_pha_15():
    """🔑 Hai vong khac ban chat, nen hai tran khac nhau.

    Vong nan (pha 15) sua mot dai luong **DO DUOC** — do dai tieng — nen no hoi
    tu: moi vong dua ket qua gan khe hon. Vong sua nay sua mot **phan doan CHU
    QUAN** cua model; hai lan chay co the cho hai phan doan khac nhau ve cung mot
    cau, va lap them la tra tien de xem model doi y.
    """
    from apps.auto_scan_video.nan_cho_vua import VONG_TOI_DA

    assert sc.VONG_SUA_TOI_DA <= VONG_TOI_DA


# ══════════════════════════════════════════════════════════════════════════════
#  E. Do khop, loi nhac, phan hoi
# ══════════════════════════════════════════════════════════════════════════════

def test_khop_van_ban_bo_qua_dau_cau_va_HOA_THUONG():
    assert qc_ai and sc.khop_van_ban("Xin chao, cac ban!", "xin chao cac ban") == 1.0


def test_khop_van_ban_KHONG_phat_nang_viec_dao_trat_tu():
    """⛔ Mot cau dao hai menh de van la mot cau doc dung ve mat long tieng.
    `SequenceMatcher` tren ca chuoi se cham diem no rat thap."""
    assert sc.khop_van_ban("hom nay troi dep", "troi dep hom nay") == 1.0


def test_khop_van_ban_bat_duoc_viec_NUOT_TU():
    diem = sc.khop_van_ban("mot hai ba bon nam", "mot hai")
    assert diem < sc.NGUONG_KHOP_DOC


def test_hai_chuoi_RONG_thi_KHOP_hoan_toan():
    """Mot doan khong co loi thoai va khong doc ra gi la khop, khong phai lech."""
    assert sc.khop_van_ban("", "") == 1.0
    assert sc.khop_van_ban("co chu", "") == 0.0


def test_doc_ngu_nghia_THIEU_ma_thi_coi_la_DAT():
    """⭐ Mot cau hoi khong duoc tra loi la mot cau hoi khong duoc tra loi. Coi im
    lang la "co loi" se bien moi lan model tra thieu thanh mot lan sua tra tien."""
    ra = qc_ai.doc_ngu_nghia({"doan": {"seg_0001": {"dat": False, "do_tin": 0.9}}},
                             {"seg_0001", "seg_0002"})
    assert [d["ma"] for d in ra] == ["seg_0001"]
    assert sc.lap_ke_hoach(qc_ngu_nghia=ra).giai_doan_sua() == {
        "content_process": ["seg_0001"]}


def test_doc_ngu_nghia_BO_ma_khong_duoc_gui():
    ra = qc_ai.doc_ngu_nghia(
        {"doan": {"seg_0001": {"dat": False, "do_tin": 0.9},
                  "seg_9999": {"dat": False, "do_tin": 0.9}}}, {"seg_0001"})
    assert {d["ma"] for d in ra} == {"seg_0001"}


def test_loi_nhac_ngu_nghia_YEU_CAU_khoa_la_MA():
    msgs = qc_ai.loi_nhac_ngu_nghia([{"ma": "seg_0001", "goc": "a", "chu": "b"}])
    assert '"<ma>"' in msgs[0]["content"]
    goi = json.loads(msgs[-1]["content"])
    assert goi["doan"][0]["ma"] == "seg_0001"


def test_chi_hoi_VLM_o_CHO_NOI_khong_hoi_khap_phim():
    """🔑 Mot canh khong bi dong toi thi khong co gi de hoi ve no. Hoi khap phim
    la tra tien de nghe model xac nhan phan khong bi cham van nguyen ven."""
    from apps.auto_scan_video.ban_do_thoi_gian import BanDoThoiGian

    m = BanDoThoiGian.tu_khoang([(0, 10), (30, 50), (60, 70)],
                                thoi_luong_nguon=70.0)
    assert qc_ai.moc_cho_noi(m) == [10.0, 30.0]
    # Preset giu hinh: mot khoang, khong cho noi nao.
    assert qc_ai.moc_cho_noi(BanDoThoiGian.giu_nguyen(70.0)) == []


def test_loi_nhac_hinh_can_HAI_dau_cua_cho_noi():
    """⛔ Cau hoi la "hai canh nay noi vao nhau co dut mach khong", va no can
    dung hai dau — mot khung khong tra loi duoc cau hoi ve mot chuyen tiep."""
    assert qc_ai.KHUNG_MOI_CHO_NOI >= 2
    with pytest.raises(qc_ai.QcAiError):
        qc_ai.loi_nhac_hinh([], moc_giay=10.0)


def test_chia_lo_doc_hang_so_luc_GOI():
    cu = qc_ai.DOAN_MOI_LO
    try:
        qc_ai.DOAN_MOI_LO = 3
        assert len(qc_ai.chia_lo([{"ma": str(i)} for i in range(9)])) == 3
    finally:
        qc_ai.DOAN_MOI_LO = cu


def test_ke_hoach_sua_doc_lai_duoc_va_co_VAN_TAY():
    ke = sc.lap_ke_hoach(
        qc_ngu_nghia=[{"ma": "seg_0001", "dat": False, "do_tin": 0.9}])
    d = ke.sang_dict()
    assert d["giai_doan_sua"] == {"content_process": ["seg_0001"]}
    assert d["can_sua"] and d["con_vong"]
    assert len(ke.van_tay()) == 32
