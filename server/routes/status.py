"""
/status — the doctor health report, in the browser (PB-2).

Two pages live here, and the difference between them is the point:

* ``/status/api`` is **public**. It groups by capability and says nothing about
  how the platform is built;
* ``/status`` is **operator-only**. It is the doctor report, and it names the
  database, the disk, the tunnel and the credential pool.

A page that mixed them would either be useless to a customer or dangerous to
publish (EXT-17).

Reuses tools/doctor.py rather than reimplementing the checks, so the CLI and
the browser can never disagree.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from server.deps import get_db, require_operator
from server.templating import templates

router = APIRouter(tags=["status"])


@router.get("/status/api", response_class=HTMLResponse)
def public_api_status(request: Request, db: Session = Depends(get_db)):
    """Is the API working — for anyone, without an account.

    Deliberately **not** behind `require_operator`, unlike `/status` below. A
    status page a customer cannot read during an incident is a status page that
    does not exist; the whole point is that it answers when support does not.

    Equally deliberately, it says nothing about how the platform is built. The
    operator report names the database, the disk, the tunnel and the credential
    pool; publishing that during an outage would tell somebody planning the next
    one which door is currently unlocked.
    """
    from platform_core.public_api.config import load_public_api_config
    from platform_core.public_api.status import public_status

    config = getattr(request.app.state, "public_api", None)
    if config is None:
        config = load_public_api_config()

    report = public_status(db, config)
    response = templates.TemplateResponse(request, "status_api.html", {
        "nav": "status",
        "report": report,
    })
    # An incident page must never be served from a cache that predates the
    # incident.
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/status", response_class=HTMLResponse)
def status_page(
    request: Request,
    user: str = Depends(require_operator),
):
    """Báo cáo cho người vận hành.

    ⚠️ Từ 2026-08-25 trang này **mỏng đi rõ rệt**, và cần đọc đúng lý do.
       `tools/doctor.py` từng có sáu mục kiểm; năm mục thuộc app socialbot
       (cấu hình, token FB/TikTok, worker, service account, Google Sheet) và
       đã bị gỡ cùng app đó. Còn lại: hồ sơ môi trường + tóm tắt Nexus.

    ⛔ Đừng đọc thành *"doctor của nền tảng bị teo"*. **Chưa bao giờ có doctor
       của nền tảng** — không mục nào từng kiểm CSDL, kho R2, worker hay
       Tunnel. Thứ trống ở đây là một chỗ trống đã tồn tại sẵn, nay nhìn thấy
       được. Lấp nó là một việc phải làm có chủ ý.

    Tham số `check_sheet` đã bỏ: nó chỉ bật mục kiểm Google Sheet, mà mục đó
    không còn.
    """
    from tools import doctor

    report = doctor.run()

    return templates.TemplateResponse(request, "status.html", {
        "user": user,
        "nav": "status",
        "sections": report.sections,
        "blockers": [s for s in report.sections if s["status"] == doctor.BLOCK],
        "checked_sheet": False,
        "nexus": _tom_tat_nexus(),
    })


def _tom_tat_nexus() -> dict | None:
    """Số liệu vận hành Nexus cho trang tình trạng, hoặc None khi Nexus tắt.

    Vì sao cần: trước cái này, người vận hành **không có cách nào** biết có bao
    nhiêu máy đã ghép, bao nhiêu đang bật, hay có ai bị relay chặn vì hết credit —
    tức là bán một dịch vụ mà không nhìn thấy nó chạy.
    """
    from platform_core import nexus

    if not nexus.enabled():
        return None
    from platform_core.db import get_session
    from platform_core.nexus import billing, devices

    ra = {"gia_thang": billing.gia_may_thang(), "loi": None}
    gen = None
    try:
        gen = get_session()
        db = next(gen)
        ds = db.query(devices.NexusDevice).all()
        ra["may"] = len(ds)
        ra["online"] = sum(1 for d in ds if devices.dang_online(d))
        ra["thu_hoi"] = sum(1 for d in ds if d.revoked_at is not None)
        ra["chua_tra"] = sum(
            1 for d in ds
            if d.revoked_at is None and not billing.da_thanh_toan(d))
        from platform_core.nexus.tables import NexusSession

        ra["phien"] = db.query(NexusSession).count()
        # Bộ đếm 24h (đăng ký, relay cho qua / chặn).
        try:
            from platform_core.public_api import metrics

            tong = metrics.aggregate(db, hours=24)
            dem = tong.get("counters", tong) if isinstance(tong, dict) else {}
            ra["dem_24h"] = {k: v for k, v in dem.items()
                             if str(k).startswith("nexus:")}
        except Exception as exc:                                # noqa: BLE001
            ra["dem_24h"] = {}
            ra["loi"] = f"khong doc duoc bo dem: {type(exc).__name__}"
    except Exception as exc:                                    # noqa: BLE001
        # Trang tình trạng phải mở được ngay cả khi phần Nexus hỏng — nó là thứ
        # người vận hành cần NHẤT lúc có sự cố.
        return {"loi": f"{type(exc).__name__}: {exc}"}
    finally:
        if gen is not None:
            try:
                next(gen)
            except StopIteration:
                pass
    return ra
