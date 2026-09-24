"""`/hooks/*` — cửa vào CÔNG KHAI của workflow: trigger webhook và resume waitpoint.

Spec §8.3. Router MỚI, **ngoài `/api/v1`** — 24 route của API công khai đang
đóng băng (`server/api/inventory.py`), và một cửa máy-gọi-máy không có khoá API
không thuộc về bề mặt đó.

## Ba luật của cửa này, mỗi luật là một lỗi đã có người khác trả giá

1. **Từ chối phải NÓI RA.** `activepieces#14808` — *"Rejected webhook auth
   returns HTTP 200 with no run and no log"*: người tích hợp thấy 200, tưởng
   đã chạy, và cái không chạy im lặng suốt nhiều ngày. Ở đây: token sai ⇒
   **401**, trigger không có/đã tắt ⇒ **404**, quá hạn mức ⇒ **429**.
2. **Trùng không được tạo run thứ hai.** Khoá khử trùng do
   `platform_core/workflow/khoa_idem.py` sinh; chốt cuối là chỉ mục bộ phận
   `ux_workflow_run_idem` trên CSDL, không phải một câu `SELECT` cẩn thận.
3. **Không giữ kết nối.** Trả `202` ngay. Cloudflare cắt ở 100 giây
   (`CLAUDE.md` luật 8) và động cơ chạy trong hàng đợi job, không trong request.

⛔ Miễn CSRF cố ý: đây là API máy-gọi-máy. An toàn đến từ token trong header
   (`X-LTT-Token`, so hằng thời gian với `sha256` đã lưu), không từ một token
   biểu mẫu.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/hooks", tags=["hooks"])
_log = logging.getLogger("ltt.hooks")

#: Trần thân request (spec §8.3). Đọc theo từng khối rồi dừng: đọc hết 1 GB
#: rồi mới đo là để người gọi quyết định ta dùng bao nhiêu bộ nhớ.
TRAN_THAN = 1024 * 1024

#: Header mang token. Một hằng vì hai chỗ nói về nó (route này và tài liệu
#: tích hợp), và vì nó là RANH GIỚI xác thực chứ không phải một cái tên.
HEADER_TOKEN = "X-LTT-Token"
HEADER_IDEM = "Idempotency-Key"


async def _doc_than(request: Request) -> bytes | None:
    """Thân request, hoặc `None` nếu vượt `TRAN_THAN`.

    ⚠️ `Content-Length` một mình KHÔNG đủ: nó là thứ người gọi tự khai, và một
       `Transfer-Encoding: chunked` không có nó. Nên đo cả hai — khai trước
       (rẻ, chặn sớm), rồi cộng dồn thật lúc đọc.
    """
    khai = request.headers.get("content-length")
    if khai and khai.isdigit() and int(khai) > TRAN_THAN:
        return None
    ra = bytearray()
    async for khoi in request.stream():
        ra.extend(khoi)
        if len(ra) > TRAN_THAN:
            return None
    return bytes(ra)


def _mo_db():
    from platform_core.db import get_session

    gen = get_session()
    return gen, next(gen)


def _dong_db(gen) -> None:
    try:
        next(gen)
    except StopIteration:
        pass


@router.post("/wf/{trigger_id}")
async def hook_workflow(trigger_id: str, request: Request):
    """Một cú bắn của `trigger.webhook` (spec §8.3)."""
    from platform_core.models import Workflow
    from platform_core.workflow import han_muc, khoa_idem, tao_run, trigger

    than = await _doc_than(request)
    if than is None:
        return JSONResponse({"ma": "than_qua_lon",
                             "thong_diep": f"than toi da {TRAN_THAN} byte"},
                            status_code=413)

    gen, db = _mo_db()
    try:
        t = trigger.theo_id(db, trigger_id)
        if t is None or t.kind != "WEBHOOK":
            return JSONResponse({"ma": "khong_tim_thay"}, status_code=404)
        if not trigger.token_khop(t.config or {},
                                  request.headers.get(HEADER_TOKEN, "")):
            _log.warning("hooks: token sai cho trigger %s", trigger_id)
            return JSONResponse({"ma": "token_sai"}, status_code=401)
        if han_muc.vuot_han_webhook(db, t):
            return JSONResponse(
                {"ma": "qua_han_muc",
                 "thong_diep": f"toi da {trigger.WEBHOOK_MOI_PHUT_MOI_TRIGGER}"
                               " lan moi phut"}, status_code=429)

        khoa = khoa_idem.khoa_webhook(
            t.id, idempotency_key=request.headers.get(HEADER_IDEM, ""),
            than=than)
        wf = db.get(Workflow, t.workflow_id)
        if wf is None:
            return JSONResponse({"ma": "khong_tim_thay"}, status_code=404)
        try:
            run, moi = tao_run.tao_run(
                db, workflow=wf, owner_id=t.owner_id, trigger_kind="webhook",
                idempotency_key=khoa,
                inputs={"than": _json_an_toan(than),
                        "query": dict(request.query_params)})
        except tao_run.KhongCoBanPublish:
            return JSONResponse({"ma": "chua_publish"}, status_code=409)
        except tao_run.QuaHanMuc as loi:
            return JSONResponse({"ma": "qua_han_muc",
                                 "thong_diep": str(loi)}, status_code=429)
        except tao_run.TrungKhoaKhacWorkflow:
            return JSONResponse({"ma": "idempotency_conflict"},
                                status_code=409)
        except Exception:                                    # noqa: BLE001
            db.rollback()
            _log.exception("hooks: tao run tu trigger %s loi", trigger_id)
            return JSONResponse({"ma": "loi_he_thong"}, status_code=500)
        t.last_fired_at = run.created_at
        db.commit()
        return JSONResponse({"run_id": run.id, "moi": bool(moi)},
                            status_code=202)
    finally:
        _dong_db(gen)


@router.post("/wp/{waitpoint_id}")
async def hook_waitpoint(waitpoint_id: str, request: Request):
    """Resume một `core.wait mode=webhook` (spec §8.3, URL một-lần)."""
    from platform_core.workflow import noi_lai

    than = await _doc_than(request)
    if than is None:
        return JSONResponse({"ma": "than_qua_lon"}, status_code=413)

    gen, db = _mo_db()
    try:
        ket = noi_lai.mo_bang_token(
            db, waitpoint_id, token=request.headers.get(HEADER_TOKEN, ""),
            du_lieu={"than": _json_an_toan(than)})
        if ket is noi_lai.KHONG_CO:
            return JSONResponse({"ma": "khong_tim_thay"}, status_code=404)
        if ket is noi_lai.TOKEN_SAI:
            return JSONResponse({"ma": "token_sai"}, status_code=401)
        if ket is noi_lai.DU_LIEU_SAI:
            return JSONResponse(
                {"ma": "du_lieu_sai",
                 "thong_diep": f"can `quyet_dinh` la mot trong "
                               f"{list(noi_lai.QUYET_DINH)}"}, status_code=400)
        if ket is noi_lai.DA_DONG:
            # ⭐ 409 chứ không 200: gửi lại vào một điểm chờ ĐÃ ĐÓNG không phải
            #    một lần resume thành công, và nói thế là nói dối người tích hợp.
            return JSONResponse({"ma": "da_dong"}, status_code=409)
        db.commit()
        return JSONResponse({"ok": True}, status_code=202)
    finally:
        _dong_db(gen)


def _json_an_toan(than: bytes):
    """Thân đã giải mã, hoặc chuỗi thô. ⛔ Không bao giờ ném ra ngoài.

    Một webhook gửi `text/plain` hay JSON hỏng là chuyện của người gọi; nó
    không được thành 500 của ta.
    """
    import json

    try:
        return json.loads(than.decode("utf-8"))
    except Exception:                                        # noqa: BLE001
        try:
            return than.decode("utf-8", "replace")[:10_000]
        except Exception:                                    # noqa: BLE001
            return ""
