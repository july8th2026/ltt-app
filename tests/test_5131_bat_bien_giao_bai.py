"""bat_bien_giao_bai — bat bien o BIEN, spec Sec 8. Nam dieu kien B-1..B-5.

T-1 (spec Sec 10.2, khong duoc thieu): tiem loi cu — canh co 2 anh, ep
refs=[] => PHAI nem. Day chinh la ham chua N-1 (prompt nhac anh ma refs
rong bi tra ve em ru).

Ghi chu ve HAI CACH VIET THE (lech spec/plan, bao dieu phoi): spec Sec 8 ghi
dieu kien B-1 theo dang `@IMG_k`/`@VID_k` (dang cua `taovideo`, xem Sec 6.2
`tag_map`), con `ommi_binding` sinh the dang `@IMAGE_k`/`@VIDEO_k` va plan
Task 7 chi khop hai dang sau. Ham duoi day nhan CA HAI dang va chuan hoa ve
mot khong gian handle duy nhat (`image_k`/`video_k`) — neu chi khop mot dang
thi pha 2 (sau khi doi the sang `@IMG_k`) se khong con dieu kien nao bat, va
N-1 quay lai im lang.
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services.bat_bien import bat_bien_giao_bai


def _refs_du():
    return [{"kind": "image", "url": "data:image/png;base64,AA==",
            "role": "reference_image", "handle": "image_1"},
           {"kind": "image", "url": "data:image/png;base64,BB==",
            "role": "reference_image", "handle": "image_2"}]


def test_hop_le_khong_nem():
    prompt = "Canh mo dau voi @IMAGE_1 va @IMAGE_2 dung canh nhau."
    bat_bien_giao_bai(prompt, _refs_du(), [], has_binding=True)  # khong nem la PASS


def test_T1_tiem_loi_cu_refs_rong_phai_nem():
    """T-1: dung canh co 2 anh (prompt nhac @IMAGE_1/@IMAGE_2), ep refs=[] =>
    phai nem. So 0 khong doi chung khong phai phat hien — day la doi chung."""
    prompt = "Canh mo dau voi @IMAGE_1 va @IMAGE_2 dung canh nhau."
    with pytest.raises(ValueError, match="B-1"):
        bat_bien_giao_bai(prompt, [], [], has_binding=True)


def test_B1_thieu_ref_nhung_co_trong_skipped_thi_hop_le():
    prompt = "Canh co @IMAGE_1 va @IMAGE_2."
    refs = [{"kind": "image", "url": "data:image/png;base64,AA==",
            "role": "reference_image", "handle": "image_1"}]
    skipped = [{"variant_id": "v2", "handle": "image_2", "ly_do": "tep khong ton tai"}]
    bat_bien_giao_bai(prompt, refs, skipped, has_binding=True)  # khong nem


def test_B1_anh_khach_da_xoa_het_khong_lam_do_oan():
    """Bao dong gia la duong dan den viec TAT phep kiem (bai hoc
    `banh-coc-do-cach-go-thay-vi-do-tinh-chat`). Ca hai anh deu bi khach xoa
    => refs RONG nhung ca hai handle nam trong skipped => KHONG duoc nem."""
    prompt = "Canh co @IMAGE_1 va @IMAGE_2."
    skipped = [{"variant_id": "v1", "handle": "image_1", "ly_do": "tep khong ton tai"},
              {"variant_id": "v2", "handle": "image_2", "ly_do": "tep khong ton tai"}]
    bat_bien_giao_bai(prompt, [], skipped, has_binding=True)  # khong nem


def test_B1_dang_the_IMG_cua_taovideo_cung_bi_bat():
    """Spec Sec 8 ghi B-1 theo dang `@IMG_k`. Pha 2 doi the sang dang do; neu
    ham chi khop `@IMAGE_k` thi luoi se IM LANG mo ra."""
    with pytest.raises(ValueError, match="B-1"):
        bat_bien_giao_bai("Canh co @IMG_1 va @IMG_2.", [], [], has_binding=True)
    with pytest.raises(ValueError, match="B-1"):
        bat_bien_giao_bai("Canh co @VID_1.", [], [], has_binding=True)


def test_B1_dang_IMG_trong_prompt_khop_handle_dang_image():
    """Prompt viet `@IMG_1` con ref mang `handle="image_1"` la CUNG mot thu —
    khong duoc nem."""
    refs = [{"kind": "image", "url": "u1", "role": "reference_image",
            "handle": "image_1"}]
    bat_bien_giao_bai("Canh co @IMG_1.", refs, [], has_binding=True)


def test_B2_ref_thua_khong_duoc_prompt_nhac_phai_nem():
    prompt = "Canh chi nhac @IMAGE_1."
    refs = _refs_du()  # co ca image_1 va image_2, prompt khong nhac image_2
    with pytest.raises(ValueError, match="B-2"):
        bat_bien_giao_bai(prompt, refs, [], has_binding=True)


def test_B3_handle_trung_lap_phai_nem():
    prompt = "Canh co @IMAGE_1."
    refs = [{"kind": "image", "url": "u1", "role": "reference_image", "handle": "image_1"},
           {"kind": "image", "url": "u2", "role": "reference_image", "handle": "image_1"}]
    with pytest.raises(ValueError, match="B-3"):
        bat_bien_giao_bai(prompt, refs, [], has_binding=True)


def test_B4_role_anh_khong_hop_le_phai_nem():
    prompt = "Canh co @IMAGE_1."
    refs = [{"kind": "image", "url": "u1", "role": "khong_hop_le", "handle": "image_1"}]
    with pytest.raises(ValueError, match="B-4"):
        bat_bien_giao_bai(prompt, refs, [], has_binding=True)


def test_B4_moi_role_trong_VALID_IMAGE_ROLES_deu_qua():
    """Khong doi chung thi so 0 khong phai phat hien: B-4 phai tu choi role la
    ma KHONG tu choi role that."""
    from apps.taovideo.refs import VALID_IMAGE_ROLES

    for role in sorted(VALID_IMAGE_ROLES):
        refs = [{"kind": "image", "url": "u1", "role": role, "handle": "image_1"}]
        bat_bien_giao_bai("Canh co @IMAGE_1.", refs, [], has_binding=True)


def test_B4_ref_video_khong_bi_bo_gia_tri_role_anh_chan():
    """B-4 chi ap cho `kind == "image"`; ref video co role rieng."""
    refs = [{"kind": "video", "url": "asset://v", "role": "reference_video",
            "handle": "video_1"}]
    bat_bien_giao_bai("Canh co @VIDEO_1.", refs, [], has_binding=True)


def test_B5_co_binding_ma_refs_va_skipped_deu_rong_phai_nem():
    prompt = "Canh khong nhac anh nao ca."
    with pytest.raises(ValueError, match="B-5"):
        bat_bien_giao_bai(prompt, [], [], has_binding=True)


def test_B5_khong_co_binding_thi_refs_rong_la_binh_thuong():
    prompt = "Canh khong nhac anh nao ca."
    bat_bien_giao_bai(prompt, [], [], has_binding=False)  # khong nem


def test_mac_dinh_has_binding_la_False_giu_cho_goi_ba_tham_so():
    """Quyet dinh D-3: cho goi cu ba tham so khong duoc vo."""
    bat_bien_giao_bai("Canh khong nhac anh nao ca.", [], [])
