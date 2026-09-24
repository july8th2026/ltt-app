"""test_2901 — `nut_loi/ai_loi.py`: ánh xạ kết quả job text.chat -> FAILED
(plan wf-v2 P7 Task 3+4).

Bẫy đã ĐO (memory `model-nha-tren-may-b.md` / `model-nha-tra-ve-rong-...md`,
12/09/2026): máy B có thể trả HTTP 200, job SUCCEEDED, `content` RỖNG (khối
suy nghĩ không đóng). Cầu nối job chung (`cau_noi.ap_ket_qua`) chỉ nhìn
`job.status`, không đọc bên trong `result` -> một job "thành công" với
content rỗng đi thẳng thành node SUCCEEDED nếu không có lớp này.
"""
from __future__ import annotations

from platform_core.workflow.nut_loi import ai_loi


def test_content_rong_la_FAILED_khong_phai_SUCCEEDED():
    """Ca đã đo: job SUCCEEDED, content rỗng -> node phải FAILED."""
    trang_thai, ma, chi_tiet = ai_loi.dien_giai({"content": ""})
    assert trang_thai == "FAILED"
    assert ma == "dau_ra_rong"
    assert chi_tiet


def test_content_chi_co_khoang_trang_cung_la_rong():
    trang_thai, ma, _ = ai_loi.dien_giai({"content": "   \n\t "})
    assert (trang_thai, ma) == ("FAILED", "dau_ra_rong")


def test_content_thieu_khoa_cung_la_rong():
    trang_thai, ma, _ = ai_loi.dien_giai({})
    assert (trang_thai, ma) == ("FAILED", "dau_ra_rong")


def test_content_khong_phai_chuoi_la_rong():
    trang_thai, ma, _ = ai_loi.dien_giai({"content": None})
    assert (trang_thai, ma) == ("FAILED", "dau_ra_rong")


def test_content_co_chu_khong_luoc_do_la_SUCCEEDED():
    """⭐ Đối chứng — không có bẫy này thì phép trên xanh giả."""
    trang_thai, ma, chi_tiet = ai_loi.dien_giai({"content": "xin chao"})
    assert (trang_thai, ma, chi_tiet) == ("SUCCEEDED", "", "")


def test_khop_luoc_do_la_SUCCEEDED():
    luoc_do = {"type": "object", "properties": {"ten": {"type": "string"}},
               "required": ["ten"]}
    trang_thai, ma, _ = ai_loi.dien_giai(
        {"content": '{"ten": "An"}'}, luoc_do=luoc_do)
    assert (trang_thai, ma) == ("SUCCEEDED", "")


def test_khong_khop_luoc_do_la_FAILED_dau_ra_sai_luoc_do():
    """spec §12.1: `ai.extract` — không khớp lược đồ ⇒ FAILED `dau_ra_sai_luoc_do`."""
    luoc_do = {"type": "object", "properties": {"tuoi": {"type": "integer"}},
               "required": ["tuoi"]}
    trang_thai, ma, chi_tiet = ai_loi.dien_giai(
        {"content": '{"ten": "An"}'}, luoc_do=luoc_do)
    assert trang_thai == "FAILED"
    assert ma == "dau_ra_sai_luoc_do"
    assert chi_tiet


def test_content_khong_phai_json_voi_luoc_do_la_FAILED():
    """Model bọc JSON trong ```json``` hoặc trả chữ thường — đã đo 14/09
    (`apps/ltt_llm/manifest.py` dòng ~318): engine có thể bỏ qua khuôn và
    JSON bị bọc trong markdown."""
    luoc_do = {"type": "object", "properties": {"ten": {"type": "string"}}}
    trang_thai, ma, chi_tiet = ai_loi.dien_giai(
        {"content": "```json\n{\"ten\": \"An\"}\n```"}, luoc_do=luoc_do)
    assert trang_thai == "FAILED"
    assert ma == "dau_ra_sai_luoc_do"
    assert chi_tiet


def test_luoc_do_sai_cu_phap_bi_bao_loi_ro_khong_nem_ngoai_y_muon():
    """`jsonschema` ném `SchemaError` khi CHÍNH lược đồ sai — module này phải
    dịch nó thành FAILED có lý do, không để ngoại lệ thoát ra ngoài."""
    luoc_do = {"type": "khong_ton_tai"}
    trang_thai, ma, chi_tiet = ai_loi.dien_giai(
        {"content": '{"a": 1}'}, luoc_do=luoc_do)
    assert trang_thai == "FAILED"
    assert ma == "dau_ra_sai_luoc_do"
    assert "luoc_do" in chi_tiet or "schema" in chi_tiet.lower()


def test_MA_LOI_AI_khai_ca_hai_ma():
    assert set(ai_loi.MA_LOI_AI) == {"dau_ra_rong", "dau_ra_sai_luoc_do"}
