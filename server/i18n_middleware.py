"""
i18n_middleware.py — nhận diện ngôn ngữ và bóc tiền tố `/en/` (H24 Pha 0).

## Vì sao bóc tiền tố ở middleware chứ không sửa định tuyến

`/en/nap` được **viết lại thành `/nap`** trước khi tới router. Nhờ vậy toàn bộ
định tuyến hiện có chạy nguyên xi — không phải sửa một `@router.get` nào, không
phải nhân đôi route, không có nguy cơ sót một trang.

Chiều ngược lại cũng vậy: route trả `RedirectResponse("/nap")` như cũ, middleware
**viết lại header `Location`** thành `/en/nap` khi đang ở tiếng Anh. Nếu không
làm thế thì mọi lần chuyển hướng sẽ ném người dùng tiếng Anh về bản tiếng Việt,
và phải sửa hàng chục chỗ `RedirectResponse` rải khắp mã.

## Vì sao có chuyển hướng lần đầu

Chủ sản phẩm chọn phương án tiền tố để Google index được cả hai bản. Muốn vậy thì
URL phải KHỚP nội dung: khách Nhật vào `/` mà thấy tiếng Anh trong khi URL không
có `/en` là hỏng đúng cái lợi ích đã đánh đổi. Nên lần đầu (chưa có cookie, chưa
có tiền tố) thì chuyển hướng 302 sang URL đúng ngôn ngữ.

Chỉ chuyển hướng khi: GET, không phải đường miễn trừ, và URL chưa nói rõ ngôn ngữ.
"""
from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from platform_core import i18n
# ⭐ MỘT nguồn cho câu hỏi "điều hướng HTML hay lời gọi dữ liệu?" —
#    `require_login` (server/auth/session.py) hỏi đúng hàm này để quyết định
#    303-về-/login hay 401+JSON. Xem docstring của module đó.
from server.loai_request import la_dieu_huong_html


def _ho_so_ngon_ngu(request) -> str:
    """Ngôn ngữ lưu ở hồ sơ tài khoản. Đọc từ session để khỏi truy vấn CSDL mỗi
    request — phiên đã có sẵn trong cookie đã ký."""
    # Hỏi thẳng scope thay vì bắt ngoại lệ — xem ghi chú cùng loại ở
    # server/routes/ngon_ngu.py.
    if "session" not in request.scope:
        return ""
    return request.session.get("lang") or ""


class I18nMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        duong_goc = request.scope.get("path", "/")

        # Đường miễn trừ: không bóc, không đoán, không chuyển hướng. Đây là các
        # URL hệ thống bên ngoài gọi vào bằng địa chỉ cố định.
        if i18n.duoc_mien_tru(duong_goc):
            i18n.dat_ngon_ngu(i18n.GOC)
            return await call_next(request)

        duong, tien_to = i18n.tach_tien_to(duong_goc)

        # `/en/webhooks/...` không được là một đường hợp lệ. Để nó chạy nghĩa là
        # webhook có HAI địa chỉ, và sớm muộn sẽ có người đăng ký nhầm địa chỉ có
        # tiền tố với cổng thanh toán — rồi mất nó khi cách xử lý tiền tố đổi.
        if tien_to is not None and i18n.duoc_mien_tru(duong):
            from starlette.responses import PlainTextResponse
            return PlainTextResponse("Not Found", status_code=404)

        cookie = request.cookies.get(i18n.COOKIE, "")
        ho_so = _ho_so_ngon_ngu(request)
        quoc_gia = request.headers.get("cf-ipcountry", "")
        accept = request.headers.get("accept-language", "")
        lang = i18n.chon(tien_to=tien_to, cookie=cookie, ho_so=ho_so,
                         quoc_gia=quoc_gia, accept_language=accept)

        # Có tín hiệu nào để mà đoán không?
        #
        # Không có tín hiệu NÀO thì phục vụ bản gốc ở đường gốc, KHÔNG chuyển
        # hướng. Client không gửi `Accept-Language` lẫn `CF-IPCountry` không phải
        # trình duyệt người thật — đó là script, bộ giám sát, hay `curl`. Đá chúng
        # sang `/en/` chỉ tốn thêm một vòng và làm gãy các lệnh kiểm tra sức khoẻ
        # vốn mong nhận 200 chứ không phải 302.
        #
        # Lưu ý: `Accept-Language: ja-JP` VẪN là tín hiệu (client nói rõ nó không
        # đọc tiếng Việt) → vẫn đưa sang tiếng Anh, đúng ý chủ sản phẩm.
        #
        # Tiền tố trong URL là tín hiệu TƯỜNG MINH NHẤT nên phải nằm trong danh
        # sách này. Thiếu nó thì `/en/nap` mở bằng script sẽ bị coi là "không
        # biết gì" và tụt về tiếng Việt — tức URL nói một đằng, nội dung một nẻo.
        co_tin_hieu = bool(tien_to or cookie or ho_so or quoc_gia or accept)
        if not co_tin_hieu:
            lang = i18n.GOC

        # URL chưa nói rõ ngôn ngữ mà kết luận lại là tiếng Anh → đưa về đúng URL,
        # để địa chỉ khớp nội dung (xem docstring).
        if (tien_to is None and lang != i18n.GOC
                and request.method == "GET"
                and not request.headers.get("hx-request")
                and la_dieu_huong_html(request)):
            dich = i18n.them_tien_to(duong, lang)
            if request.scope.get("query_string"):
                dich += "?" + request.scope["query_string"].decode("latin-1")
            return RedirectResponse(dich, status_code=302)

        # Bóc tiền tố → router thấy đường dẫn như chưa từng có ngôn ngữ.
        request.scope["path"] = duong
        # `raw_path` là bytes; đường dẫn đã qua urldecode nên luôn mã hoá được.
        # Không cần try/except: nếu nó ném thì đó là lỗi thật, phải thấy.
        if request.scope.get("raw_path"):
            request.scope["raw_path"] = duong.encode("utf-8")

        i18n.dat_ngon_ngu(lang)
        request.state.lang = lang
        resp = await call_next(request)

        # Chuyển hướng nội bộ phải giữ nguyên ngôn ngữ, nếu không mọi 303 sau khi
        # submit form sẽ ném người dùng tiếng Anh về bản tiếng Việt.
        if 300 <= resp.status_code < 400 and lang != i18n.GOC:
            loc = resp.headers.get("location", "")
            if loc.startswith("/") and not loc.startswith("//"):
                MutableHeaders(raw=resp.raw_headers)["location"] = \
                    i18n.them_tien_to(loc, lang)

        # Cho bộ nhớ đệm biết trang đổi theo ngôn ngữ, kẻo CDN phục vụ bản tiếng
        # Việt cho người dùng tiếng Anh.
        vary = resp.headers.get("vary", "")
        # `Sec-Fetch-Mode`/`Accept` cũng quyết định có chuyển hướng hay không, nên
        # thiếu chúng trong `Vary` thì một bộ đệm dùng chung có thể lấy bản 200 của
        # `fetch()` đem phục vụ cho lần điều hướng lẽ ra phải 302.
        can = "Accept-Language, CF-IPCountry, Cookie, Accept, Sec-Fetch-Mode"
        MutableHeaders(raw=resp.raw_headers)["vary"] = f"{vary}, {can}" if vary else can
        return resp
