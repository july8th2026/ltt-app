"""Pha 05.1 — điểm nối canonical cho LLM nội bộ, và MỆNH ĐỀ PHỦ ĐỊNH của nó.

⭐ Mệnh đề phủ định là loại dễ mất nhất: **không ai nhớ một thứ không tồn tại.**
   Nên nó phải là một lệnh chạy được, không phải một dòng chú thích.
"""
from __future__ import annotations

import pytest

from platform_core.llm import canonical as C


def test_khong_bi_danh_nao_anh_xa_VE_CHINH_NO():
    """🔴 Chốt đúng cái lỗi đã mắc HAI lần trong kho này.

    Lần một: `apps/ltt_llm/features.py` từng đặt `ltt_llm -> ltt_llm`, xoá sạch
    lớp đệm bí danh. `test_no_vendor_model_id_reaches_a_customer_surface` bắt
    được và nó được sửa **ở đó**.

    Lần hai: docstring của `dieu_phoi.goi` vẫn dạy
    `model_theo_provider={"ltt_llm": "ltt_llm"}`, và **đã dạy sai hai nơi chép
    theo**. Hậu quả không phải một lỗi ồn ào mà là một sự im lặng:
    `api_pool.chon_key(model="ltt_llm")` ném `ThieuKeyError` ⇒ `dieu_phoi` đọc
    thành *"provider không phục vụ được, đi tiếp"* ⇒ **bỏ qua model nhà** rồi
    xuống provider sau, không lỗi, không cảnh báo, chỉ một hoá đơn.

    ⇒ Bản sửa ở một chỗ không bảo vệ được chỗ kia. Phép kiểm này chốt **tính
      chất**, nên nó bảo vệ mọi chỗ dựng bản đồ model từ `canonical`.
    """
    trung = {k: v for k, v in C.ALIAS_SANG_ID.items() if k == v}
    assert not trung, (
        f"bi danh anh xa VE CHINH NO: {trung} — lop dem bi xoa, va "
        f"`chon_key` se im lang bo qua model nha")


def test_ban_do_model_tra_ID_THAT_chu_khong_phai_bi_danh():
    for alias in C.MODEL_HOP_LE:
        ban_do = C.ban_do_model(alias)
        assert list(ban_do) == [C.THU_TU_PROVIDER[0]]
        (id_that,) = ban_do.values()
        assert id_that not in C.ALIAS_SANG_ID, (
            f"`ban_do_model({alias!r})` tra ve mot BI DANH ({id_that!r}), "
            f"khong phai id noi bo")


def test_id_that_phai_TON_TAI_trong_registry():
    """Đối chiếu với `providers`, không gõ lại `"qwen38-api"`.

    ⭐ Chốt **TẬP HỢP**, không chốt **GIÁ TRỊ**: ngày đổi model nhà, phép kiểm
       này không đỏ giả — nó chỉ đỏ khi bản đồ trỏ tới thứ registry không có.
    """
    from platform_core import providers

    co_that = {m.id for m in providers.REGISTRY[C.THU_TU_PROVIDER[0]].models}
    thieu = set(C.ALIAS_SANG_ID.values()) - co_that
    assert not thieu, f"bi danh tro toi model KHONG CO trong registry: {thieu}"


def test_thu_tu_provider_KHONG_CO_provider_ngoai():
    """⛔ D-010 — hàng bán ra ngoài không được đổi model sau lưng khách.

    Đây là mệnh đề phủ định thứ hai: nó chốt một thứ **không được có mặt**.
    """
    from platform_core import providers

    for pid in C.THU_TU_PROVIDER:
        p = providers.REGISTRY.get(pid)
        assert p is not None, f"provider {pid!r} khong co trong registry"
        assert p.is_active, f"provider {pid!r} da ngung — duong LLM noi bo gay"
        assert p.base_url == "" or "generativelanguage" not in p.base_url
    assert "gemini" not in C.THU_TU_PROVIDER
    assert "apiai" not in C.THU_TU_PROVIDER
    assert "cheapkeyai" not in C.THU_TU_PROVIDER


def test_bi_danh_la_thi_NEM_chu_khong_im_lang_roi_ve_mac_dinh():
    """Rơi về mặc định khi nhận một bí danh lạ là **fail-open**: bên gọi tưởng
    mình chọn model A, hệ thống chạy model B, và không có dấu vết nào."""
    with pytest.raises(KeyError):
        C.ban_do_model("khong-ton-tai")


def test_app_ltt_llm_dung_CHUNG_doi_tuong_chu_khong_phai_ban_sao():
    """Hai bản sao của một bảng là hai chân lý — và chúng sẽ trôi khỏi nhau."""
    from apps.ltt_llm import features

    assert features.ALIAS_SANG_ID is C.ALIAS_SANG_ID
    assert features.THU_TU_PROVIDER is C.THU_TU_PROVIDER
    assert features.MODEL_MAC_DINH == C.MODEL_MAC_DINH
