"""Proxy egress cho runner connector — **lọc miền NGOÀI tiến trình piece**.

## Vì sao tồn tại

`vo_boc.py` khoá mã piece trong một AppContainer **không** có capability
`internetClient` ⇒ piece không tự ra Internet được, kể cả qua tiến trình con,
kể cả bằng IP trần, kể cả bằng nhị phân native (đo 24/09, có đối chứng). Nhưng
một connector Slack **phải** gọi được `slack.com`. Cách duy nhất không phá ranh
giới là: mở **đúng loopback** cho vỏ (`vo_boc.ap_dung_loopback`) và bắt mọi
lưu lượng đi qua tiến trình này, nơi danh sách miền được áp.

⭐ Đây chính là hình dạng mà đội Activepieces đề xuất trong
   `activepieces/activepieces#11547` (*"lọc domain **ngoài tiến trình**"*, dẫn
   CVE-2025-68668 của n8n) — khác ở chỗ ta không cần microVM, vì AppContainer
   đã cho ranh giới ở mức token.

## Nó thấy gì, và ⛔ không thấy gì

Với `https://` trình khách gửi `CONNECT host:443` rồi **TLS đi thẳng tới đích**.
Proxy vì vậy chỉ thấy **tên miền + cổng**, ⛔ không thấy nội dung, ⛔ không giải
mã, ⛔ không có CA giả. Đó là đủ cho việc nó làm (chặn đích) và là điều **phải**
như vậy: một proxy đọc được nội dung thì mọi token của khách đi qua đây.

## Ba chỗ dễ làm sai, viết ra để khỏi phải nhớ

1. **So khớp theo NHÃN, không theo chuỗi con.** `slack.com.ke-tan-cong.vn`
   *chứa* `slack.com`. Luật ở đây: bằng đúng, hoặc là **miền con thật**
   (`.slack.com` ở cuối). `_khop_mien` có phép kiểm đối chứng cho ca đó.
2. **Chặn cổng.** Chỉ 80/443. Không có lý do gì để một piece `CONNECT` tới
   `slack.com:22`, và mở cổng tự do là mở một đường hầm.
3. **Loopback là của cả máy.** Miễn trừ loopback mở cửa này cho **mọi** tiến
   trình trên máy, không riêng vỏ. Nên mỗi lượt chạy sinh một **vé** ngẫu
   nhiên và proxy đòi `Proxy-Authorization`. Vé đi vào vỏ qua biến môi trường
   (mã piece đọc được — đúng ý đồ), nhưng tiến trình khác trên máy thì không.
"""
from __future__ import annotations

import base64
import secrets
import selectors
import socket
import socketserver
import threading
from dataclasses import dataclass, field

#: ⛔ Danh sách ĐÓNG. Một piece muốn cổng khác thì đó là một quyết định có
#:    review, không phải một tham số.
CONG_CHO_PHEP = (80, 443)

#: Trần một phiên proxy giữ kết nối. Dài hơn `han_ms` của một lệnh connector là
#: vô nghĩa — lệnh đã bị giết rồi.
HAN_SOCKET_S = 130.0

#: Kích thước bộ đệm khi bơm hai chiều.
DEM = 64 * 1024


def _khop_mien(host: str, cho_phep) -> bool:
    """`host` có thuộc danh sách miền không — so theo **nhãn**.

    ⭐ Đối chứng bắt buộc của hàm này: `slack.com.vidu.vn` phải **False**.
       Một phép `in` hay `endswith("slack.com")` trả True cho nó, và đó là
       toàn bộ giá trị của hàm này.
    """
    h = str(host or "").strip().lower().rstrip(".")
    for m in cho_phep:
        m = str(m).strip().lower().lstrip("*").lstrip(".").rstrip(".")
        if not m:
            continue
        if h == m or h.endswith("." + m):
            return True
    return False


@dataclass
class ChinhSach:
    """Miền được phép + vé. Một lượt chạy connector = một `ChinhSach`."""

    mien: tuple = ()
    ve: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    #: Nhật ký đích đã đi qua (để báo cáo/diễn tập), ⛔ không ghi nội dung.
    da_qua: list = field(default_factory=list)
    da_chan: list = field(default_factory=list)


class _Handler(socketserver.BaseRequestHandler):
    def handle(self):  # noqa: C901 — một giao thức, đọc tuần tự dễ hơn tách nhỏ
        cs: ChinhSach = self.server.chinh_sach
        self.request.settimeout(HAN_SOCKET_S)
        try:
            dau = self._doc_dau()
        except (OSError, ValueError):
            return
        if not dau:
            return
        dong = dau.split(b"\r\n")
        try:
            cach, dich, _ = dong[0].decode("latin-1").split(" ", 2)
        except ValueError:
            return self._tra(400, "yeu cau sai hinh dang")

        ve_ok = False
        for d in dong[1:]:
            if d.lower().startswith(b"proxy-authorization:"):
                gia_tri = d.split(b":", 1)[1].strip()
                if gia_tri.lower().startswith(b"basic "):
                    try:
                        raw = base64.b64decode(gia_tri[6:]).decode("latin-1")
                    except Exception:  # noqa: BLE001
                        raw = ""
                    ve_ok = secrets.compare_digest(raw.split(":", 1)[-1], cs.ve)
        if not ve_ok:
            cs.da_chan.append((dich, "thieu_ve"))
            return self._tra(407, "thieu ve proxy")

        if cach.upper() != "CONNECT":
            # ⛔ HTTP trần không đi qua đây. Một piece gọi `http://` là một
            #    piece gửi token của khách đi không mã hoá; chặn là đúng, và
            #    câu lỗi phải nói ra điều đó thay vì im lặng hỏng.
            cs.da_chan.append((dich, "khong_phai_CONNECT"))
            return self._tra(403, "chi chap nhan CONNECT (https)")

        host, _, cong_s = dich.rpartition(":")
        try:
            cong = int(cong_s)
        except ValueError:
            return self._tra(400, "cong sai")
        if cong not in CONG_CHO_PHEP:
            cs.da_chan.append((dich, "cong_cam"))
            return self._tra(403, f"cong {cong} khong duoc phep")
        if not _khop_mien(host, cs.mien):
            cs.da_chan.append((dich, "mien_ngoai_danh_sach"))
            return self._tra(403, "mien ngoai danh sach")

        try:
            ngoai = socket.create_connection((host, cong), timeout=20)
        except OSError as loi:
            cs.da_chan.append((dich, f"khong_noi_duoc:{loi.__class__.__name__}"))
            return self._tra(502, "khong noi duoc dich")
        cs.da_qua.append(dich)
        self.request.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        self._bom(self.request, ngoai)

    def _doc_dau(self) -> bytes:
        dem = b""
        while b"\r\n\r\n" not in dem:
            phan = self.request.recv(4096)
            if not phan:
                return b""
            dem += phan
            if len(dem) > 32 * 1024:
                raise ValueError("dau yeu cau qua lon")
        return dem.split(b"\r\n\r\n", 1)[0]

    def _tra(self, ma: int, ly_do: str) -> None:
        try:
            self.request.sendall(
                f"HTTP/1.1 {ma} {ly_do}\r\nContent-Length: 0\r\n"
                f"Connection: close\r\n\r\n".encode("latin-1"))
        except OSError:
            pass

    @staticmethod
    def _bom(a: socket.socket, b: socket.socket) -> None:
        sel = selectors.DefaultSelector()
        a.setblocking(False)
        b.setblocking(False)
        sel.register(a, selectors.EVENT_READ)
        sel.register(b, selectors.EVENT_READ)
        try:
            while True:
                su_kien = sel.select(timeout=HAN_SOCKET_S)
                if not su_kien:
                    return
                for khoa, _ in su_kien:
                    nguon = khoa.fileobj
                    dich = b if nguon is a else a
                    try:
                        du_lieu = nguon.recv(DEM)
                    except BlockingIOError:
                        continue
                    except OSError:
                        return
                    if not du_lieu:
                        return
                    try:
                        dich.sendall(du_lieu)
                    except OSError:
                        return
        finally:
            sel.close()
            for s in (a, b):
                try:
                    s.close()
                except OSError:
                    pass


class _May(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


@dataclass
class DangChay:
    cong: int
    ve: str
    chinh_sach: ChinhSach
    _may: object = None
    _luong: object = None

    @property
    def url(self) -> str:
        """URL proxy kèm vé — đi vào `HTTPS_PROXY` của tiến trình runner."""
        return f"http://ltt:{self.ve}@127.0.0.1:{self.cong}"

    def dung(self) -> None:
        if self._may is not None:
            self._may.shutdown()
            self._may.server_close()
            self._may = None


def mo(mien) -> DangChay:
    """Mở proxy trên **127.0.0.1 cổng 0** (hệ điều hành chọn cổng).

    ⛔ Không bao giờ bind `0.0.0.0`: máy A là production và một proxy mở ra
       mạng là một open relay.
    """
    cs = ChinhSach(mien=tuple(mien or ()))
    may = _May(("127.0.0.1", 0), _Handler)
    may.chinh_sach = cs
    # 🔴 `poll_interval` 20 ms, ⛔ KHÔNG để mặc định 500 ms.
    #
    #    `shutdown()` **chờ** vòng `serve_forever` thoát, và vòng ấy chỉ kiểm
    #    cờ dừng mỗi `poll_interval`. Với mặc định, mỗi lệnh connector trả
    #    thêm tới **0,5 giây** — đo 24/09: lệnh đo từ NGOÀI mất 512 ms trong
    #    khi phần việc thật (đo từ trong) chỉ 100 ms. 80 % độ trễ của một lệnh
    #    là ngồi chờ một vòng `select` nhàn rỗi.
    #
    # ⚠️ Bài học chung: hai phép đo cùng tên "độ trễ" ở hai chỗ khác nhau
    #    chênh 5 lần thì chỗ chênh CHÍNH LÀ thứ cần tìm — đừng chọn con số
    #    đẹp hơn.
    luong = threading.Thread(target=may.serve_forever, kwargs={"poll_interval": 0.02},
                             daemon=True, name="ltt-proxy-egress")
    luong.start()
    return DangChay(cong=may.server_address[1], ve=cs.ve, chinh_sach=cs,
                    _may=may, _luong=luong)


__all__ = ["CONG_CHO_PHEP", "ChinhSach", "DangChay", "mo"]
