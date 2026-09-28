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

✅ `publish_duoc=True` từ 28/09/2026. Hai điều kiện còn thiếu đã xong:

  - cầu nối job **⛔ không còn** cắt chuỗi `node["type"][4:]`; `cau_noi.py:103`
    đọc `nd.ten_toolspec`. Đo được: `text.chat` tra ra trong `cong_cu.tat_ca()`
    và `job_type` khớp đúng `ltt_llm.chat`.
  - **phép dịch đầu ra** (`nd.doi_dau_ra`, thêm cùng ngày) — xem dưới.

🔴 **Và đây là lý do THẬT khiến cờ ấy phải `False` suốt tới 28/09 — ⛔ KHÔNG phải
   lý do bản docstring cũ ghi.** Bản cũ nói *"compiler chưa biết dịch `tham_so`
   thành `params`"* và *"cầu nối suy tên ToolSpec bằng `[4:]`"*. Đo trực tiếp thì
   **cả hai đã hết đúng**: bật cờ trong bộ nhớ, `bien_dich.bien_dich()` chạy
   thẳng. Nếu tin docstring, ta sẽ bật cờ và tưởng đã xong.

   Thứ thật sự hỏng nằm ở **từ vựng đầu ra**:

       ToolSpec `text.chat`  returns  content · tool_calls · usage
       `ai.llm`              cong_ra  text · json

   và `ap_ket_qua` ghi `output_ref = result` **nguyên văn**. Nên
   `{{ nodes.n2.output.text }}` đọc ra **rỗng** — ⛔ không lỗi, ⛔ không cảnh báo,
   sau khi credit đã bị trừ.

⚠️ Một lời giải thích **sai** cho một cái cờ nguy hiểm hơn ⛔ không có lời giải
   thích nào: nó mời người đọc bật cờ. Cùng họ *"tham chiếu chết"* mà B12 ghi
   (`dung_video.py:35` nói `demucs_runner` ⛔ không đặt `set_num_threads` trong khi
   dòng 324 đã đặt).
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

#: Tên ToolSpec mà cả ba node `ai.*` BỌC (`ToolSpec(name="text.chat", ...)`
#: trong `apps/ltt_llm/manifest.py`). ⛔ Khác `JOB_TYPE_TEXT_CHAT`: cái kia
#: là làn hàng đợi, cái này là khoá tra `cong_cu.tat_ca()`. Hai chuỗi khác
#: nhau, và không phép cắt chuỗi nào nối được chúng.
TEN_TOOLSPEC = "text.chat"


def doi_dau_ra_llm(ket_qua: dict, params: dict) -> dict:
    """`content` của job → cổng ra `text` / `json` của `ai.llm`.

    ⭐ `json` là `content` đã `json.loads` khi đọc được, ngược lại `None`.
       `ai.llm` ⛔ không bắt buộc JSON (chỉ `ai.extract` mới bắt), nên một
       `content` là văn xuôi là **bình thường** — và `None` ở cổng `json` nói
       đúng điều đó.

    ⚠️ Hàm này chạy **sau** `hau_kiem`, tức sau khi `content` rỗng đã bị chặn.
       Nên ⛔ không lặp lại phép kiểm rỗng ở đây: hai chỗ cùng kiểm một điều rồi
       trôi khỏi nhau là lỗi ta đã trả giá nhiều lần.
    """
    return {"text": ket_qua.get("content"),
            "json": _thu_doc_json(ket_qua.get("content"))}


def doi_dau_ra_extract(ket_qua: dict, params: dict) -> dict:
    """`content` → cổng ra `json` của `ai.extract`.

    🔴 `ai_loi.dien_giai` **đã** `json.loads` nội dung này để kiểm lược đồ, rồi
       **vứt giá trị đã parse đi** và chỉ trả `(trạng thái, mã, chi tiết)`. Nên
       công parse bị làm hai lần. Đó là một cái giá nhỏ, nhưng lý do giữ nguyên
       là đáng nói: `dien_giai` là hàm THUẦN về *"dùng được không"*; đổi nó thành
       *"dùng được không VÀ giá trị là gì"* làm nó mang hai nghĩa, và mọi nơi gọi
       nó phải học nghĩa thứ hai.

    ⭐ `hau_kiem` đã chặn ca ⛔ không phải JSON và ca sai lược đồ, nên tới đây
       `_thu_doc_json` ⛔ không thể trả `None` — trừ khi ai bỏ `hau_kiem` đi.
       ⇒ Vẫn trả thẳng, ⛔ không thêm nhánh phòng thủ cho ca ấy: một nhánh ⛔
         không bao giờ chạy mua sự yên tâm bằng tín dụng giả.
    """
    return {"json": _thu_doc_json(ket_qua.get("content"))}


def _thu_doc_json(content):
    """`json.loads` khi đọc được, `None` khi không. ⛔ Không nuốt lặng lẽ điều gì
    quan trọng: với `ai.llm`, *"⛔ không phải JSON"* là một ca HỢP LỆ, ⛔ không
    phải một lỗi bị che."""
    import json as _json
    if not isinstance(content, str) or not content.strip():
        return None
    try:
        return _json.loads(content)
    except ValueError:
        return None


def hau_kiem(ket_qua: dict, params: dict) -> tuple:
    """`NodeDefinition.hau_kiem` cho node `ai.*` — bọc `ai_loi.dien_giai`.

    Bộ chuyển đổi mỏng: cầu nối job đưa `(result, params)`, còn
    `dien_giai` chỉ cần `result` + `luoc_do` đã khai trên node. Giữ
    `ai_loi` THUẦN (không biết `params` là gì) là lý do có lớp này.
    """
    return ai_loi.dien_giai(ket_qua,
                            luoc_do=(params or {}).get("luoc_do"))

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
    ten_toolspec=TEN_TOOLSPEC, hau_kiem=hau_kiem,
    side_effect="external", idempotency_key_fields=(),
    resource={"class": "api"}, gia=Gia.theo_registry(JOB_TYPE_TEXT_CHAT),
    doi_dau_ra=doi_dau_ra_llm,
    credential=(), quyen=frozenset({"network"}),
    cho=("JOB",), ma_loi=ai_loi.MA_LOI_AI,
    publish_duoc=True))


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
    ten_toolspec=TEN_TOOLSPEC, hau_kiem=hau_kiem,
    side_effect="external", idempotency_key_fields=(),
    resource={"class": "api"}, gia=Gia.theo_registry(JOB_TYPE_TEXT_CHAT),
    doi_dau_ra=doi_dau_ra_extract,
    credential=(), quyen=frozenset({"network"}),
    cho=("JOB",), ma_loi=ai_loi.MA_LOI_AI,
    publish_duoc=True))


__all__ = ["AI_EXTRACT", "AI_LLM", "JOB_TYPE_TEXT_CHAT", "TEN_TOOLSPEC",
           "hau_kiem", "doi_dau_ra_llm", "doi_dau_ra_extract"]
