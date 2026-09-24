"""Request này là ĐIỀU HƯỚNG HTML hay LỜI GỌI DỮ LIỆU trong trang?

Một câu hỏi, MỘT câu trả lời. Hai lớp khác nhau cần nó và phải hỏi cùng chỗ:

* `server/i18n_middleware.py` — có chuyển hướng `/x` sang `/en/x` không?
  (`fetch()` không có thanh địa chỉ, chuyển hướng nó chỉ thêm một chặng.)
* `server/auth/session.py::require_login` — chưa đăng nhập thì trả 303 về
  `/login` hay 401 + JSON? (`fetch()` **đi theo** 303, nhận HTML của trang
  đăng nhập với `status: 200`, rồi `response.json()` nổ với một thông điệp
  không liên quan gì tới nguyên nhân thật — người dùng thấy một lỗi vô nghĩa
  thay vì "phiên đã hết hạn".)

Hàm sống ở một module trung lập vì nó KHÔNG thuộc i18n và cũng không thuộc
xác thực: nó chỉ đọc lời khai của client. Hai nơi trả lời cùng một câu hỏi
bằng hai cách là nguồn lệch về sau.
"""
from __future__ import annotations


def la_dieu_huong_html(request) -> bool:
    """Request này có phải trình duyệt MỞ CẢ TRANG không?

    Tiêu chí KHÔNG được là tiền tố đường dẫn. Thêm `/agent/api/` vào một danh
    sách vừa chỉ vá MỘT app — có 136 route `/api/` nằm dưới `route_prefix` của
    các app (`/chatltt/api/…`, `/autosubvideo/api/…`, …) và app sau lại dính
    đúng lỗi này.

    Hỏi chính trình duyệt thay vì đoán từ URL: `Sec-Fetch-Mode` (Fetch
    Metadata) là nơi nó khai request này là điều hướng hay lời gọi dữ liệu. Có
    header đó thì nó là lời khai TƯỜNG MINH, tin luôn. Không có (Safari <
    16.4, script) thì lùi về `Accept`.

    ⚠️ Mặc định khi KHÔNG có bằng chứng là `True` — giữ nguyên hành vi cũ. Đây
    là tiêu chí của cả trang web: chỉ thu hẹp ở nơi client đã nói rõ, để bản vá
    không lặng lẽ đổi hành vi cho một loại client chưa nghĩ tới. Cái giá:
    client máy-gọi-máy gửi `Accept: */*` mà không có Fetch Metadata vẫn ăn một
    chặng 302/303 như trước.
    """
    mode = request.headers.get("sec-fetch-mode", "")
    if mode:
        return mode == "navigate"
    accept = request.headers.get("accept", "")
    if not accept:
        return True
    return "text/html" in accept or "*/*" in accept


__all__ = ["la_dieu_huong_html"]
