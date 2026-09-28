"""`ai.router` — chọn MỘT nhánh trong enum khai sẵn qua LLM (spec §12.1, ADR Q8).

Plan wf-v2 P7 Task 2. "không khớp ⇒ nhánh `mac_dinh`" — `chon_nhanh()` là
phần LÕI của node: một hàm THUẦN, không đụng job/engine, nên kiểm được đầy
đủ bằng test đơn vị mà không cần máy B (`test_2903`).

⭐ `core.if` **không bao giờ** gọi LLM; chỉ `ai.router` gọi (spec §12.1) —
   tệp này không thay thế và không đụng `core.if`/`core.switch` (phạm vi
   node điều khiển của làn p3, `nut_loi/core_*.py`).

✅ Đã nối 28/09/2026. `chon_nhanh()` viết từ plan P7 Task 2, **có test đơn vị
   `test_2903`, và ⛔ KHÔNG ai gọi** cho tới hôm nay — một hàm đúng, được kiểm,
   nằm ngoài mọi đường chạy. Cùng họ với `gate.ngan_sach_loi(tru_phien_khac=...)`:
   một cơ chế có tài liệu, có phép kiểm riêng, và ⛔ không nơi nào dùng, nên ⛔
   không phép kiểm nào thất bại khi nó vắng mặt.

⚠️ ⇒ *"Có hàm + có test"* ⛔ **không** trả lời *"tính năng có chạy không"*. Câu
   trả lời nằm ở **ai gọi nó**, và ⛔ không bảng độ phủ nào hỏi câu đó: dòng mã ấy
   **có** chạy — trong test.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.workflow import he_kieu
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi import ai_llm, ai_loi, dang_ky

#: Nhánh dùng khi model không trả đúng một trong các nhánh đã khai (spec
#: §12.1). Cũng là `default` của tham số `mac_dinh` trên node.
NHANH_MAC_DINH = "mac_dinh"


def chon_nhanh(dau_ra, nhanh_hop_le, *, mac_dinh: str = NHANH_MAC_DINH) -> str:
    """`dau_ra` (content thô model trả) khớp ĐÚNG một nhánh trong
    `nhanh_hop_le` -> nhánh đó. Khác đi (rỗng, `None`, không khớp, hoặc chỉ
    khớp MỘT PHẦN kèm chữ khác — vd model trả `"spam vi ..."` thay vì đúng
    `"spam"`) -> `mac_dinh`.

    ⛔ So khớp CHÍNH XÁC (sau `strip`), không phải `in`/substring: khớp lỏng
       sẽ cho một câu giải thích dài có chứa tên nhánh đi qua như thể model
       đã "chọn" — sai với "chọn MỘT nhánh" của spec, và không phân biệt
       được với ca model chỉ NHẮC tới nhãn nhánh trong lời giải thích.
    """
    ung_vien = (dau_ra or "").strip()
    return ung_vien if ung_vien in set(nhanh_hop_le) else mac_dinh


def doi_dau_ra_router(ket_qua: dict, params: dict) -> dict:
    """`content` → cổng ra `nhanh`, qua `chon_nhanh()`.

    ⭐ Đọc `ai_choice`/`mac_dinh` từ **`params` của node**, ⛔ không từ một hằng:
       danh sách nhánh là thứ người soạn khai lúc thiết kế workflow (ADR Q8).

    ⚠️ `mac_dinh` lấy `params.get("mac_dinh") or NHANH_MAC_DINH` — chuỗi rỗng phải
       rơi về hằng, ⛔ không được thành một tên nhánh rỗng. Lược đồ có `default`,
       nhưng `default` của JSON Schema ⛔ không tự điền vào `params` đã lưu.
    """
    return {"nhanh": chon_nhanh(ket_qua.get("content"),
                                params.get("ai_choice") or (),
                                mac_dinh=str(params.get("mac_dinh")
                                             or NHANH_MAC_DINH))}


AI_ROUTER = dang_ky(NodeDefinition(
    type="ai.router", type_version=1, kind="ai", category="AI",
    title=N_("AI: Chọn nhánh"),
    description=N_("Model chọn một nhánh trong danh sách ai_choice đã khai; "
                    "không khớp -> nhánh mac_dinh. core.if không gọi LLM, "
                    "chỉ node này (spec §12.1)."),
    icon="🔀",
    cong_vao=(
        ("prompt", he_kieu.Cong(type="text", required=True, nhan="prompt")),
        ("model", he_kieu.Cong(type="text", required=False, nhan="model")),
    ),
    cong_ra=(
        ("nhanh", he_kieu.Cong(type="text", required=True, nhan="nhanh")),
    ),
    tham_so={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "x-ltt-control": "textarea",
                       "description": N_("Câu lệnh gửi model.")},
            "model": {"type": "string", "enum": ["ltt-3.8", "ltt-3.5"],
                      "default": "ltt-3.8"},
            # ⛔ ADR Q8: `ai_choice` là enum các NHÁNH của CHÍNH node này
            #    (danh sách hằng người dùng khai lúc thiết kế workflow) —
            #    KHÔNG phải `ToolSpec.tuy_chon_dong` (enum theo người dùng
            #    cuối, spec §4.6) và không sinh `x-ltt-dong`.
            "ai_choice": {"type": "array", "items": {"type": "string"},
                          "minItems": 1,
                          "description": N_("Danh sách nhánh hợp lệ.")},
            "mac_dinh": {"type": "string", "default": NHANH_MAC_DINH},
        },
        "required": ["prompt", "ai_choice"], "additionalProperties": False,
    },
    thi_hanh="job", job_type=ai_llm.JOB_TYPE_TEXT_CHAT,
    # Cùng ToolSpec, cùng hậu kiểm với `ai.llm` — đọc từ `ai_llm`, không gõ lại
    # chuỗi. `ai.router` chọn nhánh từ `content`, nên một `content` RỖNG phải
    # hỏng ở đây chứ không đi tiếp để `chon_nhanh` lặng lẽ trả `mac_dinh`.
    ten_toolspec=ai_llm.TEN_TOOLSPEC, hau_kiem=ai_llm.hau_kiem,
    side_effect="external", idempotency_key_fields=(),
    resource={"class": "api"}, gia=Gia.theo_registry(ai_llm.JOB_TYPE_TEXT_CHAT),
    credential=(), quyen=frozenset({"network"}),
    cho=("JOB",), ma_loi=ai_loi.MA_LOI_AI,
    doi_dau_ra=doi_dau_ra_router,
    publish_duoc=True))


__all__ = ["AI_ROUTER", "NHANH_MAC_DINH", "chon_nhanh",
           "doi_dau_ra_router"]
