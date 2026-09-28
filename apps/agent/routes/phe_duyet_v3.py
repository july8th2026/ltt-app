"""Cua duyet/tu choi cho `core.human` (lan UI-8a — Human approval).

## VI SAO MO-DUN NAY TON TAI

`platform_core/workflow/nut_loi/cho.py::chay_human` da HOAN CHINH tu truoc:
no mo mot `Waitpoint(kind="HUMAN")`, `NHANH_HUMAN = ("approve", "reject")` da
khai hai nhanh ra, `che_do_het_han` mac dinh `reject` (spec §5.7) da dung, va
`runs_v3.py::_waiting_kind` da DOC duoc waitpoint con mo. Toan bo NGHIA da
song. Thu duy nhat thieu la mot cua HTTP cho NGUOI BAM duyet/tu choi — dung
khuon "y nghia da song, cua thi chua" ma lan UI-1 da gap voi luu tru workflow.

⇒ Mo-dun nay la **day noi CUOI CUNG**, khong phai mot lop nghiep vu moi:

    POST /api/v3/runs/{run_id}/nodes/{node_id}/duyet   {quyet_dinh, ghi_chu?}

⛔ KHONG mo cua nao khac ngoai cua nay. Muon xem "cau hoi" cua node hay han
   cho hien tai, giao dien doc tu THAM SO cong khai cua chinh node do (Canvas
   da co san trong bo nho — no la mot phan cua do thi da publish, khong phai
   bi mat), khong can mot cua GET rieng.

## Cua nay KHONG lam gi (bat bien tien — credit.py/jobs.py/job_runner.py)

- ⛔ KHONG tao run, KHONG tinh tien, KHONG giu credit — no chi dong MOT
  waitpoint da co san. Tien da duoc `tao_run.tao_run()` giu tu luc run bat dau.
- ⛔ KHONG di vong qua `platform_core/workflow/tao_run.py`.
- Dong waitpoint = goi `platform_core.workflow.noi_lai.mo()` — CUNG mot ham
  ma `/hooks/wp/{id}` (webhook resume, `server/routes/hooks.py`) va bo quet
  het han (`noi_lai.quet_het_han`) da dung. Mot cua thu hai tu viet lai
  "ghi tin hieu + dong waitpoint + hen wakeup" la mot cho de ba thu do troi
  khoi nhau — dung loi da ghi trong docstring cua `noi_lai.py`.

## Bon bat bien co test (`tests/test_65xx_phe_duyet_v3.py`)

1. **404, khong phai 403, cho run cua nguoi khac** — `_run_cua_toi` loc
   `owner_id` ngay trong truy van, cung khuon `drafts_v3._cua_toi`.
2. **Thieu CSRF -> 400, KHONG dong waitpoint** — `_verify_json_csrf` chay
   TRUOC moi thao tac tren waitpoint.
3. **Luy dang** — `noi_lai.mo()` tu no da tu choi mo lai mot waitpoint
   `status != PENDING` (tra `DA_DONG`); cua nay doc gia tri do va tra loi ro
   rang (`da_dong_truoc_do: true`), ⛔ KHONG 500, ⛔ KHONG ghi de `quyet_dinh`
   da chot.
4. **`core.delay`/`core.wait` khong co nut duyet** — `_human_waitpoint_cua_node`
   doc `Waitpoint.kind`, KHONG suy tu `status` cua node: mot node WAITING vi
   DELAY/WEBHOOK/EVENT se khong tim thay waitpoint HUMAN nao va nhan 404.

## Mot lop phong thu THEM, ngoai spec — vi sao

`noi_lai.mo()` chi kiem `wp.status != PENDING`, KHONG kiem `het_han_luc`. Do
la dung cho `/hooks/wp/{id}` (khach mang token, goi mot lan) vi bo quet het
han (`dong_co.xu_ly_run` -> `noi_lai.quet_het_han`) chay THUONG XUYEN va se
dong waitpoint ngay khi qua han. Nhung co mot khe rang: giua luc `het_han_luc`
da qua VA luc dong co thuc su chay `tiep_mot()` de dong no, waitpoint van con
`PENDING` trong CSDL. Neu cua nay khong kiem them, nguoi dung co the "duyet"
mot buoc ma dong co se ket luan la HET HAN (theo `che_do_het_han` cua chinh
node) mot khoanh khac sau — hai ket luan cho CUNG mot waitpoint. ⇒ Cua nay tu
choi thao tac (`409 da_het_han`) khi `het_han_luc` da qua, ⛔ khong tu quyet
dinh thay cho `che_do_het_han` — do la viec CUA `nut_loi/cho._ket_het_han`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _user, _verify_json_csrf, router
from platform_core.i18n import _ as _t
from platform_core.models import Waitpoint, WorkflowRun
from platform_core.workflow import cho_doi, noi_lai
from server.auth.session import require_login
from server.deps import get_db

#: Do dai toi da cua ghi chu nguoi duyet gui kem. Khong phai bi mat, chi la
#: mot truong tu do — mot tran la de mot nguoi go nham 2 MB khong lam
#: `output_ref` (JSON) phinh vo to.
_DAI_GHI_CHU = 2000


def _run_cua_toi(db: Session, run_id: str, user_id: str) -> WorkflowRun:
    """Lượt chạy đã lọc theo chủ sở hữu, hoặc 404.

    Cùng khuôn `drafts_v3._cua_toi`/`runs_v3._run_cua_toi`: "không có" và
    "của người khác" phải trả cùng một 404, nếu không một 403 sẽ là máy đếm
    cho người ngoài biết id nào có thật.
    """
    run = db.execute(
        select(WorkflowRun).where(WorkflowRun.id == str(run_id or ""),
                                  WorkflowRun.owner_id == user_id)
    ).scalars().first()
    if run is None:
        raise HTTPException(status_code=404,
                            detail=_t('Không tìm thấy lượt chạy.'))
    return run


def _human_waitpoint_cua_node(db: Session, run: WorkflowRun,
                              node_id: str) -> Waitpoint | None:
    """Waitpoint kind=HUMAN mới nhất còn gắn với `node_id` của run này.

    ⛔ Đọc `Waitpoint.kind`, KHÔNG suy từ trạng thái node: một node WAITING có
    thể đang chờ DELAY/WEBHOOK/EVENT — ba loại đó không có nút duyệt.

    ⚠️ `waitpoint_cua_node` trả MỌI waitpoint từng gắn với đường thi hành này
    (kể cả của lần thử trước, nếu node đã thử lại) — lấy hàng MỚI NHẤT là câu
    trả lời đúng cho "đang chờ ai đó bấm gì".
    """
    wp_ids = cho_doi.waitpoint_cua_node(db, run.id, str(node_id))
    if not wp_ids:
        return None
    hang = db.execute(
        select(Waitpoint)
        .where(Waitpoint.id.in_(wp_ids), Waitpoint.kind == "HUMAN")
        .order_by(Waitpoint.created_at.desc())
    ).scalars().all()
    return hang[0] if hang else None


def _khong_tzinfo(luc: datetime) -> datetime:
    return luc.replace(tzinfo=None) if luc.tzinfo is not None else luc


def _bay_gio() -> datetime:
    """Đồng hồ CỦA MODULE NÀY — cùng quy ước với `cho.py`/`han_cho.py`/
    `noi_lai.py` (một hàm riêng mỗi nơi, để `monkeypatch` giả lập đồng hồ
    trong test mà không phải nhét một tham số `luc` xuyên suốt lời gọi)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _da_qua_han(wp: Waitpoint) -> bool:
    if wp.het_han_luc is None:
        return False
    return _khong_tzinfo(wp.het_han_luc) <= _bay_gio()


@router.post("/api/v3/runs/{run_id}/nodes/{node_id}/duyet")
async def v3_duyet_node(request: Request, run_id: str, node_id: str,
                        _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    """Duyệt hoặc từ chối MỘT `core.human` đang `WAITING` (spec §5.7).

    Thân: `{quyet_dinh: "approve"|"reject", ghi_chu?: string}`.

    ⛔ CSRF được kiểm TRƯỚC khi chạm tới waitpoint — thiếu/sai CSRF luôn là
    `400` và KHÔNG có tác dụng phụ nào lên waitpoint, kể cả khi `run_id`/
    `node_id` hợp lệ.
    """
    try:
        body = await request.json()
    except (ValueError, UnicodeDecodeError):
        # ⛔ Bắt ĐÚNG LOẠI, không bắt `Exception` — khuôn từ
        #    `server/nexus/routes.py` (bốn chỗ), đã dùng lại nguyên ở
        #    `ket_noi_v3.py::v3_thu_hoi_ket_noi`. Một `except Exception` ở
        #    đây sẽ nuốt cả `MemoryError` rồi trả một 400 "thuyết phục và sai".
        body = {}
    if not isinstance(body, dict):
        body = {}
    _verify_json_csrf(request, body)

    user = _user(request)
    run = _run_cua_toi(db, run_id, user.id)

    qd = str(body.get("quyet_dinh") or "").strip()
    if qd not in noi_lai.QUYET_DINH:
        # ⭐ Dùng lại CHÍNH tập mà `noi_lai.mo_bang_token` đã dùng để kiểm
        #    `quyet_dinh` của cửa webhook token — một tập đóng, một chỗ khai.
        raise HTTPException(status_code=422, detail={
            "ma": "quyet_dinh_sai",
            "thong_diep": _t('Quyết định phải là "approve" hoặc "reject".')})

    wp = _human_waitpoint_cua_node(db, run, node_id)
    if wp is None:
        # Node khong ton tai trong run nay, HOAC ton tai nhung chua tung mo
        # mot waitpoint HUMAN (dang WAITING vi DELAY/WEBHOOK/EVENT, hoac chua
        # bao gio WAITING). Ca hai deu la "khong co gi de duyet o day".
        raise HTTPException(status_code=404, detail={
            "ma": "khong_co_diem_cho_nguoi_duyet",
            "thong_diep": _t('Bước này không có điểm chờ người duyệt.')})

    if wp.status == noi_lai.DANG_CHO and _da_qua_han(wp):
        # Xem docstring module: khe hở giữa "đã quá hạn theo đồng hồ" và "động
        # cơ đã thực sự đóng waitpoint". ⛔ Không tự quyết định thay
        # `che_do_het_han` — chỉ từ chối, để lượt quét/động cơ kết luận.
        raise HTTPException(status_code=409, detail={
            "ma": "da_het_han",
            "thong_diep": _t('Đã quá hạn chờ — hệ thống sẽ tự kết luận bước '
                             'này trong giây lát.')})

    ghi_chu = str(body.get("ghi_chu") or "")[:_DAI_GHI_CHU]
    ra = {"quyet_dinh": qd, "ghi_chu": ghi_chu, noi_lai.KHOA_NHANH: qd}
    ket = noi_lai.mo(db, wp, status="SUCCEEDED", ra=ra,
                     nguon=f"nguoi:{user.id}"[:64])
    if ket is noi_lai.DA_DONG:
        # ⭐ LUỸ ĐẲNG: waitpoint đã đóng TỪ TRƯỚC (bấm hai lần, hai tab, hoặc
        #    vừa hết hạn). ⛔ KHÔNG 500, ⛔ KHÔNG ghi đè: trả lại quyết định
        #    ĐÃ CÓ, không phải quyết định vừa gửi lên.
        db.rollback()
        da_qd = str((wp.output_ref or {}).get("quyet_dinh") or "")
        return JSONResponse({
            "ok": True, "da_dong_truoc_do": True,
            "quyet_dinh": da_qd,
            "het_han": bool((wp.output_ref or {}).get("het_han"))},
            status_code=200)

    db.commit()
    return JSONResponse({"ok": True, "da_dong_truoc_do": False,
                         "quyet_dinh": qd}, status_code=200)
