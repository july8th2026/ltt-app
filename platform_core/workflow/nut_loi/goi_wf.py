"""`core.call_workflow` — gọi một workflow khác (spec §5.10).

Node này `thi_hanh="run_con"`: nó không sinh job và **không** giữ tiền; nó mở
một `workflow_run` con và chờ. Toàn bộ lập luận về tiền ở
`platform_core/workflow/run_con.py`.

⚠️ `version_id` được **ghim lúc publish cha** (`dinh_nghia.xuat_ban_draft` thay
   `"latest"` bằng id version publish hiện tại). Lúc chạy nó là một hằng — nên
   một lần publish lại workflow con **không** đổi hành vi của cha đang chạy.
   Đó là cùng bất biến mà `WorkflowRun.version_id` giữ cho chính run.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.workflow import (he_kieu, ngon_ngu, run_con,
                                    thi_hanh)
from platform_core.workflow.chinh_sach import LoiNgonNgu
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi.chay import KetQua


def chay_call_workflow(db, run, node: dict, *, moi_truong: dict, vong=(),
                       **_) -> KetQua:
    p = node.get("params") or {}
    try:
        inputs = {str(k): ngon_ngu.tinh(str(v), moi_truong)
                  for k, v in (p.get("inputs") or {}).items()}
    except LoiNgonNgu as loi:
        return KetQua(sang="FAILED", error=f"bieu_thuc_loi: {loi}"[:2000])
    try:
        # 🔴 `parent_node_id` phải là ĐƯỜNG THI HÀNH, không phải id trần:
        #    `run_con.bao_cha` hẹn wakeup theo chính chuỗi này, nên hai vòng
        #    `foreach` gọi cùng một node con sẽ sinh CÙNG một `node_run_id`
        #    nếu ở đây ghi id trần — `uq_wakeup_khu_trung` ném, hoặc tệ hơn,
        #    vòng 2 nhận wakeup của vòng 1.
        con = run_con.tao_run_con(db, cha=run,
                                  node_id=thi_hanh.khoa_node(node["id"], vong),
                                  version_id=str(p.get("version_id") or ""),
                                  inputs=inputs)
    except run_con.QuaSau as loi:
        return KetQua(sang="FAILED", error=f"qua_sau_subworkflow: {loi}"[:2000])
    except ValueError as loi:
        return KetQua(sang="FAILED", error=f"dau_vao_sai: {loi}"[:2000])
    # `WAITING` chứ không `RUNNING`: node này **không chiếm** một suất thi hành
    # nào trong lúc con chạy. `NODE_DANG_CHAY` có `WAITING`, nên nó vẫn tính vào
    # trần song song của run cha — đúng: một run con đang chạy là một việc thật.
    return KetQua(sang="WAITING", output={run_con.KHOA_RUN_CON: con.id})


DINH_NGHIA = (
    (NodeDefinition(
        type=run_con.LOAI_GOI, type_version=1, kind="subworkflow",
        category="SUBWORKFLOWS", title=N_("Gọi workflow"),
        description=N_("Chạy một workflow khác và chờ kết quả."),
        icon="⧉",
        cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in")),),
        cong_ra=(("outputs", he_kieu.Cong(type="any", required=True,
                                          nhan="outputs")),
                 ("status", he_kieu.Cong(type="text", required=True,
                                         nhan="status"))),
        tham_so={"type": "object",
                 "properties": {"workflow_id": {"type": "string"},
                                "version_id": {"type": "string"},
                                "inputs": {"type": "bang_bieu_thuc"}},
                 "required": ["workflow_id", "version_id", "inputs"],
                 "additionalProperties": False},
        thi_hanh="run_con", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=("run_con",), ma_loi=("bieu_thuc_loi", "dau_vao_sai",
                                  "qua_sau_subworkflow", "run_con_loi"),
        publish_duoc=True), chay_call_workflow),
)

__all__ = ["DINH_NGHIA", "chay_call_workflow"]
