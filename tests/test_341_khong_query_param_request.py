"""Không route nào được đòi một query param tên `request`.

## Lỗi mà phép kiểm này chốt

`server.deps.user_hien_tai` từng khai `def user_hien_tai(request)` — không chú
kiểu. Gọi thẳng thì đúng, nên chín app dùng nó nhiều tháng không sao. App thứ
mười nối nó qua `Depends(user_hien_tai)`; FastAPI soi chữ ký, thấy tham số
`request` không kiểu, và hiểu nó là **query param bắt buộc**. Trang trả 422:

    {"loc": ["query", "request"], "msg": "Field required"}

## Vì sao bộ test cũ không thấy

Vì test gọi thẳng hàm, còn trình duyệt đi qua router. Đây là đúng loại lỗi mà
`CLAUDE.md` quy tắc 5 nói tới: test xanh không chứng minh trang hiển thị được.

## Vì sao chốt theo TÊN, không theo một app

`request`, `response`, `background_tasks`, `websocket` là những tên mà FastAPI
gán ý nghĩa **theo kiểu**, không theo tên. Quên chú kiểu ở bất kỳ tên nào trong
số đó đều biến nó thành query param bắt buộc, và mọi lần đều cho một thông báo
lỗi không hề nhắc tới nguyên nhân thật. Nên chốt cả nhóm tên, một lần, cho mọi
route hiện có và mọi route sau này.
"""
from __future__ import annotations

import pytest

#: Tên tham số mà FastAPI phân giải theo KIỂU. Thấy chúng trong query params
#: nghĩa là ai đó quên chú kiểu.
TEN_PHAI_CO_KIEU = {"request", "response", "background_tasks", "websocket"}


def _cac_route():
    """Mọi APIRoute, kể cả route nằm trong router lồng.

    ⚠️ `app.routes` KHÔNG phẳng. Phiên bản FastAPI ở đây giữ mỗi
       `include_router` thành một `_IncludedRouter` và chỉ mở nó ra lúc định
       tuyến. Duyệt một tầng thì thấy đúng 4 route mặc định của FastAPI và
       **không thấy route nào của app nào** — nên một phép kiểm duyệt một tầng
       sẽ XANH bất kể có lỗi hay không.

       Bản đầu của tệp này mắc đúng lỗi đó: nó xanh cả khi chú kiểu bị gỡ ra.
       Một bánh cóc không đỏ được thì tệ hơn là không có, vì nó phát ra một
       lời hứa mà nó không giữ.
    """
    from fastapi.routing import APIRoute

    from server.app import create_app

    def di(cac, sau=0):
        if sau > 8:
            return
        for r in cac:
            if isinstance(r, APIRoute):
                yield r
                continue
            # `_IncludedRouter` không phơi `.routes`; router thật nằm ở
            # `.original_router`. Giữ cả hai lối để phép kiểm không mục khi
            # FastAPI đổi cách biểu diễn.
            con = (getattr(r, "routes", None)
                   or getattr(getattr(r, "original_router", None), "routes", None)
                   or getattr(getattr(r, "router", None), "routes", None))
            if con:
                yield from di(con, sau + 1)

    yield from di(create_app().routes)


def test_khong_route_nao_doi_query_param_ten_dac_biet():
    xau = []
    for route in _cac_route():
        for p in route.dependant.query_params:
            if p.name in TEN_PHAI_CO_KIEU:
                xau.append(f"{route.path} -> query param '{p.name}'")
        for phu in route.dependant.dependencies:
            for p in phu.query_params:
                if p.name in TEN_PHAI_CO_KIEU:
                    xau.append(f"{route.path} -> Depends({phu.name}) "
                               f"-> query param '{p.name}'")

    assert not xau, (
        "Nhung route sau doi mot query param mang ten ma FastAPI phan giai theo "
        "KIEU. Gan nhu chac chan la thieu chu kieu (vd `request` thay vi "
        "`request: Request`) o mot ham duoc dung qua Depends. Trang se tra 422 "
        "voi mot thong bao khong nhac gi toi nguyen nhan that:\n  "
        + "\n  ".join(sorted(set(xau))))


@pytest.mark.parametrize("duong", ["/ltt-voice", "/ltt-voice/"])
def test_trang_ltt_voice_khong_tra_422(duong):
    """Ca cu the da vo that, giu lai de no khong quay lai.

    Chua dang nhap thi mong doi 303 ve /login — DUNG la 422.
    """
    from fastapi.testclient import TestClient

    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    r = client.get(duong)
    assert r.status_code != 422, (
        f"{duong} tra 422: {r.text[:300]}\n"
        "Xem chu thich o `server/deps.py::user_hien_tai`.")
