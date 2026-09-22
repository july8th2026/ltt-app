"""Trang vận hành (operator-only) của video_crawler: sức khoẻ theo nền 24 giờ (PLAN_MVP §C dòng L4-b).

Router RIÊNG, không tự viết prefix (giống `routes.py`). ⚠️ Chưa được nền tảng gắn: `mount_all`
(`platform_core/registry.py`) chỉ `include_router` MỘT router mỗi app — router chính ở `routes.py`
(lane L1). Điều phối cần thêm một dòng khi gộp:

    router.include_router(routes_van_hanh.router)   # trong apps/video_crawler/routes.py

Sau dòng đó, trang hiện ở `{route_prefix}/van-hanh` = `/video-crawler/van-hanh`.

Cổng cờ: bản sao 3 dòng của `_cong_co`/`CO_MO` ở `routes.py` — KHÔNG import từ đó, vì `routes.py` sẽ
là nơi `include_router` module này (import ngược lại sẽ vòng). Hai hằng `CO_MO` phải LUÔN bằng nhau;
`test_1924` khoá điều đó bằng cách so `routes_van_hanh.CO_MO == routes.CO_MO` khi cả hai cùng nạp được.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from apps.video_crawler import suc_khoe
from apps.video_crawler.manifest import MANIFEST
from server.deps import get_db, require_operator
from server.templating import templates

router = APIRouter(tags=["video_crawler"])

#: Phải khớp `routes.py:CO_MO`.
CO_MO = "LTT_VIDEO_CRAWLER"

#: Cửa sổ đọc sức khoẻ — brief L4-a "24 h".
CUA_SO_GIO = 24


def _cong_co() -> None:
    if str(os.environ.get(CO_MO, "")).strip() != "1":
        raise HTTPException(status_code=404)


@router.get("/van-hanh", response_class=HTMLResponse, dependencies=[Depends(_cong_co)])
def van_hanh(request: Request, _operator: str = Depends(require_operator), db=Depends(get_db)):
    """Chỉ operator (`require_operator`): 403 cho khách thường đã đăng nhập, 303 → /login nếu chưa."""
    thong_ke = suc_khoe.thong_ke(db, gio=CUA_SO_GIO)
    return templates.TemplateResponse(request, "vc_van_hanh.html", {
        "app": MANIFEST, "nav": MANIFEST.slug,
        "cua_so_gio": CUA_SO_GIO,
        "thong_ke": thong_ke,
        "co_nen_khuyen_nghi_tat": any(v["khuyen_nghi_tat"] for v in thong_ke.values()),
    })
