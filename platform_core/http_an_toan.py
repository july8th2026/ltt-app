"""Client HTTP cho những cuộc gọi mà **bên ngoài chọn đích**.

PORT từ ``langchain_core/_security/_transport.py`` — repo
``langchain-ai/langchain``, commit
``7622d3dce760ac4be6d9aef4c653277e06064aea`` (lớp ``SSRFSafeSyncTransport``
và factory ``ssrf_safe_client``). Thứ **đáng lấy** ở đó là lối **ghim IP**;
vị từ chặn vẫn là `platform_core.an_toan_mang` (P5/T1), không phải danh
sách mạng gõ tay của họ.

⭐ **Vì sao ghim IP, chứ không "kiểm rồi gọi".**

   `platform_core/public_api/delivery.py` hôm nay kiểm URL rồi đưa cho
   urllib gọi. Giữa hai bước đó có **hai lần phân giải DNS**: một lần để
   kiểm, một lần khi mở kết nối. Kẻ tấn công điều khiển được DNS chỉ cần
   trả địa chỉ công cộng cho lần đầu và ``127.0.0.1`` cho lần sau — bộ gác
   thấy một thứ, socket nối tới một thứ khác (DNS rebinding, đúng khuôn
   TOCTOU).

   Ghim IP **xoá hẳn** cửa sổ đó: phân giải **một lần**, kiểm **mọi** địa
   chỉ trả về, rồi nối tới đúng địa chỉ đã kiểm — trong khi vẫn giữ
   ``Host`` và SNI là tên gốc, nếu không thì virtual host và chứng chỉ TLS
   đều hỏng và cách này sẽ không dùng được thật.

⚠️ `follow_redirects` đặt ở **client**, nên httpx gọi lại transport cho
   **từng hop** — mỗi hop vì thế tự đi qua bộ gác, không cần vòng lặp
   redirect viết tay như `delivery.py`.

⛔ Không dùng cho việc gọi các dịch vụ **nội bộ** của nền tảng (máy B,
   gateway): những chỗ đó đích do ta chọn, và chính sách mặc định ở đây sẽ
   từ chối chúng.
"""
from __future__ import annotations

import httpx

import platform_core.an_toan_mang as an_toan_mang

#: Khoá httpx nhận ở TRANSPORT; mọi khoá khác đi vào `httpx.Client`.
#: Danh sách lấy từ `_TRANSPORT_KWARGS` của tệp nguồn nói trên.
_KHOA_TRUYEN_TAI = frozenset({"verify", "cert", "trust_env", "http1", "http2",
                              "limits", "retries"})

#: Đủ cho một API thật trả lời, ngắn để một đích treo không giữ worker.
THOI_CHO_MAC_DINH_S = 30.0
SO_REDIRECT_TOI_DA = 3


class TruyenTaiAnToan(httpx.BaseTransport):
    """Transport httpx: phân giải, kiểm **mọi** địa chỉ, rồi ghim IP.

    `bo_phan_giai(host) -> list[str]` để test cắm DNS giả vào. Mặc định là
    bộ phân giải hệ thống của `an_toan_mang`.
    """

    def __init__(self, chinh_sach: an_toan_mang.ChinhSach | None = None,
                 bo_phan_giai=None, **tham_so_truyen_tai) -> None:
        self.chinh_sach = chinh_sach or an_toan_mang.CHINH_SACH_MAC_DINH
        self.bo_phan_giai = bo_phan_giai
        self._trong = httpx.HTTPTransport(**tham_so_truyen_tai)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        # 1. Sơ đồ, thông tin đăng nhập trong URL, có host hay không.
        an_toan_mang.kiem_hinh_dang(str(request.url), self.chinh_sach)

        host = request.url.host or ""
        # 2. MỘT lần phân giải. 3. Mọi địa chỉ trả về đều phải qua bộ gác —
        #    một tên trả một địa chỉ công cộng và một địa chỉ riêng tư thì
        #    cái thứ hai mới là cái kẻ tấn công nhắm tới.
        dia_chi = an_toan_mang.phan_giai(host, self.bo_phan_giai)
        for d in dia_chi:
            an_toan_mang.kiem_dia_chi(d, self.chinh_sach)

        # 4. Ghim vào địa chỉ ĐẦU TIÊN — chính là một trong những địa chỉ
        #    vừa qua bộ gác ở trên, không phải một lần phân giải mới.
        ghim = str(dia_chi[0])
        url_ghim = request.url.copy_with(host=ghim)

        # 5. Giữ `Host` (httpx đã đặt sẵn tên gốc trong headers) và ép SNI
        #    về tên gốc, nếu không chứng chỉ TLS sẽ không khớp.
        mo_rong = dict(request.extensions)
        if request.url.scheme.lower() == "https":
            mo_rong["sni_hostname"] = host.encode("ascii")

        return self._trong.handle_request(httpx.Request(
            method=request.method, url=url_ghim, headers=request.headers,
            stream=request.stream, extensions=mo_rong))

    def close(self) -> None:
        self._trong.close()


def tao_client(chinh_sach: an_toan_mang.ChinhSach | None = None,
               bo_phan_giai=None, **tham_so) -> httpx.Client:
    """`httpx.Client` đã gắn bộ gác. Đóng bằng `with` hoặc `.close()`.

    ⛔ Không đặt cookie jar và không `trust_env` proxy mặc định: một jar
    dùng chung là trạng thái đi lại giữa các đích của khách, còn một proxy
    lấy từ môi trường là một cửa hậu vòng qua toàn bộ bộ gác này.
    """
    tham_so_truyen_tai = {k: v for k, v in tham_so.items()
                          if k in _KHOA_TRUYEN_TAI}
    tham_so_client = {k: v for k, v in tham_so.items()
                      if k not in _KHOA_TRUYEN_TAI}
    tham_so_truyen_tai.setdefault("trust_env", False)

    tham_so_client.setdefault("follow_redirects", True)
    tham_so_client.setdefault("max_redirects", SO_REDIRECT_TOI_DA)
    tham_so_client.setdefault("timeout", THOI_CHO_MAC_DINH_S)
    tham_so_client.setdefault("trust_env", False)

    return httpx.Client(
        transport=TruyenTaiAnToan(chinh_sach=chinh_sach,
                                  bo_phan_giai=bo_phan_giai,
                                  **tham_so_truyen_tai),
        **tham_so_client)


__all__ = ["SO_REDIRECT_TOI_DA", "THOI_CHO_MAC_DINH_S", "TruyenTaiAnToan",
           "tao_client"]
