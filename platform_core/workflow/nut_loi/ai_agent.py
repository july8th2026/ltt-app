"""`ai.agent` — executor agent có giới hạn (spec §12.3), plan wf-v2 P8 Task 2.

Khai báo node; toàn bộ vòng lặp ở `platform_core/workflow/tac_tu.py`.

`thi_hanh="run_con"`: cùng lớp với `core.call_workflow` — node này **không
sinh job** và **không giữ tiền**; nó mở một `workflow_run` con rồi chờ. Vì thế
nó nằm trong `THI_HANH_TRONG_DONG_CO` và động cơ chạy nó ở pha inline.

## Trần nằm trong LƯỢC ĐỒ

Nguồn: Activepieces `packages/core/shared/src/lib/ee/agent/agent.ts` —

    maxSteps: z.number().int().positive().max(MAX_AGENT_STEP_BUDGET)…
    tools: z.array(AgentTool).max(MAX_AGENT_TOOLS)…

Trần là một luật của **lược đồ**, nên một cấu hình vượt trần không bao giờ
được LƯU. Ở đây `maximum`/`maxItems`/`minimum` của `tham_so` được
`bien_dich._kiem_tham_so_loi` cưỡng chế ở **cổng publish** — ⛔ không phải
một `if` lúc chạy, vì lúc chạy là lúc đang tiêu tiền của khách.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.workflow import he_kieu, tac_tu
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi import ai_loi, dang_ky

#: Bí danh của `tac_tu.NUT_BUOC` — id node duy nhất trong mỗi run con. Nêu lại
#: ở đây để bên đọc kết quả một bước không phải biết tên mô-đun thi hành.
NUT_BUOC = tac_tu.NUT_BUOC

#: Spec §12.3: `cong_cu_cho_phep` ≤ 10, `so_buoc_toi_da` ≤ 8.
MAX_CONG_CU = 10
MAX_BUOC = 8

THAM_SO = {
    "type": "object",
    "properties": {
        "muc_tieu": {"type": "string", "x-ltt-control": "textarea",
                     "description": N_("Việc agent phải hoàn thành.")},
        "cong_cu_cho_phep": {
            "type": "array", "items": {"type": "string"},
            "maxItems": MAX_CONG_CU,
            "description": N_("Danh sách TRẮNG: loại node agent được gọi. "
                              "Không nêu tức là cấm.")},
        "so_buoc_toi_da": {"type": "integer", "minimum": 1,
                           "maximum": MAX_BUOC, "default": 4,
                           "description": N_("Số lần gọi công cụ tối đa.")},
        "ngan_sach_credit": {
            "type": "integer", "minimum": 1,
            "description": N_("Trần credit của CẢ lượt agent. Đây cũng là "
                              "trần báo giá của node.")},
        "timeout_s": {"type": "integer", "minimum": 1, "maximum": 21600},
        "luoc_do_dau_ra": {
            "type": "object", "x-ltt-control": "code-json",
            "description": N_("JSON Schema cho ket_qua. Không khớp -> FAILED "
                              "dau_ra_sai_luoc_do.")},
    },
    "required": ["muc_tieu", "cong_cu_cho_phep", "so_buoc_toi_da",
                 "ngan_sach_credit"],
    "additionalProperties": False,
}


AI_AGENT = dang_ky(NodeDefinition(
    type=tac_tu.LOAI, type_version=1, kind="ai", category="AI",
    title=N_("AI: Agent có giới hạn"),
    description=N_("Agent tự chọn công cụ trong danh sách trắng. Mỗi lần gọi "
                   "là một run con; cả lượt nằm trong MỘT ngân sách."),
    icon="🧠",
    cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in")),),
    cong_ra=(("ket_qua", he_kieu.Cong(type="json", required=True,
                                      nhan="ket_qua")),
             ("buoc", he_kieu.Cong(type="json", required=False, nhan="buoc"))),
    tham_so=THAM_SO,
    # ⛔ `Gia.mien_phi()` KHÔNG có nghĩa là node này miễn phí — trần thật của
    #    nó là `params.ngan_sach_credit`, và `bao_gia._gia_node` đọc thẳng con
    #    số ấy. `Gia` chỉ tả được ba hình dạng (miễn phí / cố định / theo
    #    registry), không tả được "theo một tham số", nên nguồn chân lý là
    #    `bao_gia`, y như `core.call_workflow` với `gia_con`.
    thi_hanh="run_con", gia=Gia.mien_phi(), quyen=frozenset({"network"}),
    cho=("run_con",), ma_loi=tac_tu.MA_LOI + ai_loi.MA_LOI_AI,
    publish_duoc=True), tac_tu.chay_agent)


__all__ = ["AI_AGENT", "MAX_BUOC", "MAX_CONG_CU", "NUT_BUOC", "THAM_SO"]
