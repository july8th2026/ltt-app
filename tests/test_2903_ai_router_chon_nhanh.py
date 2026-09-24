"""test_2903 — `ai.router`: chọn một nhánh trong enum khai sẵn qua LLM; không
khớp ⇒ nhánh `mac_dinh` (plan wf-v2 P7 Task 2, spec §12.1 + ADR Q8).

⭐ `core.if` không bao giờ gọi LLM; chỉ `ai.router` gọi (spec §12.1) — tệp
này KHÔNG đụng `core.if`/`switch` (phạm vi của làn p3).
"""
from __future__ import annotations

import pytest

from platform_core.workflow import nut_loi
from platform_core.workflow.nut_loi import ai_llm, ai_router


def test_khop_dung_mot_nhanh_da_khai():
    assert ai_router.chon_nhanh("spam", ["spam", "khong_spam"]) == "spam"


def test_khong_khop_nao_thi_ve_MAC_DINH():
    assert ai_router.chon_nhanh("khong ro", ["spam", "khong_spam"]) == \
        ai_router.NHANH_MAC_DINH


def test_rong_thi_ve_MAC_DINH():
    assert ai_router.chon_nhanh("", ["spam", "khong_spam"]) == \
        ai_router.NHANH_MAC_DINH
    assert ai_router.chon_nhanh(None, ["spam", "khong_spam"]) == \
        ai_router.NHANH_MAC_DINH


def test_khop_thua_chu_khac_KHONG_duoc_tinh_la_khop():
    """Model trả `"spam vi co lien ket la"` — không phải KHỚP, phải về mặc
    định. Khớp lỏng (substring) sẽ cho qua ca này sai."""
    assert ai_router.chon_nhanh("spam vi co lien ket la",
                                ["spam", "khong_spam"]) == \
        ai_router.NHANH_MAC_DINH


def test_khoang_trang_thua_van_khop():
    """Model hay kèm khoảng trắng/newline quanh câu trả lời — `strip()` phải
    xử lý, nhưng KHÔNG được lỏng tới mức chấp nhận khớp một phần."""
    assert ai_router.chon_nhanh("  spam\n", ["spam", "khong_spam"]) == "spam"


def test_mac_dinh_tuy_chinh_duoc():
    assert ai_router.chon_nhanh("khong ro", ["a", "b"], mac_dinh="khac") == \
        "khac"


def test_danh_sach_nhanh_rong_luon_ve_mac_dinh():
    """Đối chứng tập rỗng — spec §12.1 'chọn MỘT nhánh trong enum khai sẵn':
    khai sẵn rỗng thì không có gì để khớp."""
    assert ai_router.chon_nhanh("bat_ky", []) == ai_router.NHANH_MAC_DINH


def test_dinh_nghia_node_kind_ai_khong_dung_luoi_di_kem_ai_choice():
    nd = ai_router.AI_ROUTER
    assert nd.type == "ai.router" and nd.kind == "ai" and nd.category == "AI"
    assert "ai_choice" in nd.tham_so["properties"]
    assert set(nd.tham_so["required"]) >= {"prompt", "ai_choice"}
    assert nd.job_type == ai_llm.JOB_TYPE_TEXT_CHAT


def test_da_dang_ky_vao_so_nut_loi():
    assert nut_loi.tat_ca().get("ai.router") is ai_router.AI_ROUTER
