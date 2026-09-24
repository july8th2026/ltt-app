"""Bộ thi hành node `ai.agent` (spec §12.3) — mỗi bước là **một run con**.

## Hình dạng

Một lượt `ai.agent` là một vòng lặp hai pha, và **cả hai pha đều là run con
một-node**:

```
NGHI      run con [app.text.chat]   -> model tra ve mot QUYET DINH (JSON)
CONG_CU   run con [<cong cu>]       -> ket qua that cua cong cu
NGHI      ...                       -> {"xong": true, "ket_qua": {...}}
```

⭐ **Vì sao pha NGHI cũng là một run con, không phải một lời gọi thẳng.** Động
   cơ chạy trong một transaction; một lời gọi HTTP tới máy B ở đó sẽ giam
   transaction hàng chục giây và **không đi qua** hàng đợi job — tức không qua
   admission, không qua sổ tiền, không qua nhật ký. Đúng cái lỗ mà
   `platform_core/agent/planner.py` từng là (*"đường DUY NHẤT tới máy B không
   đi qua admission"*, P08 F-06). Cho pha NGHI đi đúng đường job là cách
   **dùng lại** cả bốn thứ đó thay vì dựng lại.

## 🔴 Tiền

`run_con.py`: *"MỘT khoản giữ cho cả cây."* Hàm này gọi `run_con.tao_run_con`,
thứ đã **không** gọi `tien.giu_cho_run` — nên mở mười run con vẫn là một khoản
giữ. Chi phí thật cộng lên cha bằng `run_con.tong_chi_phi_con` (một hàm **dẫn
xuất**), không bằng phép cộng dần ở đây.

Trần: `params.ngan_sach_credit` **là** `gia_tran` của node (`bao_gia._gia_node`,
spec §12.3 *"Trần báo giá node = `ngan_sach_credit`"*). Nó là con số người soạn
workflow tự khai cho **chính mình**, nên khai to nghĩa là bị giữ nhiều hơn —
⛔ khác hẳn `core.call_workflow.gia_con`, nơi một trường trong body sẽ là cách
**né** trần. Trước mỗi bước, hàm này kiểm `đã tiêu + trần của bước tới ≤ ngân
sách`; vượt thì **không mở run con nào** (fail-closed).

## Nguồn (⛔ không tự suy)

- **Activepieces** `packages/core/shared/src/lib/ee/agent/agent.ts` —
  `maxSteps … .max(MAX_AGENT_STEP_BUDGET)`, `tools … .max(MAX_AGENT_TOOLS)`:
  trần sống trong **lược đồ**, nên một cấu hình vượt trần không lưu được. Ta
  đặt chúng vào `NodeDefinition.tham_so` và cưỡng chế ở cổng publish.
- **LangGraph** `libs/langgraph/langgraph/pregel/main.py` — hết bước thì
  `raise GraphRecursionError`. Hết bước ở đây là FAILED `vuot_so_buoc`, ⛔
  không phải "trả về kết quả dở" (một kết quả dở trông giống kết quả thật).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from platform_core.models import WorkflowRun
from platform_core.workflow import (bao_gia, dinh_nghia, may_trang_thai as mtt,
                                    run_con, su_kien, thi_hanh)
from platform_core.workflow.nut_loi import ai_loi
from platform_core.workflow.nut_loi.chay import KetQua

LOAI = "ai.agent"

#: Khoá giữ trạng thái vòng lặp trong `output_ref` của node agent.
KHOA = "_tac_tu"

#: Id của node duy nhất trong mỗi run con. Một hằng vì `tiep_buoc` phải đọc
#: lại ảnh chụp của đúng node ấy — hai chỗ gõ tay cùng một chuỗi là hai chỗ
#: bắt đầu lệch nhau.
NUT_BUOC = "buoc"

#: Công cụ của pha NGHI. Cùng ToolSpec mà `ai.llm` bọc (`ai_llm.TEN_TOOLSPEC`),
#: nhưng đi qua node `app.text.chat` — đường **đã chạy được** của cầu nối job.
TOOL_NGHI = "app.text.chat"

PHA_NGHI, PHA_CONG_CU = "NGHI", "CONG_CU"

MA_LOI = ("quyet_dinh_khong_doc_duoc", "cong_cu_khong_duoc_phep",
          "vuot_so_buoc", "vuot_ngan_sach", "dau_ra_sai_luoc_do",
          "buoc_agent_loi", "loi_he_thong")


class LoiAgent(Exception):
    """Một bước không đi tiếp được. `ma` là mã miền (spec §5.6)."""

    def __init__(self, ma: str, chi_tiet: str = ""):
        super().__init__(f"{ma}: {chi_tiet}" if chi_tiet else ma)
        self.ma = ma


# ── Đọc quyết định của model ────────────────────────────────────────────────

def doc_quyet_dinh(noi_dung: Any) -> dict:
    """Text model → `{"xong": bool, "ket_qua"|"cong_cu"/"params"}`.

    ⛔ Không đoán. Một câu tiếng Việt không phải một quyết định, và coi nó là
       "chưa xong, thử lại" sẽ biến một model lạc đề thành một vòng lặp tiêu
       tiền tới hết ngân sách.
    """
    van = noi_dung if isinstance(noi_dung, str) else ""
    van = van.strip()
    if van.startswith("```"):
        xuong = van.find("\n")
        van = van[xuong + 1:] if xuong >= 0 else van[3:]
        if van.rstrip().endswith("```"):
            van = van.rstrip()[:-3]
    bo_doc = json.JSONDecoder()
    for i, ky_tu in enumerate(van):
        if ky_tu != "{":
            continue
        try:
            gia_tri, _het = bo_doc.raw_decode(van[i:])
        except json.JSONDecodeError:
            continue
        if not isinstance(gia_tri, dict):
            continue
        if gia_tri.get("xong") is True:
            return {"xong": True, "ket_qua": gia_tri.get("ket_qua")}
        cong_cu = str(gia_tri.get("cong_cu") or "")
        if cong_cu:
            tham = gia_tri.get("params") or {}
            if not isinstance(tham, dict):
                raise LoiAgent("quyet_dinh_khong_doc_duoc",
                               "`params` phai la object")
            return {"xong": False, "cong_cu": cong_cu, "params": tham}
    raise LoiAgent("quyet_dinh_khong_doc_duoc",
                   "khong tim thay JSON quyet dinh trong dau ra model")


def _prompt(params: dict, lich_su: list) -> str:
    return json.dumps({
        "muc_tieu": params.get("muc_tieu") or "",
        "cong_cu_cho_phep": list(params.get("cong_cu_cho_phep") or []),
        "luoc_do_dau_ra": params.get("luoc_do_dau_ra") or {},
        "lich_su": lich_su,
        "huong_dan": (
            "Tra ve DUNG mot object JSON. Goi cong cu: "
            '{"cong_cu": "<mot ten trong cong_cu_cho_phep>", "params": {...}}. '
            'Xong viec: {"xong": true, "ket_qua": {...}} khop luoc_do_dau_ra. '
            "Khong markdown, khong giai thich."),
    }, ensure_ascii=False)


# ── Mở một run con một-node ─────────────────────────────────────────────────

def _do_thi_mot_nut(loai: str, params: dict, cong_cu: Optional[dict]) -> dict:
    """Đồ thị `ltt.workflow/3` đúng MỘT node, đã có `gia_tran`.

    ⛔ Không đi qua `bien_dich`: đồ thị này do NỀN TẢNG dựng, không do người
       dùng soạn, nên nó không có `pages`, không có biểu thức, không có gì để
       một cổng chống-người-dùng phải canh. Thứ nó **vẫn phải** đi qua là
       `bao_gia_do_thi` — cái ghi `gia_tran`, tức trần mà `cau_noi.nop_job` so
       trước khi nộp job. Bỏ nó là bỏ trần của chính bước này.
    """
    g = {"schema": "ltt.workflow/3", "inputs": [], "outputs": [],
         "settings": {"max_concurrency": 1, "timeout_s": 21600},
         "nodes": [{"id": NUT_BUOC, "type": loai, "type_version": 1,
                    "params": dict(params), "credential_ref": "",
                    "settings": {}, "thi_hanh": "job"}],
         "edges": [], "thu_tu": [NUT_BUOC]}
    bg = bao_gia.bao_gia_do_thi(g, cong_cu=cong_cu)
    return {"graph": g, "tran": bg.toi_da}


def _mo_buoc(db, cha: WorkflowRun, node_id: str, tt: dict, *,
             loai: str, params: dict, cong_cu: Optional[dict],
             ngan_sach: int) -> tuple:
    """Dựng đồ thị một-node, kiểm ngân sách, mở run con. Trả `(run con, trần)`."""
    dt = _do_thi_mot_nut(loai, params, cong_cu)
    con_lai = int(ngan_sach) - int(tt.get("da_tieu") or 0)
    if dt["tran"] > con_lai:
        # ⛔ FAIL-CLOSED: không mở run con nào. Mở rồi mới phát hiện vượt là
        #    mở một lượt tiêu tiền mà trần của cha không đủ che.
        raise LoiAgent("vuot_ngan_sach",
                       f"buoc toi can {dt['tran']}, con lai {con_lai}")
    if not tt.get("wf"):
        wf = dinh_nghia.tao_workflow(
            db, owner_id=cha.owner_id, name=f"agent:{cha.id}:{node_id}")
        tt["wf"] = wf.id
    ver = dinh_nghia.xuat_ban(db, tt["wf"], dt["graph"],
                              created_by=cha.owner_id,
                              estimated_max=dt["tran"])
    con = run_con.tao_run_con(db, cha=cha, node_id=node_id,
                              version_id=ver.id, inputs={})
    return con, dt["tran"]


def _nghi(db, cha, node_id, tt, params, cong_cu) -> WorkflowRun:
    con, _tran = _mo_buoc(
        db, cha, node_id, tt, loai=TOOL_NGHI,
        params={"messages": [{"role": "user",
                              "content": _prompt(params,
                                                 tt.get("lich_su") or [])}]},
        cong_cu=cong_cu, ngan_sach=int(params.get("ngan_sach_credit") or 0))
    tt["pha"] = PHA_NGHI
    return con


# ── Bộ thi hành node (`nut_loi.dang_ky`) ────────────────────────────────────

def chay_agent(db, run: WorkflowRun, node: dict, *, cong_cu=None, **_) -> KetQua:
    """Bước ĐẦU của một node `ai.agent`: mở run con pha NGHI."""
    params = dict(node.get("params") or {})
    tt = {"pha": PHA_NGHI, "buoc": 0, "da_tieu": 0, "lich_su": [], "wf": ""}
    try:
        con = _nghi(db, run, str(node["id"]), tt, params, cong_cu)
    except LoiAgent as loi:
        return KetQua(sang="FAILED", error=str(loi)[:2000])
    su_kien.ghi(db, run.id, "AgentStep",
                du_lieu={"node_id": str(node["id"]), "pha": PHA_NGHI,
                         "buoc": 0, "run_con": con.id})
    return KetQua(sang="WAITING",
                  output={KHOA: tt, run_con.KHOA_RUN_CON: con.id})


# ── Resume: một run con vừa kết thúc ────────────────────────────────────────

def _ket_qua_buoc(db, con_id: str) -> dict:
    anh = thi_hanh.anh_chup_hien_tai(db, con_id, NUT_BUOC)
    return dict((anh.output_ref if anh else None) or {})


def _xong(db, cha, nid, tt, quyet, params, lan) -> None:
    ket = quyet.get("ket_qua")
    lo = params.get("luoc_do_dau_ra") or {}
    if lo:
        sai = ai_loi.kiem_luoc_do(ket, lo)
        if sai:
            raise LoiAgent("dau_ra_sai_luoc_do", sai)
    mtt.chuyen_node(db, cha.id, nid, sang="SUCCEEDED",
                    mo_ta="agent xong", attempt_number=lan,
                    output_ref={KHOA: tt, "ket_qua": ket,
                                "buoc": int(tt.get("buoc") or 0)})


def _buoc_ke(db, cha, nid, tt, quyet, params, cong_cu, lan) -> None:
    cong_cu_chon = str(quyet.get("cong_cu") or "")
    cho_phep = [str(x) for x in (params.get("cong_cu_cho_phep") or [])]
    if cong_cu_chon not in cho_phep:
        # ⛔ Danh sách trắng, không danh sách đen: một công cụ KHÔNG được nêu
        #    là một công cụ bị cấm. Danh sách đen chỉ chặn thứ ta nghĩ ra trước.
        raise LoiAgent("cong_cu_khong_duoc_phep",
                       f"{cong_cu_chon!r} khong nam trong {cho_phep}")
    toi_da = int(params.get("so_buoc_toi_da") or 0)
    if int(tt.get("buoc") or 0) + 1 > toi_da:
        raise LoiAgent("vuot_so_buoc", f"{toi_da} buoc la het")
    con, tran = _mo_buoc(db, cha, nid, tt, loai=cong_cu_chon,
                         params=dict(quyet.get("params") or {}),
                         cong_cu=cong_cu,
                         ngan_sach=int(params.get("ngan_sach_credit") or 0))
    tt["pha"] = PHA_CONG_CU
    tt["buoc"] = int(tt.get("buoc") or 0) + 1
    tt["cong_cu_dang_goi"] = cong_cu_chon
    su_kien.ghi(db, cha.id, "AgentStep",
                du_lieu={"node_id": nid, "pha": PHA_CONG_CU,
                         "buoc": tt["buoc"], "cong_cu": cong_cu_chon,
                         "tran": tran, "run_con": con.id})
    mtt.chuyen_node(db, cha.id, nid, sang="RUNNING", mo_ta="agent goi cong cu",
                    attempt_number=lan)
    mtt.chuyen_node(db, cha.id, nid, sang="WAITING", mo_ta="cho cong cu",
                    attempt_number=lan,
                    output_ref={KHOA: tt, run_con.KHOA_RUN_CON: con.id})


def _sau_cong_cu(db, cha, nid, tt, ket, params, cong_cu, lan) -> None:
    lich_su = list(tt.get("lich_su") or [])
    lich_su.append({"cong_cu": tt.get("cong_cu_dang_goi", ""),
                    "ket_qua": ket})
    tt["lich_su"] = lich_su[-8:]
    con = _nghi(db, cha, nid, tt, params, cong_cu)
    su_kien.ghi(db, cha.id, "AgentStep",
                du_lieu={"node_id": nid, "pha": PHA_NGHI,
                         "buoc": int(tt.get("buoc") or 0), "run_con": con.id})
    mtt.chuyen_node(db, cha.id, nid, sang="RUNNING", mo_ta="agent nghi tiep",
                    attempt_number=lan)
    mtt.chuyen_node(db, cha.id, nid, sang="WAITING", mo_ta="cho model",
                    attempt_number=lan,
                    output_ref={KHOA: tt, run_con.KHOA_RUN_CON: con.id})


def tiep_buoc(db, cha: WorkflowRun, graph: dict, *, cong_cu=None) -> int:
    """Run con của một node `ai.agent` xong ⇒ đi bước kế. Trả số node đã động.

    Cùng vai với `run_con.ap_ket_qua_con` cho `core.call_workflow`, và cùng lý
    do tồn tại: `WAITING` **không** tự quay về `READY`, nên không có bước này
    thì node agent đứng tới `TRAN_RUN` 20 giờ **với tiền bị giữ**.
    """
    dem = 0
    for n in graph.get("nodes") or []:
        if str(n.get("type")) != LOAI:
            continue
        nid = str(n["id"])
        anh = thi_hanh.anh_chup_hien_tai(db, cha.id, nid)
        if anh is None or anh.execution_status != "WAITING":
            continue
        ra = dict(anh.output_ref or {})
        rid = str(ra.get(run_con.KHOA_RUN_CON) or "")
        con = db.get(WorkflowRun, rid) if rid else None
        if con is None or con.status not in mtt.RUN_KET_THUC:
            continue
        lan = int(anh.attempt_number or 1)
        tt = dict(ra.get(KHOA) or {})
        tt["da_tieu"] = int(tt.get("da_tieu") or 0) + int(con.actual_cost or 0)
        params = dict(n.get("params") or {})
        try:
            if con.status != "SUCCEEDED":
                raise LoiAgent("buoc_agent_loi", f"run con {con.status}")
            ket = _ket_qua_buoc(db, con.id)
            if tt.get("pha") == PHA_NGHI:
                quyet = doc_quyet_dinh(ket.get("content"))
                if quyet.get("xong"):
                    _xong(db, cha, nid, tt, quyet, params, lan)
                else:
                    _buoc_ke(db, cha, nid, tt, quyet, params, cong_cu, lan)
            else:
                _sau_cong_cu(db, cha, nid, tt, ket, params, cong_cu, lan)
        except LoiAgent as loi:
            mtt.chuyen_node(db, cha.id, nid, sang="FAILED",
                            mo_ta="agent dung", error=str(loi)[:2000],
                            attempt_number=lan, output_ref={KHOA: tt})
        dem += 1
    return dem


__all__ = ["KHOA", "LOAI", "MA_LOI", "NUT_BUOC", "PHA_CONG_CU", "PHA_NGHI",
           "TOOL_NGHI", "LoiAgent", "chay_agent", "doc_quyet_dinh",
           "tiep_buoc"]
