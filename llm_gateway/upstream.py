"""
upstream.py — lớp vận chuyển thật tới `llama-swap`, bằng `httpx`.

Tách khỏi phần còn lại để test chạy được **trên máy A, không cần GPU và không cần
llama-swap** — chỉ cần một đối tượng giả cùng hình dạng. Cùng lý do và cùng khuôn
với `render_gateway/http.py`.

⛔ `llama-swap` và `llama-server` chỉ nghe `127.0.0.1`. Lớp này **không bao giờ**
   được trỏ ra ngoài loopback, và **không bao giờ** làm proxy tới Internet: cổng
   trên máy B không được là một đường đi ra (Q102).
"""
from __future__ import annotations

from typing import Any, Iterator, Optional, Protocol

#: Mã nội bộ khi lớp vận chuyển hỏng. Không phải mã HTTP thật của thượng nguồn —
#: `api.py` dịch chúng thành mã cho khách. Chọn ngoài dải HTTP để không bao giờ
#: lẫn với một mã `llama-server` thật sự trả về.
#:
#: 🔴 VÌ SAO TÁCH HAI MÃ, KHÔNG DÙNG CHUNG MỘT. Trước 09/09 cả hai là `599`, và
#:    `api.py` dịch mọi thứ `>= 500` thành **502**. Máy A đọc 502 thành
#:    `CongVlmError` ⇒ `api_pool.danh_dau_loi()` ⇒ sau
#:    `ERROR_TO_STATUS_THRESHOLD` (5) lần thì `key.status = APIKEY_ERROR`.
#:
#: ⛔ VÀ `APIKEY_ERROR` **KHÔNG TỰ HỒI**. `api_pool._ung_vien` bỏ mọi khoá
#:    `status != ACTIVE`, và chỉ `APIKEY_COOLDOWN` mới tự về `ACTIVE` khi hết
#:    hạn. Tức **năm lần hết giờ là model nhà tắt, và nó ở lại tắt** cho tới khi
#:    có người vào sửa tay.
#:
#: ⭐ Đó đúng là thảm hoạ D-005 mà cả kho này đã cẩn thận bịt ở cửa **429** —
#:    chỉ là nó vào bằng cửa **hết giờ**, cửa không ai bịt. Một yêu cầu 200K
#:    prefill mất hàng phút là chuyện **bình thường** của hệ này, không phải
#:    dấu hiệu máy B hỏng.
MA_HET_GIO = 598
MA_KHONG_VOI_TOI = 599


class Upstream(Protocol):
    """Hình dạng mà `api.py` cần. Bản giả trong test cài đúng hai hàm này."""

    def json(self, method: str, path: str, *, body: Any = None,
             timeout: float = 60.0) -> tuple[int, bytes]: ...

    def stream(self, method: str, path: str, *, body: Any = None,
               timeout: float = 900.0) -> tuple[int, str, Iterator[bytes]]: ...


class HttpxUpstream:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def json(self, method: str, path: str, *, body: Any = None,
             timeout: float = 60.0) -> tuple[int, bytes]:
        import httpx
        try:
            r = httpx.request(method, self.base_url + path, json=body, timeout=timeout)
        except httpx.TimeoutException as e:
            # ⛔ PHẢI BẮT TRƯỚC `HTTPError` — `TimeoutException` là **con** của nó.
            #    Đảo thứ tự thì nhánh này chết và không ai thấy.
            return MA_HET_GIO, str(e).encode("utf-8", "replace")
        except httpx.HTTPError as e:
            # Trả 599 thay vì ném: `api.py` phân loại lỗi ở một chỗ duy nhất.
            return MA_KHONG_VOI_TOI, str(e).encode("utf-8", "replace")
        return r.status_code, r.content

    def stream(self, method: str, path: str, *, body: Any = None,
               timeout: float = 900.0) -> tuple[int, str, Iterator[bytes]]:
        """Chuyển tiếp SSE **nguyên xi**, không phân tích, không gom lại.

        ⛔ TUYỆT ĐỐI KHÔNG tự phân tích rồi dựng lại SSE. Cộng đồng đã mất thời
           gian vì đúng lỗi này: một harness dùng regex cắt delta ở dấu nháy đã
           thoát, làm mất chữ giữa dòng, và người ta tưởng là lỗi của engine
           (vllm-project/vllm#52469 — đã đóng, engine vô can). Cổng này là đường
           ống, không phải bộ dịch.

        ⚠️ `timeout` phải rộng: ở ngữ cảnh 200K, prefill có thể mất VÀI PHÚT trước
           byte đầu tiên (cộng đồng đo prefill ~1.000 tok/s ở đầu vào 100k).
        """
        import httpx
        client = httpx.Client(timeout=timeout)
        try:
            ctx = client.stream(method, self.base_url + path, json=body)
            r = ctx.__enter__()
        except httpx.TimeoutException as e:            # phải đứng TRƯỚC HTTPError
            client.close()
            return MA_HET_GIO, "text/plain", iter([str(e).encode("utf-8", "replace")])
        except httpx.HTTPError as e:
            client.close()
            return MA_KHONG_VOI_TOI, "text/plain", iter([str(e).encode("utf-8", "replace")])

        content_type = r.headers.get("content-type", "text/event-stream")

        def _di() -> Iterator[bytes]:
            try:
                for khoi in r.iter_raw():
                    yield khoi
            finally:
                dong()

        da_dong = [False]

        def dong() -> None:
            """Đóng kết nối thượng nguồn. Gọi bao nhiêu lần cũng được."""
            if da_dong[0]:
                return
            da_dong[0] = True
            try:
                ctx.__exit__(None, None, None)
            finally:
                client.close()

        # 🔴 VÌ SAO PHẢI GIAO RA MỘT HÀM ĐÓNG, KHÔNG CHỈ MỘT GENERATOR.
        #
        #    Kết nối đã MỞ ngay lúc này — `ctx.__enter__()` chạy ở trên, header
        #    đã về. Nhưng thứ đóng nó lại nằm trong `finally` của `_di`, và
        #    `finally` ấy chỉ tồn tại **sau khi generator chạy dòng đầu tiên**.
        #
        #    Không ai lặp qua `_di` thì khối `try` chưa từng được vào, nên
        #    `.close()` trên generator cũng **không** chạy `finally` — Python chỉ
        #    đánh dấu nó đã đóng. Kết quả: socket còn mở và `llama-server` sinh
        #    chữ tiếp cho một yêu cầu không còn ai đọc.
        #
        #    Đây đúng là đường đã gây sự cố 31/08 ở tầng trên (`boc_luong` giữ
        #    suất vĩnh viễn vì cùng lý do). Nên đường dọn phải gọi được **mà
        #    không cần generator khởi động**.
        return r.status_code, content_type, LuongUpstream(_di(), dong)


class LuongUpstream:
    """Luồng byte kèm một đường đóng gọi được **độc lập với việc lặp**.

    Vẫn là `Iterator[bytes]` nên `Upstream` protocol không đổi, và mọi bản giả
    trong test trả `iter([...])` vẫn dùng được — bên gọi hỏi `dong` bằng
    `getattr`, không đòi hỏi.
    """

    __slots__ = ("_it", "dong")

    def __init__(self, it: Iterator[bytes], dong):
        self._it = it
        self.dong = dong

    def __iter__(self) -> "LuongUpstream":
        return self

    def __next__(self) -> bytes:
        return next(self._it)

    def close(self) -> None:
        """`nhip_tim` tìm `.close()` để bảo thượng nguồn dừng sinh chữ.

        Đóng generator TRƯỚC (để `finally` của nó chạy nếu nó đã khởi động), rồi
        đóng thẳng — `dong` idempotent nên gọi hai lần vô hại.

        ⚠️ `getattr` chứ không gọi thẳng: **không phải iterator nào cũng có
           `close`**. Bản đầu của tôi gọi `self._it.close()` trần và vỡ với một
           `list_iterator` — tức nó chỉ chạy được với đúng generator thật, và
           mọi bản giả trong bộ test sẽ ném `AttributeError` **từ trong đường
           dọn dẹp**, nơi một ngoại lệ dễ nuốt mất cả việc đóng thượng nguồn.

        🔴 VÀ MỘT NGOẠI LỆ NỮA, ĐO ĐƯỢC TRÊN MÁY B 03/09:

               Exception ignored in: <generator object _di at 0x...>
                 File "llm_gateway/nhip_tim.py", line 110, in _di
                   dong()
                 File "llm_gateway/upstream.py", line 136, in close
                   dong_it()
               ValueError: generator already executing

           `nhip_tim` lặp generator này trong **một luồng phụ** (`bom`), nên khi
           đường dọn dẹp gọi `close()` từ luồng khác, luồng phụ có thể đang đứng
           **bên trong** `next()`. Đóng một generator đang chạy là bất hợp lệ, và
           Python ném `ValueError`.

        ⚠️ NÓI ĐÚNG MỨC ĐỘ: **suất KHÔNG bị rò vì chuyện này.** `dong()` nằm
           trong `finally` nên nó vẫn chạy dù `dong_it()` ném. Bản đầu của mục
           chú thích này viết rằng lỗi ấy "để lại một lượt chạy trên GPU" —
           **sai**, và sai theo hướng kịch tính hoá. Hậu quả thật hẹp hơn nhiều:
           một dòng `Exception ignored` vào log mỗi lần khách ngắt giữa chừng.

        ⭐ Vẫn đáng sửa, vì hai lý do đo được chứ không phải vì gọn mắt:
           một đường **dọn dẹp** mà ném thì lần sau ai thêm việc phía sau
           `dong_it()` sẽ mất việc đó mà không có cảnh báo; và dòng nhiễu ấy
           trông y hệt một sự cố thật trong `gateway_err.log` — nó đã làm mất
           thời gian của đúng phiên này ngày 03/09.

        ⛔ Nuốt đúng `ValueError`, và **chỉ** nó. Một `RuntimeError` từ đường dọn
           là một khuyết tật khác và phải nổi lên.
        """
        dong_it = getattr(self._it, "close", None)
        try:
            if dong_it is not None:
                dong_it()
        except ValueError:
            # Luồng phụ đang ở trong generator. `dong()` bên dưới vẫn dọn đủ.
            pass
        finally:
            self.dong()
