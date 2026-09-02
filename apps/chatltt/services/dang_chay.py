"""
dang_chay.py — sổ các lượt đang chảy TRONG TIẾN TRÌNH web, để phát sự kiện cho nhiều
người xem và để nút Dừng tới được luồng. (H43 Phase 08)

## Hai lớp, vì hai lý do khác nhau

1. **Sự thật** ở CSDL (`chatltt_execution.partial_text`, `status`) — Phase 07.
   Reload, tab thứ hai, hay một tiến trình web khác đều đọc được từ đó.
2. **Độ tươi** ở đây: một `Queue` cho mỗi người xem đang mở SSE trong cùng
   tiến trình, để delta tới trình duyệt ngay thay vì đợi nhịp ghi 1 s.

Người xem không cùng tiến trình (hoặc tới sau khi lượt xong) rơi về lớp 1: đọc
snapshot rồi poll — chậm hơn một nhịp ghi, nhưng **không bao giờ sai**.

## Dừng

`yeu_cau_dung()` đặt cờ trong tiến trình (nhanh) **và** route đã ghi
`status='cancelled'` xuống CSDL trước đó (chắc). Luồng chạy kiểm cả hai theo
nhịp — nên Dừng bấm ở tiến trình khác vẫn tới, chỉ chậm hơn một nhịp ghi.
"""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import Iterator, Optional

#: Khi hàng đợi của một người xem đầy (họ đọc chậm), ta bỏ delta cũ nhất của HỌ —
#: sự thật vẫn ở CSDL, và họ sẽ thấy đủ ở snapshot kế tiếp.
SUC_CHUA_HANG_DOI = 2000
_HET = object()


@dataclass
class LuotDangChay:
    execution_id: str
    user_id: str
    dung: threading.Event = field(default_factory=threading.Event)
    _nguoi_xem: list = field(default_factory=list)
    _khoa: threading.Lock = field(default_factory=threading.Lock)
    _xong: bool = False

    def phat(self, sk: dict) -> None:
        with self._khoa:
            nguoi_xem = list(self._nguoi_xem)
        for q in nguoi_xem:
            try:
                q.put_nowait(sk)
            except queue.Full:
                try:
                    q.get_nowait()
                except queue.Empty:
                    pass
                try:
                    q.put_nowait(sk)
                except queue.Full:
                    pass

    def ket_thuc(self) -> None:
        with self._khoa:
            self._xong = True
            nguoi_xem = list(self._nguoi_xem)
        for q in nguoi_xem:
            try:
                q.put_nowait(_HET)
            except queue.Full:
                pass

    def dang_ky(self) -> Optional["queue.Queue"]:
        """Một hàng đợi mới cho người xem; `None` nếu lượt đã xong (đọc CSDL thay vì chờ)."""
        with self._khoa:
            if self._xong:
                return None
            q: "queue.Queue" = queue.Queue(maxsize=SUC_CHUA_HANG_DOI)
            self._nguoi_xem.append(q)
            return q

    def huy_dang_ky(self, q) -> None:
        with self._khoa:
            try:
                self._nguoi_xem.remove(q)
            except ValueError:
                pass


_SO: dict = {}
_KHOA = threading.Lock()


def bat_dau(execution_id: str, user_id: str) -> LuotDangChay:
    with _KHOA:
        luot = LuotDangChay(execution_id=str(execution_id), user_id=str(user_id))
        _SO[str(execution_id)] = luot
        return luot


def tim(execution_id: str) -> Optional[LuotDangChay]:
    with _KHOA:
        return _SO.get(str(execution_id))


def ket_thuc(execution_id: str) -> None:
    with _KHOA:
        luot = _SO.pop(str(execution_id), None)
    if luot is not None:
        luot.ket_thuc()


def yeu_cau_dung(execution_id: str) -> bool:
    """Đặt cờ dừng trong tiến trình. `False` nếu lượt không chạy ở tiến trình này."""
    luot = tim(execution_id)
    if luot is None:
        return False
    luot.dung.set()
    return True


def theo_doi(q, *, cho_moi_lan_s: float = 15.0) -> Iterator[Optional[dict]]:
    """Đọc hàng đợi của một người xem: `None` mỗi khi hết `cho_moi_lan_s` mà không có gì
    (để route gửi `: ping`), dừng khi lượt kết thúc."""
    while True:
        try:
            sk = q.get(timeout=cho_moi_lan_s)
        except queue.Empty:
            yield None
            continue
        if sk is _HET:
            return
        yield sk
