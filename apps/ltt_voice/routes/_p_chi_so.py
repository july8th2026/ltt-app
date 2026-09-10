"""Cửa CHỈ SỐ THEO GIỌNG cho người vận hành (U-14).

## ⛔ VÌ SAO KHÔNG ĐẶT Ở `/health/version`

Bản kiểm toán viết *"`/health/version` **hoặc** trang admin"*, và hai chỗ ấy
không tương đương:

- `/health/version` là bề mặt **hạ tầng** — nó trả lời *"máy chủ đang chạy bản
  nào"*. Thêm số liệu kinh doanh vào đó là làm một endpoint hạ tầng phụ thuộc
  một truy vấn bảng `jobs`, tức một CSDL chậm làm phép dò sức khoẻ chậm theo.
- Và nó **rộng hơn cần thiết**. Mức dùng theo từng giọng nói ra hình dạng kinh
  doanh của ta — giọng nào bán chạy, kho lớn cỡ nào. Đó không phải bí mật sống
  còn, nhưng cũng không có lý do gì để nó nằm sau một cửa dò sức khoẻ.

⇒ Một cửa riêng, sau `is_operator`.

## ⚠️ `is_operator`, KHÔNG phải `require_login`

`server.deps.is_operator` là chỗ nền tảng đã định nghĩa ranh giới ấy — admin-env
hoặc `user.role == "admin"`. Tự dựng một phép kiểm quyền thứ hai trong một app
là cách hai định nghĩa "admin" trôi khỏi nhau, và bên trôi thường là bên ít
người đọc hơn.
"""
from __future__ import annotations

from ._chung import (Depends, JSONResponse, Request, _db, require_login,
                     router, user_hien_tai)


@router.get("/chi-so")
def chi_so(request: Request, user=Depends(user_hien_tai),
           _=Depends(require_login)):
    """Chỉ số vận hành theo từng giọng. JSON. Chỉ người vận hành.

    ⛔ TRẢ 404, KHÔNG TRẢ 403, cho người không phải vận hành.

       403 xác nhận rằng đường dẫn này **tồn tại** và rằng người hỏi **không đủ
       quyền** — hai mẩu thông tin cho một người không có việc gì ở đây. 404 thì
       không nói gì cả, và nó là câu trả lời đúng của một cửa mà đa số tài
       khoản không nên biết là có.
    """
    from server.deps import is_operator

    if not is_operator(request):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    from .. import chi_so_giong

    gen = _db()
    db = next(gen)
    try:
        return JSONResponse(chi_so_giong.gom(db))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
