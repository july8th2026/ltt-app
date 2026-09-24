"""Bộ gác SSRF — **một nguồn chân lý** cho mọi cuộc gọi ra mà khách chọn đích.

Trước 24/09/2026 phép kiểm này sống **duy nhất** trong
`platform_core/public_api/webhooks.py` (đường production đang chạy). Node
`core.http` của Workflow V2 cần đúng phép kiểm ấy: nếu nó chép một bản thứ
hai thì hai bản sẽ lệch nhau theo thời gian, và **bản lệch là bản có lỗ
hổng**. Nên bản gốc được rút ra đây, và `webhooks.py` gọi vào.

⭐ **Hỏi `is_global`, đừng liệt kê lớp địa chỉ.**

   Đo 24/09/2026: ``ipaddress.ip_address("100.64.0.1").is_private`` trả
   **False**. Dải CGNAT (RFC 6598, ``100.64.0.0/10``) đi lọt qua mọi bộ lọc
   kiểu ``is_private or is_reserved or is_loopback or ...`` — và hạ tầng VPS
   của dự án chạy NAT qua WireGuard, nên dải đó có thật trên máy này.

   ``is_global`` là **một mệnh đề** trả lời đúng câu cần hỏi: "địa chỉ này
   định tuyến được trên Internet công cộng không". Nó phủ ngược lại loopback,
   private, link-local, reserved, unspecified **cộng** CGNAT,
   ``192.0.0.0/24``, các dải tài liệu và IPv6 unique-local — mà không bắt ai
   phải nhớ bổ sung danh sách.

🔴 **Nhưng `is_global` MỘT MÌNH là chưa đủ, và bản production tưởng là đủ.**

   Đo trên CPython 3.13.12 ngày 24/09/2026 — không suy, chạy thật::

       ipaddress.ip_address("239.255.255.250").is_global  -> True   # SSDP/UPnP
       ipaddress.ip_address("224.0.0.1").is_global        -> True
       ipaddress.ip_address("ff02::1").is_global          -> True   # all-nodes
       ipaddress.ip_address("64:ff9b::7f00:1").is_global  -> True   # NAT64 ->
                                                                    # 127.0.0.1

   Tức **multicast đi lọt**, dù docstring của `webhooks.py` khai là `is_global`
   phủ multicast. ``239.255.255.250`` là đúng địa chỉ dùng để dò dịch vụ trong
   mạng LAN — nó là bàn đạp SSRF cổ điển, không phải ca lý thuyết.

   ⇒ Vị từ đúng là ``not is_global`` **HOẶC** ``is_multicast`` **HOẶC** IPv4
   lồng trong IPv6 không global **HOẶC** nằm trong `METADATA_ADDRESSES`.
   Hai vế giữa là **khác biệt cố ý** so với bản production trước 24/09 — chặt
   hơn, không lỏng hơn, và mỗi vế có một phép kiểm riêng trong
   `tests/test_2910_an_toan_mang.py`.

   So sánh nguồn ngoài: ``langchain_core/_security/_policy.py`` (commit
   ``7622d3dce760ac4be6d9aef4c653277e06064aea``) liệt kê 15 mạng IPv4 + 8
   mạng IPv6 bằng tay. Danh sách đó **đúng nhưng phải bảo trì**, và nó vẫn
   bỏ sót những dải ``is_global`` phủ (ví dụ ``233.252.0.0/24`` MCAST-TEST).
   Ta giữ `is_global`; thứ **đáng lấy** từ nguồn ấy là phép gỡ IPv4 lồng
   trong IPv6 (`go_ipv4_long_trong_ipv6`) và lối ghim IP của transport —
   xem `platform_core/http_an_toan.py`.

⚠️ `METADATA_ADDRESSES` giữ nguyên tập của bản production. Đo 24/09/2026 cho
   thấy **cả năm địa chỉ trong tập đó đã là `is_global == False`** (metadata
   dùng link-local, ULA hoặc CGNAT), nên hôm nay tập này là **thừa** — giữ
   lại vì nó rẻ, và vì một nhà cung cấp mới có thể đặt metadata trên một địa
   chỉ định tuyến được.
"""
from __future__ import annotations

import dataclasses
import ipaddress
import socket
from urllib.parse import urlparse

#: Mã lỗi — để nơi gọi dịch sang thông báo của riêng nó mà không phải khớp
#: chuỗi. `webhooks.validate_target` dùng đúng cơ chế này để giữ nguyên từng
#: câu thông báo của `/api/v1` sau khi phép kiểm được rút ra đây.
MA_RONG = "rong"
MA_QUA_DAI = "qua_dai"
MA_SO_DO = "so_do"
MA_THONG_TIN_DANG_NHAP = "thong_tin_dang_nhap"
MA_KHONG_CO_HOST = "khong_co_host"
MA_KHONG_PHAN_GIAI_DUOC = "khong_phan_giai_duoc"
MA_KHONG_CHO_PHEP = "khong_cho_phep"

#: Xem docstring mô-đun. Giữ y hệt bản `webhooks.py` trước khi rút ra.
METADATA_ADDRESSES = frozenset({"169.254.169.254", "fd00:ec2::254"})

#: URL dài hơn ngần này là rác hoặc là một phép thử — không phải địa chỉ thật.
DO_DAI_TOI_DA = 2000


class LoiChanSSRF(Exception):
    """Một URL bị bộ gác từ chối.

    `ma` là một trong các hằng `MA_*`. `str(exc)` cố tình **một câu cho mọi
    lớp bị chặn**: nơi gọi không được để khách dùng thông báo lỗi làm công cụ
    vẽ bản đồ mạng nội bộ.
    """

    def __init__(self, ma: str, thong_bao: str = "") -> None:
        self.ma = ma
        super().__init__(thong_bao or "Dia chi nay khong duoc phep.")


@dataclasses.dataclass(frozen=True)
class ChinhSach:
    """Cái gì được phép. Bất biến, để không ai sửa chính sách giữa hai hop.

    Khuôn lấy từ `SSRFPolicy` của `langchain_core._security._policy`
    (commit `7622d3dc`): một đối tượng chính sách truyền vào, thay vì một
    chuỗi cờ boolean rải rác ở từng nơi gọi.
    """

    #: Mặc định **chỉ https**. `http` rò rỉ cả nội dung lẫn chữ ký trên đường.
    so_do_cho_phep: frozenset[str] = frozenset({"https"})
    #: ⛔ CHỈ cho test và cho máy chủ giả cục bộ. Bật cái này trên đường khách
    #: chọn URL là mở thẳng cửa SSRF.
    cho_phep_noi_bo: bool = False
    do_dai_toi_da: int = DO_DAI_TOI_DA


CHINH_SACH_MAC_DINH = ChinhSach()
#: https-only nhưng cho địa chỉ nội bộ — dùng cho máy chủ giả trong test.
CHINH_SACH_NOI_BO = ChinhSach(so_do_cho_phep=frozenset({"http", "https"}),
                              cho_phep_noi_bo=True)


def go_ipv4_long_trong_ipv6(addr):
    """IPv4 nằm trong một địa chỉ IPv6, hoặc None.

    Port từ `_extract_embedded_ipv4` — `langchain_core/_security/_policy.py`,
    commit `7622d3dce760ac4be6d9aef4c653277e06064aea`.

    🔴 Lý do có hàm này: đo 24/09/2026,
    ``ipaddress.ip_address("64:ff9b::7f00:1").is_global`` trả **True** —
    tức ``is_global`` **một mình** cho lọt NAT64 (RFC 6052) bọc 127.0.0.1.
    IPv4-mapped (``::ffff:127.0.0.1``) thì `is_global` đã chặn đúng.
    """
    if not isinstance(addr, ipaddress.IPv6Address):
        return None
    if addr.ipv4_mapped is not None:
        return addr.ipv4_mapped
    # RFC 6052 (64:ff9b::/96) và RFC 8215 (64:ff9b:1::/48): IPv4 nằm ở 4 byte
    # cuối. Hai hằng lấy từ cùng tệp nguồn trên.
    for prefix in (ipaddress.IPv6Network("64:ff9b::/96"),
                   ipaddress.IPv6Network("64:ff9b:1::/48")):
        if addr in prefix:
            return ipaddress.IPv4Address(addr.packed[-4:])
    return None


def kiem_dia_chi(address, chinh_sach: ChinhSach = CHINH_SACH_MAC_DINH) -> None:
    """Một địa chỉ ĐÃ phân giải có được gọi tới không. Không thì raise."""
    if isinstance(address, str):
        address = ipaddress.ip_address(address)
    long_ben_trong = go_ipv4_long_trong_ipv6(address)
    if long_ben_trong is not None:
        address = long_ben_trong
    if chinh_sach.cho_phep_noi_bo:
        # Vẫn chặn metadata và multicast: một chính sách "dev" được mở đường
        # tới `127.0.0.1` của chính máy, **không** tới kho thông tin đăng nhập
        # của máy ảo, cũng không tới cả một mạng LAN qua một gói.
        if str(address) in METADATA_ADDRESSES or address.is_multicast:
            raise LoiChanSSRF(MA_KHONG_CHO_PHEP)
        return
    # ⚠️ `is_multicast` KHÔNG thừa — đo được `239.255.255.250` có
    #    `is_global == True`. Xem docstring mô-đun.
    if (not address.is_global
            or address.is_multicast
            or str(address) in METADATA_ADDRESSES):
        raise LoiChanSSRF(MA_KHONG_CHO_PHEP)


def _phan_giai_he_thong(host: str) -> list:
    return sorted({info[4][0] for info in socket.getaddrinfo(host, None)})


def phan_giai(host: str, resolver=None) -> list:
    """Mọi địa chỉ host phân giải ra — **tất cả** phải công cộng.

    Chỉ kiểm câu trả lời đầu là một lỗ: một tên có thể trả về một địa chỉ công
    cộng và một địa chỉ riêng tư, và client nối tới cái nào không phải thứ mã
    này điều khiển.
    """
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass
    lookup = resolver or _phan_giai_he_thong
    try:
        dia_chi = lookup(host)
    except OSError as exc:
        raise LoiChanSSRF(MA_KHONG_PHAN_GIAI_DUOC) from exc
    if not dia_chi:
        raise LoiChanSSRF(MA_KHONG_PHAN_GIAI_DUOC)
    return [ipaddress.ip_address(d) for d in dia_chi]


def kiem_hinh_dang(url: str,
                   chinh_sach: ChinhSach = CHINH_SACH_MAC_DINH) -> tuple[str, str]:
    """Phần kiểm **không** cần DNS. Trả `(url đã gọt, host)`."""
    raw = str(url or "").strip()
    if not raw:
        raise LoiChanSSRF(MA_RONG)
    if len(raw) > chinh_sach.do_dai_toi_da:
        raise LoiChanSSRF(MA_QUA_DAI)
    parsed = urlparse(raw)
    if (parsed.scheme or "").lower() not in chinh_sach.so_do_cho_phep:
        raise LoiChanSSRF(MA_SO_DO)
    if parsed.username or parsed.password:
        # Thông tin đăng nhập trong URL sẽ bị chép vào log, và chưa bao giờ
        # là thứ cần thiết.
        raise LoiChanSSRF(MA_THONG_TIN_DANG_NHAP)
    host = parsed.hostname or ""
    if not host:
        raise LoiChanSSRF(MA_KHONG_CO_HOST)
    return raw, host


def kiem_url(url: str, *, chinh_sach: ChinhSach = CHINH_SACH_MAC_DINH,
             resolver=None) -> str:
    """Kiểm một URL do bên ngoài chọn, hoặc raise `LoiChanSSRF`.

    Gọi **trước mỗi lần gửi** và **lại sau mỗi redirect**, không chỉ lúc lưu
    cấu hình: DNS đổi được giữa hai thời điểm đó, và một tên hôm qua trỏ ra
    địa chỉ công cộng hôm nay trỏ vào 127.0.0.1 (DNS rebinding).
    """
    raw, host = kiem_hinh_dang(url, chinh_sach)
    for address in phan_giai(host, resolver):
        kiem_dia_chi(address, chinh_sach)
    return raw


__all__ = [
    "CHINH_SACH_MAC_DINH", "CHINH_SACH_NOI_BO", "ChinhSach", "DO_DAI_TOI_DA",
    "LoiChanSSRF", "METADATA_ADDRESSES",
    "MA_KHONG_CHO_PHEP", "MA_KHONG_CO_HOST", "MA_KHONG_PHAN_GIAI_DUOC",
    "MA_QUA_DAI", "MA_RONG", "MA_SO_DO", "MA_THONG_TIN_DANG_NHAP",
    "go_ipv4_long_trong_ipv6", "kiem_dia_chi", "kiem_hinh_dang", "kiem_url",
    "phan_giai",
]
