"""``/api/v1/workflows`` và ``/api/v1/runs`` — chạy workflow qua API công khai.

Nguồn: `02 §WF-802`. Nó đòi **năm** bề mặt và đòi chúng đi qua *"đúng hạ tầng
đã có: inventory, scope, idempotency, rate limit, SYNC/ASYNC_JOB, webhook HMAC.
**Không dựng bộ máy API thứ hai.**"*

Nên tệp này mỏng đúng như `jobs.py`: phân tích, xác thực, uỷ quyền, rồi giao cho
`platform_core.workflow.*`. Ranh giới transaction là chính request
(`server.deps.get_db` commit khi handler trả về, rollback khi nó ném) — đó là
thứ làm *"khoản giữ và lượt chạy cùng sống hoặc cùng chết"* đúng mà không cần
nghi thức gì.

## ⭐ VÌ SAO CÓ `/quotes` RIÊNG CHO WORKFLOW

`POST /api/v1/quotes` định giá `(tool, input)`. Một workflow thì báo giá gắn với
**graph đã publish**, và nó trả **HAI** số (`M8`): trần tất định và một ước
tính. Cùng bộ máy ký (`quotes.issue`), khác thứ được ký — nên đây là *dùng lại*,
không phải *dựng thêm*.

## 🔴 `chargeable=True` CHỈ TRUNG THỰC TỪ 08/09/2026

`protocol.check_mode_rules` bắt một `ASYNC_JOB` chargeable phải đòi cả quote lẫn
`Idempotency-Key`. Nhưng trước khi `platform_core/workflow/tien.py` tồn tại,
**không gì trong `platform_core/workflow/` chạm sổ credit** — `hold_id` chỉ từng
bị *xoá*, chưa từng được *đặt*. Khai `chargeable=True` khi ấy là một lời hứa
không có gì đứng sau: một route công khai cho người lạ khởi động một lượt chạy
nhiều node (mỗi node có thể là **20 phút A100**) mà không giữ một credit nào.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import Body, Depends, Header, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core import credit
from platform_core.models import (Artifact, NodeRunSnapshot, Workflow,
                                  WorkflowRun, WorkflowVersion)
from platform_core.public_api import idempotency, quotes
from platform_core.public_api.errors import (conflict, insufficient_credit,
                                             invalid_request, not_found)
from platform_core.public_api.principal import Principal
from platform_core.public_api.scopes import (SCOPE_WORKFLOWS_CANCEL,
                                             SCOPE_WORKFLOWS_READ,
                                             SCOPE_WORKFLOWS_RUN)
from platform_core.workflow import bao_gia, may_trang_thai, thi_hanh, tien
from server.api.auth import require_scope
# ⛔ DUNG LAI, khong chep. Chu thich cua chinh ham do canh bao dung cai bay
#    toi vua dinh: `request.app` ben trong mot sub-app la SUB-APP, nen voi
#    toi cau hinh cua app cha se khong thay gi va **am tham tat bao gia**.
#    Mot ban sao cua ham nay la mot ban sao co the troi khoi ban goc.
from server.api.jobs import _quote_secret
from server.deps import get_db

log = logging.getLogger("server.api.workflows")

_NO_STORE = {"Cache-Control": "no-store"}
OPERATION_START_RUN = "workflows.run"

#: Tiền tố khoá báo giá. `quotes.issue` ký một `tool_name` bất kỳ, nên tiền tố
#: này là thứ ngăn một báo giá tool bị nộp vào cửa workflow và ngược lại.
_KHOA_BAO_GIA = "workflow:"


def _iso(v: datetime | None) -> str | None:
    if v is None:
        return None
    return v.replace(tzinfo=v.tzinfo or timezone.utc).isoformat()


def _cua_toi(db: Session, lop, ma: str, principal: Principal):
    """Lấy một hàng **đã lọc theo chủ sở hữu**, hoặc 404.

    ⛔ Lọc ngay trong truy vấn chứ không lấy rồi mới so: *"không tìm thấy"* và
       *"của người khác"* phải trả về **cùng một** 404, nếu không một người lạ
       dò được id nào có thật.
    """
    hang = db.execute(
        select(lop).where(lop.id == str(ma or ""),
                          lop.owner_id == principal.user_id)).scalars().first()
    if hang is None:
        raise not_found("Not found.")
    return hang


def _ban_publish(db: Session, wf: Workflow) -> WorkflowVersion:
    """Bản đã xuất bản mà run sẽ **ghim**. Chưa publish ⇒ từ chối.

    ⚠️ `WF-801` đòi mọi trigger **ghim version** — chạy bản đã publish, không
       chạy bản nháp. Đường API là một trigger, nên nó không được ngoại lệ:
       chạy bản nháp qua API nghĩa là hai lượt chạy cùng một `workflow_id` có
       thể có nội dung khác nhau mà không gì ghi lại điều đó.
    """
    if not wf.published_version_id:
        raise conflict("This workflow has no published version to run.")
    ver = db.get(WorkflowVersion, wf.published_version_id)
    if ver is None or ver.workflow_id != wf.id:
        raise conflict("This workflow has no published version to run.")
    return ver


def _cong_khai_run(run: WorkflowRun) -> dict:
    return {
        "id": run.id,
        "workflow_id": run.workflow_id,
        "version_id": run.version_id,
        "status": run.status,
        "trigger": run.trigger_kind,
        # ⭐ HAI số, luôn cùng nhau. `estimated_max` là thứ khách đã đồng ý;
        #    `actual_cost` là thứ thật sự thu. Trả một số duy nhất là buộc
        #    người đọc đoán số kia (`M8`).
        "credit_max": int(run.estimated_max or 0),
        "credit_charged": int(run.actual_cost or 0),
        "settled": run.ket_so_luc is not None,
        "created_at": _iso(run.created_at),
    }


def register_workflow_routes(api, config, tag: str) -> None:
    """Mắc năm route của `WF-802`."""

    @api.post("/workflows/{workflow_id}/quotes", tags=[tag],
              summary="Price a workflow run before starting it",
              description=("Returns a signed quote bound to this account and "
                           "the published graph. Submit it to POST "
                           "/workflows/{workflow_id}/runs."))
    def create_workflow_quote(
        request: Request,
        workflow_id: str = Path(...),
        principal: Principal = Depends(require_scope(SCOPE_WORKFLOWS_RUN)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        wf = _cua_toi(db, Workflow, workflow_id, principal)
        ver = _ban_publish(db, wf)
        try:
            gia = bao_gia.uoc_tinh({"nodes": ver.graph.get("nodes", [])})
        except bao_gia.KhongBaoGiaDuoc as loi:
            # ⛔ Từ chối, đừng đoán một con số: một trần đoán ra không chặn gì,
            #    nó chỉ làm người đọc yên tâm.
            raise invalid_request(str(loi)) from loi

        token, _ = quotes.issue(
            secret=_quote_secret(request), user_id=principal.user_id,
            key_id=principal.key_id,
            tool_name=f"{_KHOA_BAO_GIA}{wf.id}",
            params={"version_id": ver.id, "graph_hash": ver.graph_hash},
            credit=gia.toi_da)
        return JSONResponse(
            {
                "quote": token,
                "workflow_id": wf.id,
                "version_id": ver.id,
                # HAI số (`M8`): trần là thứ được giữ và được ký; ước tính chỉ
                # để khách biết mình nhiều khả năng trả bao nhiêu.
                "credit_max": gia.toi_da,
                "credit_estimate": gia.uoc_tinh,
                "expires_in": quotes.QUOTE_TTL_S,
                "balance": credit.so_du(db, principal.user_id),
            },
            headers=_NO_STORE)

    @api.post("/workflows/{workflow_id}/runs", tags=[tag],
              summary="Start a quoted workflow run",
              description=("Holds the quoted ceiling and queues the run. "
                           "Requires an Idempotency-Key header."))
    def start_run(
        request: Request,
        workflow_id: str = Path(...),
        body: dict = Body(default=None),
        idempotency_key: str = Header(default="", alias="Idempotency-Key"),
        principal: Principal = Depends(require_scope(SCOPE_WORKFLOWS_RUN)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        key = idempotency.require_key(idempotency_key)
        wf = _cua_toi(db, Workflow, workflow_id, principal)
        ver = _ban_publish(db, wf)

        bg = quotes.verify(secret=_quote_secret(request),
                           token=str((body or {}).get("quote") or ""),
                           user_id=principal.user_id)
        # ⭐ DUNG LAI `check_matches`, khong tu doi chieu. Bao gia KHONG luu
        #    `params` — no luu `fingerprint(tool_name, params)`, va chinh vong
        #    bam ay la thu bien mot bao gia thanh loi hua ve *request nay* chu
        #    khong ve mot token. Ban dau toi doc `payload["params"]`, thu khong
        #    ton tai, nen phep kiem cua toi luon truot.
        #
        # No phu HAI truong hop bang MOT loi:
        #    `tool` lech  -> bao gia cua workflow KHAC (hoac cua mot tool)
        #    van tay lech -> ban publish DA DOI giua luc bao gia va luc chay
        #
        # ⚠️ Hai thu ay cung mot ma loi (400 `quote_invalid`, `retry: never`) va
        #    do la dung: hanh dong cua khach y het nhau — xin mot bao gia moi.
        #    De ra mot ma thu hai cho cung mot viec la cho khach hai cau tra loi
        #    cho mot cau hoi.
        quotes.check_matches(
            bg, tool_name=f"{_KHOA_BAO_GIA}{wf.id}",
            params={"version_id": ver.id, "graph_hash": ver.graph_hash})

        # Luỹ đẳng do chỉ mục bộ phận `ux_workflow_run_idem` cưỡng chế, không do
        # một SELECT trước INSERT — một SELECT để lại đúng cửa sổ tranh chấp mà
        # chỉ mục ấy sinh ra để đóng.
        cu = db.execute(
            select(WorkflowRun).where(
                WorkflowRun.owner_id == principal.user_id,
                WorkflowRun.workflow_id == wf.id,
                WorkflowRun.idempotency_key == key)).scalars().first()
        if cu is not None:
            return JSONResponse(_cong_khai_run(cu), status_code=200,
                                headers=_NO_STORE)

        try:
            run = thi_hanh.tao_run(
                db, workflow_id=wf.id, version_id=ver.id,
                owner_id=principal.user_id, trigger_kind="api",
                idempotency_key=key, estimated_max=int(bg.get("credit") or 0))
        except Exception as loi:                             # noqa: BLE001
            # `tao_run` flush bên trong, nên `IntegrityError` của chỉ mục bộ
            # phận nổi lên **ở đây**, không ở commit. Thua ở CSDL rồi trả lượt
            # cũ rẻ hơn thắng ở một câu truy vấn không có khoá.
            db.rollback()
            lai = db.execute(
                select(WorkflowRun).where(
                    WorkflowRun.owner_id == principal.user_id,
                    WorkflowRun.workflow_id == wf.id,
                    WorkflowRun.idempotency_key == key)).scalars().first()
            if lai is None:
                raise
            # Moi tep khac trong `server/api/` dung `logging`; `print`
            # trong mot bo xu ly request di thang ra stdout, khong mang
            # muc do va khong loc duoc o production.
            log.info("tao_run dua idempotency: %s", type(loi).__name__)
            return JSONResponse(_cong_khai_run(lai), status_code=200,
                                headers=_NO_STORE)

        try:
            tien.giu_cho_run(db, run)
        except credit.ThieuCreditError as loi:
            # Cùng transaction ⇒ run và khoản giữ cùng rollback. Không có lượt
            # chạy nào tồn tại mà không có tiền đứng sau nó.
            raise insufficient_credit(str(loi)) from loi

        return JSONResponse(_cong_khai_run(run), status_code=201,
                            headers=_NO_STORE)

    @api.get("/runs/{run_id}", tags=[tag], summary="Read one workflow run",
             description="Owner-scoped. Unknown or foreign ids answer 404.")
    def get_run(
        run_id: str = Path(...),
        principal: Principal = Depends(require_scope(SCOPE_WORKFLOWS_READ)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        run = _cua_toi(db, WorkflowRun, run_id, principal)
        return JSONResponse(_cong_khai_run(run), headers=_NO_STORE)

    @api.post("/runs/{run_id}/cancel", tags=[tag],
              summary="Cancel a workflow run",
              description="Terminal runs answer 409; cancelling twice is safe.")
    def cancel_run(
        run_id: str = Path(...),
        principal: Principal = Depends(require_scope(SCOPE_WORKFLOWS_CANCEL)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        run = _cua_toi(db, WorkflowRun, run_id, principal)
        if run.status in may_trang_thai.RUN_KET_THUC:
            if run.status == "CANCELLED":
                return JSONResponse(_cong_khai_run(run), headers=_NO_STORE)
            raise conflict(f"This run is already {run.status}.")
        # ⭐ `chuyen_run` kéo theo `ket_so` trong CÙNG transaction — đó chính là
        #    hình dạng của `M10`. Không có bước "nhớ hoàn tiền" nào ở đây để
        #    quên, và cũng không có cửa sổ nào cho một lần restart lọt vào.
        may_trang_thai.chuyen_run(db, run.id, sang="CANCELLED",
                                  ly_do="huy qua API")
        return JSONResponse(_cong_khai_run(run), headers=_NO_STORE)

    @api.get("/runs/{run_id}/artifacts", tags=[tag],
             summary="List artifacts produced by a run",
             description="Owner-scoped, in the order they were produced.")
    def list_run_artifacts(
        run_id: str = Path(...),
        principal: Principal = Depends(require_scope(SCOPE_WORKFLOWS_READ)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        run = _cua_toi(db, WorkflowRun, run_id, principal)
        # Đi qua `created_by_snapshot_id` — cột LINEAGE trả lời *"tệp này từ đâu
        # ra"* bằng một cột, nên không cần một bảng nối thứ hai để lệch.
        anh = select(NodeRunSnapshot.id).where(NodeRunSnapshot.run_id == run.id)
        hang = db.execute(
            select(Artifact)
            .where(Artifact.owner_id == principal.user_id,
                   Artifact.created_by_snapshot_id.in_(anh))
            .order_by(Artifact.created_at)).scalars().all()
        return JSONResponse(
            {"run_id": run.id,
             "artifacts": [{"id": a.id, "kind": a.kind, "mime": a.mime,
                            "size_bytes": int(a.size_bytes or 0),
                            "checksum_sha256": a.checksum_sha256,
                            "created_at": _iso(a.created_at)} for a in hang]},
            headers=_NO_STORE)
