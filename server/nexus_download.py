"""Trang tải LTT Nexus + bản kê phiên bản (Model B, Q101: web = hướng dẫn/tải).

Công khai (không cần đăng nhập) — ai cũng tải được ứng dụng. `/nexus/version.json`
là nguồn CHUNG: trang này render từ nó, và client tự-update đọc chính nó.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from platform_core.nexus import versions
from server.templating import templates

router = APIRouter(tags=["nexus-download"])


@router.get("/tai-xuong")
async def trang_tai(request: Request):
    """Trang tải: logo + 4 nền tảng (Windows/macOS/iOS/Android) + hướng dẫn."""
    m = versions.manifest()
    plats = [{"key": k, **m["platforms"][k]}
             for k in versions.PLATFORM_ORDER if k in m["platforms"]]
    return templates.TemplateResponse(
        request, "nexus_download.html",
        {"version": m.get("version", ""), "notes": m.get("notes", ""),
         "platforms": plats})


@router.get("/nexus/version.json")
async def version_json():
    """Bản kê phiên bản (JSON). Client tự-update GỌI cái này để so phiên bản.

    Cache ngắn ở biên: phải mới đủ để bản cập nhật tới người dùng nhanh, nhưng
    không cần no-store (nó là dữ liệu công khai, không nhạy cảm).
    """
    return JSONResponse(versions.manifest(),
                        headers={"Cache-Control": "public, max-age=300"})
