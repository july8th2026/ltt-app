"""`ai.llm` / `ai.extract` — bọc ToolSpec `text.chat` có sẵn (spec §12.1).

Plan wf-v2 P7 Task 1 ("đấu dây node AI → ToolSpec"). Bảng §4.3: không gian
`ai.*` là **node lõi**, `type_version` "khai trong mã" — KHÁC `app.*` (thứ
suy `NodeDefinition` từ `ToolSpec` qua `nut.tu_toolspec`). ⇒ `tham_so`/cổng
của `ai.llm` là từ vựng RIÊNG của node (đơn giản hơn `text.chat` thô: một
`prompt`, không phải mảng `messages` đầy đủ vai trò), còn cái THẬT SỰ dùng
lại từ ToolSpec là đường thực thi:

  - `job_type="ltt_llm.chat"` — chuỗi lấy ĐÚNG từ `apps/ltt_llm/manifest.py`
    (`ToolSpec(name="text.chat", job_type="ltt_llm.chat", ...)`), không suy
    đoán (`test_2902::test_job_type_khop_that_voi_ToolSpec_text_chat`).
  - `Gia.theo_registry("ltt_llm.chat")` — CÙNG cơ chế báo giá
    (`registry.credit_for`) mà `app.text.chat` dùng, không viết một biểu giá
    song song.

`ai.extract` = `ai.llm` + `luoc_do` (JSON Schema) BẮT BUỘC; không khớp lược
đồ ⇒ FAILED `dau_ra_sai_luoc_do` (spec §12.1) — việc kiểm thật nằm ở
`ai_loi.dien_giai` (Task 3+4), tệp này chỉ khai `tham_so`/cổng/`ma_loi`.

⛔ `publish_duoc=False`: bộ biên dịch (`bien_dich._node`) chưa biết dịch
   `tham_so` của `ai.*` (vd `luoc_do`) thành `params` của job `text.chat`
   thật — cùng lý do `trigger.manual`/mọi `core.*` hôm nay đều `False` cho
   tới khi có plan nối compiler. Việc đó KHÔNG thuộc `nut_loi/ai_*.py`.

⛔ CHƯA nối vào `cau_noi.nop_job`/`ap_ket_qua`: cầu nối job chung suy tên
   ToolSpec bằng `node["type"][4:]` (cắt đúng 4 ký tự cho tiền tố `"app."`)
   — áp trực tiếp cho `"ai.llm"` ra `"lm"`, vô nghĩa. Tổng quát hoá cầu nối
   đó là việc ở `platform_core/workflow/cau_noi.py`, ngoài phạm vi tệp cho
   phép của làn p7. Xem `docs/superpowers/reports/p7-ai/task-1-report.md`.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.workflow import he_kieu
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi import ai_loi, dang_ky

#: `apps/ltt_llm/manifest.py` — `ToolSpec(name="text.chat",
#: job_type="ltt_llm.chat", ...)`. Một hằng, đọc từ nguồn một lần, dùng lại
#: ở cả hai NodeDefinition thay vì gõ lại chuỗi.
JOB_TYPE_TEXT_CHAT = "ltt_llm.chat"

_MO_HINH = {"type": "string", "enum": ["ltt-3.8", "ltt-3.5"],
            "default": "ltt-3.8", "description": N_("Model nội bộ.")}


def _tham_so(*, bat_buoc_luoc_do: bool) -> dict:
    """§4.6 — tập con JSON Schema. `luoc_do` mang `x-ltt-control: code-json`:
    người soạn workflow gõ một JSON Schema thật (Draft 2020-12) cho đầu ra
    — `ai_loi.kiem_luoc_do` kiểm nó bằng `jsonschema` lúc chạy."""
    bat_buoc = ["prompt"] + (["luoc_do"] if bat_buoc_luoc_do else [])
    return {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "x-ltt-control": "textarea",
                       "description": N_("Câu lệnh gửi model.")},
            "model": dict(_MO_HINH),
            "luoc_do": {"type": "object", "x-ltt-control": "code-json",
                        "description": N_(
                            "JSON Schema cho đầu ra. Không khớp -> FAILED "
                            "dau_ra_sai_luoc_do.")},
            "max_tokens": {"type": "integer", "minimum": 1},
        },
        "required": bat_buoc, "additionalProperties": False,
    }


AI_LLM = dang_ky(NodeDefinition(
    type="ai.llm", type_version=1, kind="ai", category="AI",
    title=N_("AI: Sinh văn bản"),
    description=N_("Gọi model nội bộ (bọc text.chat). Khai luoc_do (tuỳ "
                    "chọn) để ép JSON có kiểm — spec §12.1."),
    icon="🤖",
    cong_vao=(
        ("prompt", he_kieu.Cong(type="text", required=True, nhan="prompt")),
        ("model", he_kieu.Cong(type="text", required=False, nhan="model")),
    ),
    cong_ra=(
        ("text", he_kieu.Cong(type="text", required=True, nhan="text")),
        # `required=False`: chỉ có giá trị dùng được khi node khai `luoc_do`
        # (spec §12.1 "json_schema tuỳ chọn ⇒ ra json đã kiểm") — khác
        # `ai.extract`, nơi cổng `json` LUÔN bắt buộc vì lược đồ bắt buộc.
        ("json", he_kieu.Cong(type="json", required=False, nhan="json")),
    ),
    tham_so=_tham_so(bat_buoc_luoc_do=False),
    thi_hanh="job", job_type=JOB_TYPE_TEXT_CHAT,
    side_effect="external", idempotency_key_fields=(),
    resource={"class": "api"}, gia=Gia.theo_registry(JOB_TYPE_TEXT_CHAT),
    credential=(), quyen=frozenset({"network"}),
    cho=("JOB",), ma_loi=ai_loi.MA_LOI_AI,
    publish_duoc=False))


AI_EXTRACT = dang_ky(NodeDefinition(
    type="ai.extract", type_version=1, kind="ai", category="AI",
    title=N_("AI: Trích xuất có kiểm"),
    description=N_("text.chat + lược đồ BẮT BUỘC. Không khớp -> FAILED "
                    "dau_ra_sai_luoc_do (spec §12.1)."),
    icon="🧩",
    cong_vao=(
        ("prompt", he_kieu.Cong(type="text", required=True, nhan="prompt")),
        ("model", he_kieu.Cong(type="text", required=False, nhan="model")),
    ),
    cong_ra=(
        ("json", he_kieu.Cong(type="json", required=True, nhan="json")),
    ),
    tham_so=_tham_so(bat_buoc_luoc_do=True),
    thi_hanh="job", job_type=JOB_TYPE_TEXT_CHAT,
    side_effect="external", idempotency_key_fields=(),
    resource={"class": "api"}, gia=Gia.theo_registry(JOB_TYPE_TEXT_CHAT),
    credential=(), quyen=frozenset({"network"}),
    cho=("JOB",), ma_loi=ai_loi.MA_LOI_AI,
    publish_duoc=False))


__all__ = ["AI_EXTRACT", "AI_LLM", "JOB_TYPE_TEXT_CHAT"]
