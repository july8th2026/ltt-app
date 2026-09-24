"""test_2902 — `ai.llm` / `ai.extract`: đấu dây node AI vào ToolSpec `text.chat`
(plan wf-v2 P7 Task 1). Spec §12.1, bảng §4.3 dòng `ai.*`: "node lõi bọc
ToolSpec AI" — type_version/tham_so/cổng khai TRONG MÃ (khác `app.*`, thứ suy
từ ToolSpec), nhưng đường THỰC THI (job_type) phải khớp ToolSpec thật, không
suy đoán.
"""
from __future__ import annotations

from platform_core.workflow import nut_loi
from platform_core.workflow.nut_loi import ai_llm, ai_loi


def test_job_type_khop_that_voi_ToolSpec_text_chat():
    """`job_type` phải đúng chuỗi thật của `text.chat`
    (`apps/ltt_llm/manifest.py`: `ToolSpec(name="text.chat",
    job_type="ltt_llm.chat", ...)`), không phải một chuỗi tự đặt."""
    assert ai_llm.AI_LLM.job_type == "ltt_llm.chat"
    assert ai_llm.AI_EXTRACT.job_type == "ltt_llm.chat"


def test_ai_llm_kind_ai_va_gia_theo_registry_cung_job_type():
    nd = ai_llm.AI_LLM
    assert nd.type == "ai.llm" and nd.kind == "ai" and nd.category == "AI"
    assert nd.thi_hanh == "job"
    assert nd.gia.kieu == "theo_registry" and nd.gia.job_type == "ltt_llm.chat"
    assert nd.resource.get("class") == "api"
    assert nd.side_effect == "external"


def test_ai_llm_tham_so_bat_buoc_prompt_khong_bat_buoc_luoc_do():
    nd = ai_llm.AI_LLM
    assert nd.tham_so["required"] == ["prompt"]
    assert "prompt" in nd.tham_so["properties"]
    assert "luoc_do" in nd.tham_so["properties"]


def test_ai_extract_bat_buoc_ca_prompt_va_luoc_do():
    """spec §12.1: `ai.extract` = `text.chat` + lược đồ BẮT BUỘC."""
    nd = ai_llm.AI_EXTRACT
    assert set(nd.tham_so["required"]) == {"prompt", "luoc_do"}


def test_ai_extract_ma_loi_khai_dau_ra_sai_luoc_do():
    assert "dau_ra_sai_luoc_do" in ai_llm.AI_EXTRACT.ma_loi
    assert set(ai_llm.AI_LLM.ma_loi) == set(ai_loi.MA_LOI_AI)


def test_ai_llm_cong_ra_co_text_bat_buoc_json_khong_bat_buoc():
    cong = dict(ai_llm.AI_LLM.cong_ra)
    assert cong["text"].type == "text" and cong["text"].required is True
    assert cong["json"].type == "json" and cong["json"].required is False


def test_ai_extract_cong_ra_chi_co_json_bat_buoc():
    cong = dict(ai_llm.AI_EXTRACT.cong_ra)
    assert list(cong) == ["json"]
    assert cong["json"].required is True


def test_hai_type_khong_trung_nhau():
    assert ai_llm.AI_LLM.type == "ai.llm"
    assert ai_llm.AI_EXTRACT.type == "ai.extract"


def test_da_dang_ky_vao_so_nut_loi_dung_ham_dang_ky_chung():
    """Dùng lại CHÍNH cơ chế `nut_loi.dang_ky` (không tự chế đăng ký thứ
    hai) — import module là tự động có mặt trong `nut_loi.tat_ca()`."""
    so = nut_loi.tat_ca()
    assert so.get("ai.llm") is ai_llm.AI_LLM
    assert so.get("ai.extract") is ai_llm.AI_EXTRACT
