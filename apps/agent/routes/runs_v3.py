"""Cửa v3 cho MỘT LƯỢT CHẠY — Canvas chỉ gọi đường này (spec §13.1).

## ⭐ Vì sao cửa này được mở, trong khi `drafts_v3.py` từ chối mở nó

`drafts_v3.py` viết: *"Chạy một workflow đi qua `/api/v1/workflows/{id}/runs`,
nơi có báo giá đã ký, `Idempotency-Key` và một khoản giữ chỗ"*. Câu đó đúng lúc
nó được viết, và **vẫn đúng** — nhưng thứ nó bảo vệ là **ba bất biến**, không
phải **một URL**. Kể từ 01a, cả ba sống trong `tao_run.tao_run()`:

    giữ chỗ tiền     `tien.giu_cho_run` trong cùng savepoint với INSERT
    idempotency      `ux_workflow_run_idem` + `TrungKhoaKhacWorkflow`
    hạn mức          `MAX_RUN_DONG_THOI`

Cửa này gọi đúng hàm đó, nên nó KHÔNG phải đường chạy thứ hai — nó là cửa thứ
hai của **cùng một** đường. Thứ nó bỏ so với `/api/v1` là **báo giá đã ký**, và
bỏ có lý do: quote token ký là hợp đồng với một **khách API** (giá phải bất biến
giữa lúc chào và lúc chạy, qua hai request của hai tiến trình). Người đang mở
Canvas vừa bấm publish xong giây trước; giá anh ta thấy đến từ chính
`version.estimated_max` mà `tao_run` đọc lại. Ký một token để tự mình kiểm lại
trong cùng một phiên là nghi thức, không phải bảo đảm.

## ⭐ Cửa này ĐÒI `Idempotency-Key` (sửa 23/09 — đo được là trừ tiền hai lần)

Bản đầu viết: *"Trình duyệt bấm hai lần ⇒ hai run. Đó là hành vi ĐÚNG cho một
nút bấm tay: hai lần bấm là hai ý định, và `MAX_RUN_DONG_THOI` (5) là trần chặn
tai nạn."* Câu đó **sai**, và sai ở chỗ đắt nhất:

* "hai lần bấm là hai ý định" chỉ đúng khi người dùng CHỦ Ý bấm hai lần. Bấm
  đúp, mạng chậm rồi bấm lại, React gọi lại handler — đều là MỘT ý định.
* `MAX_RUN_DONG_THOI` không phải cái rào cho việc này: nó chặn run **thứ 6**
  (429). Run thứ hai vẫn tạo, vẫn `tien.giu_cho_run`, vẫn **trừ tiền lần hai**.
  Một hạn mức đồng thời không bao giờ là hàng rào chống bấm đúp.

Đã đo qua HTTP trên app thật (23/09): hai POST ⇒ hai run, hai khoản giữ chỗ.

### Thiếu header thì trả 400, KHÔNG cho qua

Đây là câu hỏi đã có **một câu trả lời của nền tảng**, ghi trong
`platform_core/public_api/idempotency.require_key`: *"Required rather than
optional on chargeable routes: making it optional means the safe path is the one
a client has to remember, and the unsafe one is the default."* Cửa này tiêu tiền
⇒ cùng một luật, và dùng lại luôn hằng độ dài khoá của nó thay vì đặt luật thứ
hai.

⛔ **Máy chủ TUYỆT ĐỐI không tự sinh khoá.** Mỗi request một khoá mới thì hai
   lần bấm vẫn là hai khoá khác nhau: không chống được gì, mà lại trông như có
   chống — tệ hơn hẳn không làm gì, vì nó dập tắt câu hỏi.

Khoá phải sinh ở chỗ biết được "một ý định": **handler của nút bấm**, một
`crypto.randomUUID()` mỗi lần bấm, giữ nguyên qua mọi lần thử lại của cùng lần
bấm đó. Đó là việc của `frontend/agent-canvas` — cửa này chỉ từ chối cho to
tiếng khi client quên, thay vì im lặng trừ tiền hai lần.

## Vì sao đọc run trả CẢ node CẢ sự kiện trong một lời gọi

Giao diện vẽ ba thứ cùng lúc: huy hiệu trạng thái trên từng node, dòng thời
gian, và tổng chi phí. Ba endpoint ⇒ ba ảnh chụp lệch nhau vài trăm ms, và
người dùng thấy một node `SUCCEEDED` trong khi dòng thời gian chưa có sự kiện
của nó. Một lời gọi ⇒ một ảnh chụp nhất quán (một transaction).
SSE là plan 13 (spec §19) — xem "Quyết định transport" trong plan 01b.

## SSE (P9 task 1) — vì sao KHÔNG thêm `sse-starlette`

Plan chốt "Dùng lại: `sse-starlette`", nhưng gói đó KHÔNG có trong
`requirements*.txt` và `pip show sse-starlette` báo "not found" trên máy này
(đo 24/09). Trong khi đó `text/event-stream` qua `StreamingResponse` thuần đã
sống VÀ CHẠY THẬT ở hai cửa khác của chính kho này —
`apps/agent/routes/assistant.py:130` (SSE phân tích Assistant) và
`server/api/streaming.py:949,1081` (SSE chat LLM). Thêm một thư viện ngoài để
làm lại đúng việc hai cửa kia đã làm là "tự viết" theo nghĩa xấu (thêm một
đường thứ hai cho cùng một giao thức), không phải "dùng lại" — nên cửa này
dùng lại NGUYÊN khuôn `StreamingResponse(..., media_type="text/event-stream")`
đã có trong `apps/agent/routes/assistant.py`, không phải khuôn ngoài.

⭐ Cửa này CỐ Ý là `GET` thuần, để frontend dùng `EventSource` gốc của trình
   duyệt thay vì tự `fetch()`. Đây là chỗ né đúng con nợ đã khai (P9 brief
   #1): `previewAssistant` tự `fetch()` qua `apiFetch()` (`workflowApi.ts`),
   một hàm gắn `Accept: application/json` cho MỌI request — kể cả khi request
   đó đang mở một luồng SSE, sai giao thức. `EventSource` không đi qua hàm đó:
   trình duyệt tự gắn đúng `Accept: text/event-stream`, nên lớp lỗi ấy không
   có đường vào nếu (và chỉ nếu) phía Canvas gọi `new EventSource(url)` thay
   vì `apiFetch()`.

⭐ Con trỏ đọc tiếp ưu tiên `Last-Event-ID` (header `EventSource` TỰ gắn khi
   nối lại) hơn `?sau=` (chỉ đúng ở lần connect ĐẦU): nhờ vậy trình duyệt tự
   phục hồi đúng chỗ sau khi máy chủ chủ động đóng ở mốc `_SSE_DONG_SAU_S`,
   không cần JavaScript tự viết logic nối lại — đó là hành vi có sẵn của
   `EventSource`.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime

from fastapi import Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _user, _verify_json_csrf, router
from platform_core import credit
from platform_core.i18n import _ as _t
from platform_core.models import Workflow, WorkflowRun, WorkflowVersion
# Dùng lại hằng độ dài khoá của cửa `/api/v1` — một luật, hai cửa. Đặt một trần
# thứ hai ở đây là mời hai cửa cùng nền tảng trả lời khác nhau cho cùng câu hỏi.
from platform_core.public_api.idempotency import (MAX_KEY_LENGTH,
                                                  MIN_KEY_LENGTH)
from platform_core.registry import RegistryError
from platform_core.workflow import (bao_gia, dong_co, may_trang_thai, su_kien,
                                    tao_run, thi_hanh)
from server.auth.session import require_login
from server.deps import get_db

_NO_STORE = {"Cache-Control": "no-store"}

#: `X-Accel-Buffering: no` — cùng header hai cửa SSE kia đã dùng (Cloudflare/
#: proxy trung gian không được gộp byte lại chờ đầy buffer).
_SSE_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}

#: Nhịp quét CSDL phía máy chủ — đúng con số spec §14 ghi ("poll CSDL 1 s").
_SSE_NHIP_S = 1.0

#: Đóng chủ động trước trần 100 s của Cloudflare (spec §14: "đóng sau 90 s").
#: `EventSource` tự nối lại cùng URL, mang theo `Last-Event-ID`.
_SSE_DONG_SAU_S = 90.0

#: Trần kích thước `inputs` do người dùng gõ — nó đi thẳng vào
#: `WorkflowStarted.du_lieu["inputs"]` (`tao_run.py`), sống 90 ngày trong
#: `workflow_event` (`su_kien.RETENTION_DAYS`), cùng LÝ DO với trần đầu ra
#: node (`cau_noi.GIOI_HAN_DAU_RA`): một payload khổng lồ không nên nằm mãi
#: trong nhật ký sự kiện.
#:
#: ⚠️ PHẢI nhỏ hơn `server/request_body_limit.AGENT_BODY_LIMIT` (128 KiB —
#: trần CHUNG cho mọi body POST/PUT/PATCH dưới `/agent/`), nếu không nhánh
#: này chết: request đã bị middleware trả 413 trước khi route kịp chạy.
#: Chọn NỬA trần đó — đủ rộng cho `inputs` có thật, và còn khoảng cách rõ với
#: 128 KiB để phép kiểm (và chính nhánh này) không phụ thuộc hai trần trùng
#: khít nhau.
_GIOI_HAN_INPUTS = 64 * 1024


def _khoa_idempotency(raw: str) -> str:
    """Khoá do CLIENT cấp, bắt buộc. Xem mục ⭐ ở đầu tệp vì sao không sinh hộ.

    Từ chối 400 chứ không cho qua: cửa này tiêu tiền, và một mặc định "cho qua"
    biến đường AN TOÀN thành đường khách phải nhớ, đường NGUY HIỂM thành mặc
    định — nguyên văn lý do của `public_api/idempotency.require_key`.
    """
    khoa = str(raw or "").strip()
    if not khoa:
        raise HTTPException(status_code=400, detail={
            "ma": "thieu_idempotency_key",
            "thong_diep": _t('Can header "Idempotency-Key" cho moi lan chay.')})
    if not MIN_KEY_LENGTH <= len(khoa) <= MAX_KEY_LENGTH:
        # Trần dưới giữ "1"/"retry" ra khỏi bảng: những giá trị đó đụng nhau
        # giữa hai request không liên quan, và khi đó idempotency KHÔNG cứu
        # người dùng mà làm hại họ — lần chạy thứ hai bị nuốt thành phát lại.
        raise HTTPException(status_code=400, detail={
            "ma": "idempotency_key_khong_hop_le",
            "thong_diep": _t('Idempotency-Key phai dai %(min)d den %(max)d ky tu.')
            % {"min": MIN_KEY_LENGTH, "max": MAX_KEY_LENGTH}})
    return khoa


def _iso(v: datetime | None) -> str | None:
    return v.isoformat() if v is not None else None


def _wf_cua_toi(db: Session, workflow_id: str, user_id: str) -> Workflow:
    """Lọc chủ sở hữu NGAY TRONG truy vấn — "không có" và "của người khác"
    phải cùng trả 404, nếu không một người lạ dò được id nào có thật."""
    wf = db.execute(select(Workflow).where(
        Workflow.id == str(workflow_id or ""),
        Workflow.owner_id == user_id)).scalars().first()
    if wf is None:
        raise HTTPException(status_code=404,
                            detail=_t('Không tìm thấy workflow.'))
    return wf


def _run_cua_toi(db: Session, run_id: str, user_id: str) -> WorkflowRun:
    run = db.execute(select(WorkflowRun).where(
        WorkflowRun.id == str(run_id or ""),
        WorkflowRun.owner_id == user_id)).scalars().first()
    if run is None:
        raise HTTPException(status_code=404,
                            detail=_t('Không tìm thấy lượt chạy.'))
    return run


#: Đường thi hành bị BĂM (`danh_thuc.duong_thi_hanh`, vượt 64 ký tự) luôn bắt
#: đầu bằng ký tự này — phải khớp `platform_core.workflow.danh_thuc._TIEN_TO_BAM`
#: (chữ riêng, không xuất `__all__`; ký tự `#` không nằm trong tập id hợp lệ
#: của `bien_dich._ID`, nên không đụng một khoá đường-thật, xem docstring gốc).
_TIEN_TO_BAM = "#"

#: Trạng thái hiển thị khi một node THÂN `foreach` có lượt thực thi bị BĂM
#: (xem `_gop_than_foreach`) — KHÔNG dùng `PENDING`. `PENDING` giả là lời NÓI
#: DỐI: node có thể đang `RUNNING` hoặc đã `FAILED`, và một người vận hành tin
#: `PENDING` sẽ bấm HUỶ một việc đang chạy ĐÚNG (P9 brief task 3, 🔴 "một màn
#: hình nói sai trạng thái còn tệ hơn một màn hình không nói gì").
TRANG_THAI_KHONG_XAC_DINH = "KHONG_XAC_DINH"


def _gop_than_foreach(db: Session, run: WorkflowRun,
                      do_thi: dict) -> tuple[dict, frozenset]:
    """`({node_id trần: trạng thái GỘP}, {node_id trần bị BĂM che mất})`.

    Một node thân chạy N lần, mỗi lần một hàng `node_run` mang đường thi hành
    (`f:0/x`). Giao diện chỉ có MỘT ô cho node ấy trên Canvas, nên phải gộp:

      - còn lượt chưa kết thúc ⇒ `RUNNING` (người dùng thấy nó đang chạy);
      - có lượt hỏng ⇒ `FAILED` (⛔ không giấu: một vòng hỏng là một việc hỏng);
      - còn lại ⇒ `SUCCEEDED`.

    `cost_credit` CỘNG mọi lượt; `attempt` là **số lượt**, không phải số lần thử
    của một lượt — nói ra ở đây vì hai con số ấy dễ bị đọc nhầm nhau.

    ## 🔴 Đường thi hành bị BĂM — vì sao phần tử thứ hai của cặp trả về tồn tại

    `foreach` lồng sâu + id dài ⇒ `danh_thuc.duong_thi_hanh` băm (`#<sha256>`,
    KHÔNG còn `/`). Khoá đó không khớp hậu tố `/<node_id>` nữa — và vì hash
    một chiều, KHÔNG có cách nào trong tầng quan sát (không đụng schema, không
    đụng động cơ — ranh giới của lượt p9-quan-sat) suy ngược lại nó thuộc
    node_id trần nào. Đã cân nhắc brute-force mọi tổ hợp `(tên_vòng, chỉ_số)`
    tới `max_items`: chi phí là TÍCH `max_items` qua mọi tầng lồng (spec đang
    để `foreach` tới 1000 phần tử), tức không có trần trên — không chấp nhận
    được cho một endpoint bị gọi mỗi 1 s (SSE task 1) hay mỗi lần poll.

    ⇒ Thay vì ÂM THẦM bỏ qua (hành vi cũ — để lại `PENDING` giả), hàm này trả
      thêm tập TẤT CẢ node nằm trong thân của MỌI `foreach` trong đồ thị mà
      bản thân KHÔNG có một khoá chưa-băm nào khớp. Diện phủ RỘNG hơn cần
      thiết (có thể đánh dấu cả node không hề bị băm) là lựa chọn CÓ CHỦ Ý:
      giữa "có thể thừa một cảnh báo" và "chắc chắn thiếu một cảnh báo", cái
      trước rẻ hơn — nó không bao giờ khiến người vận hành tin nhầm một việc
      đang chạy là chưa bắt đầu.
    """
    from platform_core.models import NodeRun

    gom: dict[str, list] = {}
    co_khoa_bam = False
    for hang in db.query(NodeRun).filter_by(run_id=run.id).all():
        khoa = str(hang.node_id)
        if khoa.startswith(_TIEN_TO_BAM):
            co_khoa_bam = True
            continue
        if "/" not in khoa:
            continue
        gom.setdefault(khoa.rsplit("/", 1)[1], []).append(khoa)

    ra: dict[str, dict] = {}
    for nid, khoas in gom.items():
        anhs = [a for a in (thi_hanh.anh_chup_theo_khoa(db, run.id, k)
                            for k in khoas) if a is not None]
        if not anhs:
            continue
        tt = [a.execution_status for a in anhs]
        if any(t not in may_trang_thai.NODE_KET_THUC for t in tt):
            gop = "RUNNING"
        elif any(t in ("FAILED", "ABANDONED", "CANCELLED") for t in tt):
            gop = "FAILED"
        else:
            gop = "SUCCEEDED"
        loi = next((a.error for a in anhs if a.error), "")
        ra[nid] = {"status": gop, "attempt": len(anhs),
                   "cost_credit": sum(int(a.cost_credit or 0) for a in anhs),
                   "job_id": "", "error": loi}

    khong_xac_dinh: frozenset = frozenset()
    if co_khoa_bam:
        ung_vien: set[str] = set()
        try:
            for _dong, than in bao_gia.than_foreach(do_thi).values():
                ung_vien.update(than)
        except bao_gia.KhongBaoGiaDuoc:
            # Đồ thị không tự bao giá được (cặp foreach/foreach_end hỏng) —
            # đã bị validator publish chặn trong ĐA SỐ ca, nhưng đây là JSON
            # đã GHIM (`version.graph`) từ một publish cũ hơn luật hiện hành;
            # không đoán thân, chỉ đơn giản không đánh dấu thêm node nào.
            ung_vien = set()
        khong_xac_dinh = frozenset(n for n in ung_vien if n not in ra)
    return ra, khong_xac_dinh


def _nodes_json(db: Session, run: WorkflowRun) -> list[dict]:
    """Trạng thái hiện tại của MỌI node trong đồ thị đã ghim.

    ⭐ Duyệt theo danh sách node của **version**, không theo các ảnh chụp đã
       có: node chưa chạy phải xuất hiện với `PENDING`. Nếu chỉ liệt kê node
       đã có ảnh chụp, giao diện thấy đồ thị "mọc dần" và không phân biệt được
       "chưa tới lượt" với "không nằm trong bản đã publish".
    """
    ver = db.get(WorkflowVersion, run.version_id)
    do_thi = (ver.graph if ver is not None else {}) or {}
    theo_than, khong_xac_dinh = _gop_than_foreach(db, run, do_thi)
    ra: list[dict] = []
    for nut in do_thi.get("nodes") or []:
        nid = str(nut.get("id") or "")
        anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid)
        if anh is None and nid in theo_than:
            # ⭐ Node THÂN `foreach`: trạng thái của nó không nằm ở khoá id
            #    trần mà ở các ĐƯỜNG THI HÀNH `f:0/x`, `f:1/x`… Gộp chúng lại
            #    dưới đúng `node_id` trần — giao diện (`CanvasShell.tsx` so
            #    `item.node_id === node.id`) vì vậy KHÔNG phải sửa.
            ra.append(theo_than[nid] | {"node_id": nid})
            continue
        if anh is None and nid in khong_xac_dinh:
            # ⛔ KHÔNG `PENDING` — xem `TRANG_THAI_KHONG_XAC_DINH`.
            ra.append({
                "node_id": nid, "status": TRANG_THAI_KHONG_XAC_DINH,
                "attempt": 0, "cost_credit": 0, "job_id": "",
                "error": _t('Không gộp được trạng thái: một đường thi hành '
                            'trong vòng lặp lồng sâu đã bị băm (quá 64 ký '
                            'tự), không thể biết chắc đây có phải node này.')})
            continue
        if anh is None:
            # Chưa có ảnh chụp nào ⇒ chưa từng thử: `attempt: 0`, không phải
            # `1` — `1` sẽ nói dối rằng node đã chạy một lượt.
            ra.append({"node_id": nid, "status": may_trang_thai.NODE_BAT_DAU,
                       "attempt": 0, "cost_credit": 0, "job_id": "",
                       "error": ""})
            continue
        ra.append({
            "node_id": nid,
            "status": anh.execution_status,
            "attempt": int(anh.attempt_number),
            "cost_credit": int(anh.cost_credit),
            "job_id": anh.job_id,
            "error": anh.error,
        })
    return ra


def _run_json_v3(db: Session, run: WorkflowRun, *, sau: int = 0) -> dict:
    sau = int(sau or 0)
    su = su_kien.doc(db, run.id, sau=sau)
    # ⭐ Con trỏ poll đến từ CHÍNH LÔ vừa trả, không phải từ một truy vấn thứ
    #    hai hỏi lại bảng.
    #
    #    `su_kien.doc()` + `su_kien.seq_cuoi()` là HAI truy vấn. Ở READ
    #    COMMITTED (mặc định của PostgreSQL), động cơ commit một sự kiện vào
    #    đúng khe giữa hai truy vấn đó ⇒ `seq_cuoi` trả về một con trỏ **vượt
    #    qua** lô vừa gửi cho client. Client xin nhịp sau từ con trỏ mới, nên
    #    những sự kiện nằm giữa **không bao giờ được gửi**: mất VĨNH VIỄN.
    #    `nhapRun` phía client chống TRÙNG (bỏ seq đã có) chứ không chống
    #    THIẾU — không ai phát hiện, dòng thời gian chỉ đơn giản khuyết.
    #
    #    Lấy `su[-1].seq` thì con trỏ không thể vượt quá thứ đã gửi: cùng lắm
    #    là lùi lại, và lùi chỉ gây gửi TRÙNG — thứ client đã chống được.
    #
    #    Lô RỖNG (`sau=` đã ở cuối) ⇒ giữ nguyên con trỏ khách đang cầm. Trả
    #    `0` ở đây sẽ làm con trỏ lùi về đầu và gửi lại toàn bộ lịch sử mỗi
    #    nhịp — đúng thứ `su_kien.seq_cuoi()` từng đứng đây để tránh.
    #
    #    Bớt luôn một truy vấn mỗi nhịp poll (1,5 giây/lần, mỗi Canvas đang mở).
    return {
        "id": run.id,
        "workflow_id": run.workflow_id,
        "version_id": run.version_id,
        "status": run.status,
        "credit_max": int(run.estimated_max or 0),
        "credit_charged": int(run.actual_cost or 0),
        "settled": run.ket_so_luc is not None,
        "created_at": _iso(run.created_at),
        "nodes": _nodes_json(db, run),
        "su_kien": [{"seq": e.seq, "loai": e.loai, "node_id": e.node_id,
                     "du_lieu": dict(e.du_lieu or {}),
                     "created_at": _iso(e.created_at)} for e in su],
        "seq_cuoi": su[-1].seq if su else sau,
    }


@router.post("/api/v3/workflows/{workflow_id}/runs")
async def v3_tao_run(request: Request, workflow_id: str,
                     idempotency_key: str = Header(default="",
                                                   alias="Idempotency-Key"),
                     _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    body = await request.json() if await request.body() else {}
    _verify_json_csrf(request, body if isinstance(body, dict) else {})
    khoa = _khoa_idempotency(idempotency_key)
    user = _user(request)
    wf = _wf_cua_toi(db, workflow_id, user.id)
    # ⭐ `inputs` đến thẳng từ khách, chưa qua `params_schema` của tool nào —
    # `dict(raw or {})` trên MỘT list/chuỗi ném `TypeError`/`ValueError` TRƯỚC
    # khi `tao_run` kịp chạy, nên đây là 500 duy nhất còn sót trên cửa tiêu
    # tiền (task-2-review.md, Important #2). Kiểm kiểu tường minh ⇒ 422 có mã.
    raw_inputs = (body or {}).get("inputs") if isinstance(body, dict) else None
    if raw_inputs is not None and not isinstance(raw_inputs, dict):
        raise HTTPException(status_code=422, detail={
            "ma": "inputs_khong_hop_le",
            "thong_diep": _t('Truong "inputs" phai la mot object.')})
    inputs = dict(raw_inputs or {})
    # ⭐ Đếm BYTE, không đếm ký tự. `ensure_ascii` mặc định biến mỗi chữ tiếng
    #    Việt thành một dãy `\uXXXX` 6 ký tự cho 2-3 byte thật, nên
    #    `len(json.dumps(...))` siết payload tiếng Việt gắt gấp ~2-3 lần so với
    #    chính con số "byte" mà thông điệp lỗi ngay dưới đây hứa với khách.
    do_dai = len(json.dumps(inputs, default=str,
                            ensure_ascii=False).encode("utf-8"))
    if do_dai > _GIOI_HAN_INPUTS:
        raise HTTPException(status_code=422, detail={
            "ma": "inputs_qua_lon",
            "thong_diep": _t('Du lieu "inputs" vuot qua %(n)d byte.')
            % {"n": _GIOI_HAN_INPUTS}})
    try:
        run, moi = tao_run.tao_run(
            db, workflow=wf, owner_id=user.id, trigger_kind="manual",
            idempotency_key=khoa, inputs=inputs)
    except tao_run.TrungKhoaKhacWorkflow:
        # Cùng khoá, KHÁC workflow ⇒ không phải một lần thử lại mà là hai ý
        # định khác nhau đội chung một khoá. Phát lại run cũ ở đây sẽ trả về
        # một run của workflow mà khách không hề gọi.
        raise HTTPException(status_code=409, detail={
            "ma": "khoa_dung_cho_workflow_khac",
            "thong_diep": _t('Idempotency-Key nay da dung cho workflow khac.')
        }) from None
    except tao_run.KhongCoBanPublish as loi:
        raise HTTPException(status_code=422, detail={
            "ma": "chua_publish", "thong_diep": str(loi)}) from None
    except tao_run.QuaHanMuc as loi:
        raise HTTPException(status_code=429, detail={
            "ma": "qua_han_muc", "thong_diep": str(loi)}) from None
    except credit.ThieuCreditError as loi:
        raise HTTPException(status_code=402, detail={
            "ma": "thieu_credit", "thong_diep": str(loi)}) from None
    except RegistryError as loi:
        # `chu_dong_co()` (gọi trong `tao_run` → `danh_thuc_dong_co`) ném cái
        # này khi KHÔNG app nào khai `job_type` của động cơ — sự cố cấu hình
        # thật (`2d3e3c41` phải đăng ký lại `apps/agent_dong_co` "ở mọi điểm
        # ratchet" vì đúng lỗi này), không phải lỗi của khách. 503 có mã, để
        # Canvas phân biệt được với một 500 chung chung.
        raise HTTPException(status_code=503, detail={
            "ma": "dong_co_chua_san_sang", "thong_diep": str(loi)}) from None
    db.commit()
    db.refresh(run)
    # 201 = vừa tạo · 200 = phát lại run đã có. Cùng quy ước với cửa `/api/v1`
    # (`server/api/workflows.py`), để một người dùng cả hai cửa không phải học
    # hai luật. Client phân biệt được "lần bấm này tạo run" với "lần bấm này
    # trùng lần trước" mà không phải so id.
    return JSONResponse(_run_json_v3(db, run), status_code=201 if moi else 200,
                        headers=_NO_STORE)


@router.get("/api/v3/runs/{run_id}")
def v3_doc_run(request: Request, run_id: str, sau: int = Query(0, ge=0),
               _identity: str = Depends(require_login),
               db: Session = Depends(get_db)):
    user = _user(request)
    run = _run_cua_toi(db, run_id, user.id)
    return JSONResponse(_run_json_v3(db, run, sau=sau), headers=_NO_STORE)


@router.get("/api/v3/runs/{run_id}/su-kien")
async def v3_su_kien_sse(request: Request, run_id: str, sau: int = Query(0, ge=0),
                         last_event_id: str = Header(default="",
                                                     alias="Last-Event-ID"),
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    """SSE cho MỘT run đang chạy (spec §14, phase 13 task 1). Xem docstring
    đầu tệp mục "SSE (P9 task 1)" cho lý do khuôn + vì sao không phải cửa thứ
    hai của giao thức poll.

    Mỗi nhịp gửi LẠI TOÀN BỘ `nodes` (rẻ — đúng khối lượng đọc mà
    `GET /runs/{id}` polling vẫn làm mỗi 1,5 s hôm nay) cộng phần `su_kien`
    MỚI kể từ mốc đã gửi. `id:` của sự kiện SSE là `seq_cuoi` — không phải để
    trang trí: đó là giá trị `EventSource` gửi lại trong header
    `Last-Event-ID` khi tự nối lại, nên một lần đóng-mở của máy chủ không làm
    mất hay lặp một `workflow_event` nào.
    """
    user = _user(request)
    _run_cua_toi(db, run_id, user.id)  # 404 sớm nếu không phải run của mình
    # `Last-Event-ID` (client tự gắn khi NỐI LẠI) thắng `?sau=` (chỉ đúng ở
    # lần connect ĐẦU) — cùng lý do ghi trong docstring đầu tệp.
    try:
        moc_khoi_dau = int(last_event_id) if last_event_id.strip() else int(sau)
    except ValueError:
        moc_khoi_dau = int(sau)

    async def luong():
        vi_tri = max(0, moc_khoi_dau)
        bat_dau = asyncio.get_event_loop().time()
        while True:
            if await request.is_disconnected():
                return
            # ⭐ `expire_all()` trước mỗi vòng: session của request được TÁI
            #    DÙNG suốt vòng đời stream (không phải một session/tick), nên
            #    không có nó thì SQLAlchemy identity map trả lại đúng các
            #    object đã nạp ở tick trước — "đọc CSDL mỗi giây" sẽ chỉ là
            #    đọc lại cache của chính nó.
            db.expire_all()
            run = _run_cua_toi(db, run_id, user.id)
            goi = _run_json_v3(db, run, sau=vi_tri)
            vi_tri = int(goi["seq_cuoi"])
            yield (f"id: {vi_tri}\nevent: run\ndata: "
                  + json.dumps(goi, ensure_ascii=False, default=str)
                  + "\n\n")
            if run.status in may_trang_thai.RUN_KET_THUC:
                # Run đã kết thúc: sẽ không còn gì đổi nữa, đóng luôn thay vì
                # ngồi quét vô ích tới mốc 90 s.
                yield "event: dong\ndata: {}\n\n"
                return
            if asyncio.get_event_loop().time() - bat_dau >= _SSE_DONG_SAU_S:
                # Dưới trần 100 s của Cloudflare (luật dự án #8). `EventSource`
                # tự nối lại, mang `Last-Event-ID`, nên không mất gì.
                return
            await asyncio.sleep(_SSE_NHIP_S)

    return StreamingResponse(luong(), media_type="text/event-stream",
                             headers=_SSE_HEADERS)


@router.post("/api/v3/runs/{run_id}/cancel")
async def v3_huy_run(request: Request, run_id: str,
                     _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    body = await request.json() if await request.body() else {}
    _verify_json_csrf(request, body if isinstance(body, dict) else {})
    user = _user(request)
    run = _run_cua_toi(db, run_id, user.id)
    # ⭐ `huy_run` trả `False` khi run ĐÃ ở trạng thái kết thúc. Đó không phải
    #    lỗi hệ thống (500) và cũng không phải thành công (200): thao tác
    #    KHÔNG xảy ra, và lý do đọc được bằng máy.
    if not dong_co.huy_run(db, run.id, "nguoi dung huy tren Canvas"):
        db.rollback()
        raise HTTPException(status_code=409, detail={
            "ma": "da_ket_thuc",
            "thong_diep": _t('Lượt chạy đã kết thúc.')})
    db.commit()
    db.refresh(run)
    return JSONResponse(_run_json_v3(db, run), headers=_NO_STORE)
