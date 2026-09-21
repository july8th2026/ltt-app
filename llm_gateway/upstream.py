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

from typing import Any, Iterator, Protocol

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

#: Lượt bị **hủy theo yêu cầu** (`POST /v1/huy` đã đóng cửa ra mạng của nó).
#:
#: 🔴 VÌ SAO MÃ THỨ BA, KHÔNG DÙNG LẠI `MA_KHONG_VOI_TOI`. `httpx` ném **cùng
#:    một lớp ngoại lệ** cho "mạng chập" và cho "ta vừa tự đóng socket" — cả hai
#:    là `httpx.HTTPError`. Trộn chúng thì một lượt khách chủ động hủy sẽ ra 502,
#:    và máy A đọc 502 thành `CongVlmError` ⇒ `api_pool.danh_dau_loi()` ⇒ sau
#:    **5** lần `key.status = APIKEY_ERROR`, thứ **không tự hồi**.
#:
#: ⛔ Tức nếu không tách mã này, năm lần khách bấm "dừng" là model nhà tắt và ở
#:    lại tắt — đúng thảm hoạ D-005, chỉ vào bằng cửa **hủy**. Đây là lần thứ ba
#:    cùng một lớp lỗi đi qua đúng chỗ này (429, rồi hết giờ, giờ là hủy), nên
#:    luật viết cho gọn: **mọi kết cục KHÔNG PHẢI "máy B hỏng" phải có mã riêng.**
MA_DA_HUY = 597


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
        """Một lời gọi không stream — và nó **hủy được giữa chừng**.

        🔴 VÌ SAO KHÔNG PHẢI `httpx.request` NỮA. Cùng lý do `dieu_phoi._goi_openai`
           đã đổi ở máy A: `httpx.request` dựng một client bên trong rồi vứt đi,
           nên **không ai cầm được tay nắm để đóng nó**. Cửa đồng bộ là cửa duy
           nhất không tự dừng khi khách đi: thân endpoint chạy ở threadpool của
           uvicorn và không nhận tin khách đã ngắt, nên nếu không đóng được socket
           này thì `llama-server` sinh hết một lượt cho một người đã đi — và
           llama.cpp chỉ nhả slot ≤1 s **sau khi client rời** (`server-context.cpp:39`).

        ⛔ KHÔNG thêm tham số `dong=` vào chữ ký. Hình dạng hai hàm `json`/`stream`
           **là hợp đồng với bộ test** (xem đầu tệp: bản giả cùng hình dạng là
           điều kiện để test chạy trên máy A), và `FakeUpstream` của `test_250`
           cài đúng hai chữ ký ấy. Tay nắm đi qua `so_luot` — cùng khuôn
           `ContextVar` mà `platform_core/llm/ngat.py` dùng, và `so_luot` ghi rõ
           vì sao không import được chính tệp ấy.
        """
        import httpx

        from . import so_luot
        client = httpx.Client(timeout=timeout)
        so_luot.ghi_nhan(client.close)
        try:
            r = client.request(method, self.base_url + path, json=body)
            return r.status_code, r.content
        except httpx.TimeoutException as e:
            # ⛔ PHẢI BẮT TRƯỚC `HTTPError` — `TimeoutException` là **con** của nó.
            #    Đảo thứ tự thì nhánh này chết và không ai thấy.
            return MA_HET_GIO, str(e).encode("utf-8", "replace")
        except httpx.HTTPError as e:
            # 🔴 CÙNG NGOẠI LỆ, HAI NGHĨA. `client.close()` giữa một request đang
            #    đọc cũng ném `httpx.HTTPError` — y hệt một lần mạng chập. Hỏi
            #    `so_luot.da_huy()` là cách duy nhất phân biệt, và phân biệt sai
            #    ở đây có giá đã đo: xem `MA_DA_HUY` ở đầu tệp.
            if so_luot.da_huy():
                return MA_DA_HUY, b"huy theo yeu cau"
            # Trả 599 thay vì ném: `api.py` phân loại lỗi ở một chỗ duy nhất.
            return MA_KHONG_VOI_TOI, str(e).encode("utf-8", "replace")
        finally:
            client.close()

    def stream(self, method: str, path: str, *, body: Any = None,
               timeout: float = 900.0) -> tuple[int, str, Iterator[bytes]]:
        """Lớp vận chuyển trả SSE nguyên byte, không phân tích hay gom lại.

        Việc quan sát terminal frame thuộc `upstream_errors` ở lớp API.

        ⛔ TUYỆT ĐỐI KHÔNG tự phân tích rồi dựng lại SSE. Cộng đồng đã mất thời
           gian vì đúng lỗi này: một harness dùng regex cắt delta ở dấu nháy đã
           thoát, làm mất chữ giữa dòng, và người ta tưởng là lỗi của engine
           (vllm-project/vllm#52469 — đã đóng, engine vô can). Cổng này là đường
           ống, không phải bộ dịch.

        ⚠️ `timeout` phải rộng: ở ngữ cảnh 200K, prefill có thể mất VÀI PHÚT trước
           byte đầu tiên (cộng đồng đo prefill ~1.000 tok/s ở đầu vào 100k).
        """
        import httpx

        from . import so_luot
        client = httpx.Client(timeout=timeout)
        # ⚠️ Ghi tay nắm vào sổ NGAY, trước cả khi header về: `/v1/huy` có thể
        #    đến trong lúc prefill — ở ngữ cảnh 200K đó là **hàng phút** — và
        #    trước bản này thì cả khoảng ấy là một vùng không hủy được.
        so_luot.ghi_nhan(client.close)
        try:
            ctx = client.stream(method, self.base_url + path, json=body)
            r = ctx.__enter__()
        except httpx.TimeoutException as e:            # phải đứng TRƯỚC HTTPError
            client.close()
            return MA_HET_GIO, "text/plain", iter([str(e).encode("utf-8", "replace")])
        except httpx.HTTPError as e:
            client.close()
            if so_luot.da_huy():
                # Hủy đến trước header. Cùng lý do tách mã như ở `json` ở trên.
                return MA_DA_HUY, "text/plain", iter([b"huy theo yeu cau"])
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

        # ⭐ Cùng tay nắm ấy vào sổ lượt, để `POST /v1/huy` cắt được một luồng SSE
        #    đang chảy. Luồng đã có đường hủy qua `nhip_tim`/`BackgroundTask` khi
        #    **khách** ngắt; đường này là khi **máy A nói bằng lời** rằng thôi.
        from . import so_luot
        so_luot.ghi_nhan(dong)

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
