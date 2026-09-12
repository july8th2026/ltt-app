"""huy_luot.py — hủy MỘT lượt LLM đang bay, tra theo **mã lượt**. (Multi-Job T11)

## Vì sao không chỉ dùng `ngat.py`

`ngat.SO_DONG` là sổ đóng theo **ngữ cảnh**, và nó trả lời đúng câu hỏi của cửa
đồng bộ: *"lượt mà CÂY GỌI NÀY đang chạy"* — ở đó người hủy chính là request đang
giữ khách, nên ngữ cảnh là thứ hai bên cùng có.

Job nền khác ở một điểm quyết định: người hủy là `POST /jobs/{id}/cancel`
(`server/api/jobs.py:524`) — một **request khác**, thường ở một tiến trình khác.
Từ đó không có ngữ cảnh nào chia sẻ được. Chỉ có một cái tên: `ma_luot`.

⇒ Tệp này là **chỉ mục thứ hai** lên đúng những hàm đóng ấy, tra theo tên, ở mức
  tiến trình. Không phải một cơ chế hủy thứ hai:

      ngat.SO_DONG   ->  "lượt của tôi"    (bản sao ngữ cảnh, không cần mã)
      huy_luot       ->  "lượt tên X"      (sổ tiến trình, cần mã)

⛔ HAI CHỈ MỤC, **MỘT** HÀM ĐÓNG. `dieu_phoi._goi_openai` ghi cùng một `_dong` vào
   cả hai sổ. Viết hai hàm đóng khác nhau là mở đường cho một đường hủy làm đủ
   việc (đóng socket **và** bảo máy B thôi) và đường kia làm nửa việc — và nửa
   việc ở đây nghĩa là GPU vẫn sinh chữ cho một người đã đi.

⚠️ PHẠM VI: **một tiến trình**, và đó là đủ cho đúng chỗ đang dùng nó. Worker canh
   `is_cancelled()` trong CHÍNH tiến trình đang gọi model (`apps/ltt_llm/jobs.py`),
   nên một sổ trong bộ nhớ là câu trả lời đúng — không phải một sự tạm bợ.
   Nếu một ngày tiến trình **web** muốn cắt lượt của worker thì cái nối hai tiến
   trình **đã có sẵn** và không cần tệp này lớn lên: `ma_luot` đi lên máy B qua
   `X-LTT-Request-Id`, và cổng có `POST /v1/huy`.

⛔ KHÔNG bao giờ `taskkill`, không `/unload` của llama-swap, không chạm slot khác.
   Đóng kết nối **là** cơ chế hủy: llama.cpp nhả slot ≤1 s sau khi client rời
   (`server-context.cpp:39`, `server-queue.cpp:607-617`). `/unload` của llama-swap
   thậm chí không mang tên model nên nó nhả cả hai card (L-17) — tức hủy lượt của
   mình bằng cách giết lượt của người khác.
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Callable, Iterator, Optional

log = logging.getLogger(__name__)


class Luot:
    """Một lượt đang bay ở máy A: cửa ra mạng của nó và cờ hủy.

    ⚠️ Bị hai luồng chạm (luồng gọi model ghi cửa; luồng canh `is_cancelled` bật
       cờ), nên cả hai đi qua một khoá.
    """

    __slots__ = ("ma", "_khoa", "_cua", "da_huy")

    def __init__(self, ma: str):
        self.ma = ma
        self._khoa = threading.Lock()
        self._cua: list[Callable[[], None]] = []
        self.da_huy = False

    def ghi_nhan(self, dong: Callable[[], None]) -> None:
        """Ghi một cửa. Đã hủy rồi mới ghi ⇒ đóng NGAY.

        ⚠️ Nhánh "đã hủy rồi" không phải phòng xa. Luồng canh thăm mỗi 1 giây và
           `httpx.Client` dựng trong vài micro giây: một lượt bị hủy đúng giữa hai
           việc ấy sẽ để lại một socket mà không ai đóng, vì `huy()` đã chạy xong
           một danh sách rỗng và không quay lại.
        """
        with self._khoa:
            self._cua.append(dong)
            da = self.da_huy
        if da:
            _dong_mot(dong)

    def huy(self) -> int:
        """Bật cờ rồi đóng mọi cửa. Trả số cửa đóng được. Idempotent."""
        with self._khoa:
            self.da_huy = True
            cua = list(self._cua)
        return sum(1 for dong in cua if _dong_mot(dong))


#: Sổ tiến trình. Một biến module (khác `llm_gateway.so_luot`, nơi sổ đi theo
#: `create_app`) vì ở đây **không có** một vật thể "ứng dụng" nào để bám vào:
#: worker là một tiến trình, và một lượt của nó là của cả tiến trình ấy.
_KHOA = threading.Lock()
_SO: dict[str, Luot] = {}


def ghi_danh(ma: str) -> Optional[Luot]:
    """Mở một lượt tên `ma`. Mã rỗng ⇒ `None` (lượt không hủy được theo tên).

    ⚠️ Trùng mã ⇒ trả lại **đúng vật thể đang có**, không đè. Đè sẽ làm cửa của
       lượt cũ biến mất khỏi sổ trong khi socket của nó còn mở — một lượt không
       hủy được nữa và không ai biết.
    """
    if not ma:
        return None
    with _KHOA:
        luot = _SO.get(ma)
        if luot is None:
            luot = Luot(ma)
            _SO[ma] = luot
        return luot


def xoa(ma: str) -> None:
    if not ma:
        return
    with _KHOA:
        _SO.pop(ma, None)


@contextmanager
def phien(ma: str) -> Iterator[Optional[Luot]]:
    """Ghi danh rồi rút, chắc chắn rút.

    ⛔ Phải rút: một mã còn trong sổ sau khi lượt xong nghĩa là `huy()` sẽ đóng
       một `httpx.Client` đã đóng (vô hại) và **trả `True`** cho bên hủy (có hại)
       — bên hủy sẽ tin là vừa cắt được một lượt không còn tồn tại.
    """
    luot = ghi_danh(ma)
    try:
        yield luot
    finally:
        xoa(ma)


def ghi_nhan(ma: str, dong: Callable[[], None]) -> None:
    """Ghi một cửa ra mạng cho lượt `ma`. Chưa ghi danh ⇒ ghi danh luôn."""
    luot = ghi_danh(ma)
    if luot is not None:
        luot.ghi_nhan(dong)


def huy(ma: str) -> bool:
    """Hủy lượt `ma`: đóng mọi cửa ra mạng của nó. `False` khi không có lượt ấy.

    ⛔ `False` chứ không im lặng thành `True`. Bên gọi dùng giá trị này để biết
       mình có thật sự cắt được gì hay không, và một `True` lạc quan biến "lượt đã
       xong từ lâu" thành "vừa hủy xong" — đúng loại câu làm người ta thôi kiểm.
    """
    with _KHOA:
        luot = _SO.get(ma)
    if luot is None:
        return False
    n = luot.huy()
    log.warning("huy luot %s: dong %s cua ra mang", ma, n)
    return True


def danh_dau(ma: str) -> None:
    """Bật cờ hủy mà **không** đóng gì — dùng khi người đóng là chính nó.

    ⭐ Cần vì `upstream`/`_goi_openai` phân biệt *"ta tự đóng"* với *"mạng chập"*
       bằng đúng cờ này. Đường hủy của `ngat` (khách ngắt cửa đồng bộ) đóng cửa
       qua sổ ngữ cảnh, không qua `huy()` ở trên — nếu nó không bật cờ thì lượt ấy
       sẽ bị phân loại thành `AmbiguousProviderError`, tức một lỗi provider.
    """
    luot = ghi_danh(ma)
    if luot is not None:
        with luot._khoa:                                 # noqa: SLF001 - cùng module
            luot.da_huy = True


def da_huy(ma: str) -> bool:
    if not ma:
        return False
    with _KHOA:
        luot = _SO.get(ma)
    return bool(luot is not None and luot.da_huy)


def dang_bay() -> int:
    with _KHOA:
        return len(_SO)


def _dong_mot(dong: Callable[[], None]) -> bool:
    """Đóng một cửa, nuốt lỗi nhưng **không lặng lẽ**.

    ⚠️ Cùng lập luận `ngat.dong_het`: ta đang ở đường hủy, và một `close()` hỏng
       không được che mất việc đóng những cửa còn lại — và nhất là không được che
       mất việc **hoàn tiền** ngay sau đó.
    """
    try:
        dong()
        return True
    except Exception:  # noqa: BLE001 - duong huy khong duoc nem
        log.exception("khong dong duoc cua ra mang khi huy luot")
        return False
