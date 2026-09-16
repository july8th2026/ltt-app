"""HTTP công khai của kênh phát hành LTTCODE. Nghiệp vụ ở `phat_hanh.py`.

Router KHÔNG tự viết prefix `/lttcode`; nền tảng gắn từ `MANIFEST.route_prefix`.

## Vì sao không route nào dùng require_login

Người gọi là ứng dụng LTTCODE trên máy người dùng, trước (và độc lập với) mọi
tài khoản: nó không có — và theo thiết kế không bao giờ gửi — cookie hay khoá
API. Thứ được phục vụ đều công khai như trang tải `/tai-xuong` của Nexus: số
phiên bản, ghi chú, chữ ký minisign (công khai theo bản chất) và bộ cài. Tính
toàn vẹn của bộ cài do chữ ký kiểm ở phía app, không do đăng nhập.

Không có POST, không ghi gì; `Cache-Control` giữ mặc định `no-store` của nền tảng.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from apps.lttcode import phat_hanh
from platform_core.runtime_paths import data_path
from server.templating import templates

router = APIRouter(tags=["lttcode"])

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_MAY_CUC_BO = {"127.0.0.1", "localhost", "::1"}


def _goc(request: Request) -> str:
    """Gốc URL tuyệt đối cho link tải. Sau Cloudflare Tunnel origin nhận http,
    nhưng updater của app chỉ nên tải qua https — ép https trừ máy cục bộ."""
    host = request.url.hostname or ""
    scheme = request.url.scheme if host in _MAY_CUC_BO else "https"
    port = request.url.port
    netloc = host if port is None or host not in _MAY_CUC_BO else f"{host}:{port}"
    return f"{scheme}://{netloc}"


@router.get("")
async def trang_tai(request: Request):
    ban = phat_hanh.ban_moi_nhat(phat_hanh.doc_manifest(), "stable")
    return templates.TemplateResponse(request, "lttcode_download.html", {"ban": ban})


@router.get("/update/{channel}/{target}/{arch}/{current_version}")
async def kiem_cap_nhat(request: Request, channel: str, target: str, arch: str, current_version: str):
    install_id = request.headers.get("x-lttcode-install-id")
    if install_id is not None and not _UUID.match(install_id):
        install_id = None
    code, body = phat_hanh.quyet_dinh(
        phat_hanh.doc_manifest(), channel, target, arch, current_version, install_id, _goc(request))
    if code == 200 and body is not None:
        return JSONResponse(body)
    return Response(status_code=code)


@router.api_route("/dl/{filename}", methods=["GET", "HEAD"])
async def tai_file(filename: str):
    if not phat_hanh.TEN_TEP.match(filename):
        raise HTTPException(status_code=404)
    root = Path(data_path(phat_hanh.THU_MUC_DIST)).resolve()
    target = (root / filename).resolve()
    # Phải nằm ĐÚNG trong thư mục dist (chống '..' và symlink thoát ra ngoài).
    if root not in target.parents or not target.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(target, media_type="application/vnd.microsoft.portable-executable", filename=filename)
