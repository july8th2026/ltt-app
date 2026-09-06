"""_chung.py — router + helper dùng chung cho các mảnh route của ChatLTT."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token  # noqa: F401
from server.deps import user_hien_tai

router = APIRouter(tags=["chatltt"])

NO_STORE = {"Cache-Control": "no-store"}


def cong_tep() -> None:
    """Cong co cho nhom P06 (dinh tai lieu). Tat => 404, khong phai 403.

    🔴 PHAI dat TRUOC `require_login` trong danh sach tham so. `Depends`
       chay theo thu tu khai bao, va `require_login` **chuyen huong 303 ve
       /login** — nen dat sau thi mot route "da dong" van tra 303 cho khach
       chua dang nhap, tuc no van noi rang duong nay ton tai. Ca nay da xay
       ra that o kho nay.

    ⛔ 404 chu khong 403: mot tinh nang chua mo thi khong nen tu khai rang
       no ton tai va dang bi cam.
    """
    from apps.chatltt.services import co_v3

    if not co_v3.tep_bat():
        raise HTTPException(status_code=404)


def cong_ghi_nho() -> None:
    """Cong co cho nhom B4 (ghi nho). Tat => 404, khong phai 403.

    🔴 Cung luat dat-truoc-`require_login` nhu `cong_tep` — xem docstring o tren.
       Ghi lai o day chu khong chi tro sang: mot luat chi song trong mot chu
       thich o ham ben canh la mot luat se bi bo qua khi ai do chep khuon nay
       cho cong thu ba.
    """
    from apps.chatltt.services import co_v3

    if not co_v3.ghi_nho_bat():
        raise HTTPException(status_code=404)


def cong_du_an() -> None:
    """Cong co cho nhom B5 (du an). Tat => 404, khong phai 403.

    🔴 Cung luat dat-truoc-`require_login` nhu `cong_tep`/`cong_ghi_nho`.
       Ghi lai o day chu khong tro sang: mot luat chi song trong mot chu
       thich o ham ben canh la mot luat se bi bo qua khi ai do chep khuon.
    """
    from apps.chatltt.services import co_v3

    if not co_v3.du_an_bat():
        raise HTTPException(status_code=404)


def uid(request: Request) -> str:
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(status_code=401, detail="chua dang nhap")
    return str(u.id)


def json_ok(than: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(than, status_code=status_code, headers=NO_STORE)


def loi(ma: int, code: str, thong_diep: str = "") -> JSONResponse:
    """Lỗi JSON cho client React: `{"error": {"code", "message"}}`, no-store (Q88)."""
    return JSONResponse({"error": {"code": code, "message": thong_diep}},
                        status_code=ma, headers=NO_STORE)


async def doc_json(request: Request) -> dict:
    try:
        than = await request.json()
    except (ValueError, json.JSONDecodeError):
        than = {}
    return than if isinstance(than, dict) else {}


def kiem_csrf(request: Request, than: dict | None = None) -> bool:
    """CSRF cho MỌI cửa ghi: header `X-CSRF-Token` (React), hoặc trường
    `csrf_token` trong thân (form).

    ⚠️ `than` NHẬN `None`, và đó không phải tiện tay. Cửa tải ảnh
    (`POST /api/anh-vao`) nhận `multipart/form-data`: thân của nó là một **tệp**,
    không phải một dict ta đọc được trong khi vẫn còn muốn stream nó. Không có
    mặc định này thì cửa đó buộc phải gọi thẳng `verify_csrf_token`, tức có
    **hai** đường kiểm CSRF trong cùng một app.

    ⛔ Và hai đường là hai đường sẽ lệch. `test_628::test_moi_cua_GHI_deu_doi_CSRF`
       đọc mã nguồn từng route và đòi thấy đúng tên `kiem_csrf` — nó bắt được
       chính chuyện này ở lượt gate đầu tiên sau khi cửa tải ảnh ra đời. Bánh cóc
       đúng; cách sửa là gom về một cửa, không phải nới bánh cóc.
    """
    token = (request.headers.get("X-CSRF-Token", "")
             or str((than or {}).get("csrf_token", "") or ""))
    return verify_csrf_token(request, token)
