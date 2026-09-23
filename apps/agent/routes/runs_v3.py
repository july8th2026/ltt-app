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

## ⛔ Cửa này KHÔNG có `Idempotency-Key`

Trình duyệt bấm hai lần ⇒ hai run. Đó là hành vi ĐÚNG cho một nút bấm tay: hai
lần bấm là hai ý định, và `MAX_RUN_DONG_THOI` (5) là trần chặn tai nạn. Khoá
idempotency là hợp đồng cho **máy** thử lại, và máy đi cửa `/api/v1`.

## Vì sao đọc run trả CẢ node CẢ sự kiện trong một lời gọi

Giao diện vẽ ba thứ cùng lúc: huy hiệu trạng thái trên từng node, dòng thời
gian, và tổng chi phí. Ba endpoint ⇒ ba ảnh chụp lệch nhau vài trăm ms, và
người dùng thấy một node `SUCCEEDED` trong khi dòng thời gian chưa có sự kiện
của nó. Một lời gọi ⇒ một ảnh chụp nhất quán (một transaction).
SSE là plan 13 (spec §19) — xem "Quyết định transport" trong plan 01b.
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _user, _verify_json_csrf, router
from platform_core import credit
from platform_core.i18n import _ as _t
from platform_core.models import Workflow, WorkflowRun, WorkflowVersion
from platform_core.registry import RegistryError
from platform_core.workflow import (dong_co, may_trang_thai, su_kien,
                                    tao_run, thi_hanh)
from server.auth.session import require_login
from server.deps import get_db

_NO_STORE = {"Cache-Control": "no-store"}

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


def _nodes_json(db: Session, run: WorkflowRun) -> list[dict]:
    """Trạng thái hiện tại của MỌI node trong đồ thị đã ghim.

    ⭐ Duyệt theo danh sách node của **version**, không theo các ảnh chụp đã
       có: node chưa chạy phải xuất hiện với `PENDING`. Nếu chỉ liệt kê node
       đã có ảnh chụp, giao diện thấy đồ thị "mọc dần" và không phân biệt được
       "chưa tới lượt" với "không nằm trong bản đã publish".
    """
    ver = db.get(WorkflowVersion, run.version_id)
    do_thi = (ver.graph if ver is not None else {}) or {}
    ra: list[dict] = []
    for nut in do_thi.get("nodes") or []:
        nid = str(nut.get("id") or "")
        anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid)
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
                     _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    body = await request.json() if await request.body() else {}
    _verify_json_csrf(request, body if isinstance(body, dict) else {})
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
        run, _moi = tao_run.tao_run(
            db, workflow=wf, owner_id=user.id, trigger_kind="manual",
            idempotency_key="", inputs=inputs)
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
    return JSONResponse(_run_json_v3(db, run), status_code=201,
                        headers=_NO_STORE)


@router.get("/api/v3/runs/{run_id}")
def v3_doc_run(request: Request, run_id: str, sau: int = Query(0, ge=0),
               _identity: str = Depends(require_login),
               db: Session = Depends(get_db)):
    user = _user(request)
    run = _run_cua_toi(db, run_id, user.id)
    return JSONResponse(_run_json_v3(db, run, sau=sau), headers=_NO_STORE)


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
