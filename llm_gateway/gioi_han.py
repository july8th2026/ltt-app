"""
gioi_han.py — hàng rào của riêng cổng VLM: đồng thời và tần suất. (H38, V9)

⭐ VÌ SAO CỔNG CẦN HÀNG RÀO RIÊNG, DÙ NỀN TẢNG ĐÃ CÓ:

   `public_api/limits.py` bảo vệ **nền tảng** khỏi khách. Cổng này nằm ở máy B và
   chỉ nghe LAN từ một IP — nó không sợ khách, nó sợ **chính máy A**: một vòng thử
   lại hỏng, một worker nhân đôi, một script ai đó chạy tay.

   Và nó sợ theo một kiểu khác. `llama-server` chạy `--parallel 1`, nên **50 yêu
   cầu đồng thời không thành 50 lượt song song** — chúng thành 50 kết nối treo và
   một hàng đợi không ai nhìn thấy. Người gọi thứ 50 chờ 50 lượt mà không có cách
   nào biết. Chờ vô hình còn tệ hơn một cái 429 rõ ràng.

⭐ ĐỒNG THỜI QUAN TRỌNG HƠN TẦN SUẤT ở đây, ngược với một API web thường:
   một lượt LLM kéo dài hàng chục giây, nên "20 lượt mỗi phút" gần như không chặn
   gì, còn "3 lượt cùng lúc" thì chặn đúng thứ cần chặn.

   `render_gateway` đã chốt cùng ý: *"Một GPU = một việc. Đổi số này là mời OOM."*
   Ở đây nới hơn một chút vì `llama-swap` xếp hàng giúp, nhưng nguyên tắc y hệt.

⛔ ĐẦY THÌ TRẢ **429**, KHÔNG PHẢI 503. Bên gọi (`dieu_phoi`) coi 429 là *bận* và
   đi tiếp; coi 5xx là *hỏng* và đánh dấu lỗi cho khoá. Nhầm chỗ này thì khoá model
   nhà tự tắt sau 5 lần đông khách — cùng cái bẫy D-005.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class PhanXuGioiHan:
    cho_qua: bool
    ly_do: str = ""
    #: Gợi ý cho header `Retry-After`, tính bằng giây.
    thu_lai_sau_s: int = 5


class Suat:
    """Một suất đã cấp. Trả lại bằng `tra()`, và **trả bao nhiêu lần cũng được**.

    🔴 TÍNH MỘT-LẦN LÀ CẢ MỤC ĐÍCH CỦA LỚP NÀY, không phải sự cẩn thận thừa. Bản
       đầu tôi để `gh.xong()` trần, và một đường lỗi đã trả **hai lần**: `finally`
       trong hàm chạy trả một lần, rồi `except` ở hàm gọi trả tiếp. Bộ đếm tụt
       xuống dưới số thật, cổng nhận nhiều lượt hơn hạn mức, và chốt đồng thời
       lặng lẽ ngừng chốt. Không có lỗi nào được ném ra — nó chỉ thôi bảo vệ.

       Chiều ngược lại (quên trả) thì cổng tự bóp cổ mình: 429 vĩnh viễn trong khi
       GPU rảnh hoàn toàn. Cả hai đều câm, nên tính đúng phải nằm trong kiểu dữ
       liệu, đừng để nó phụ thuộc vào việc đọc kỹ luồng điều khiển.
    """

    __slots__ = ("_gh", "_da_tra")

    def __init__(self, gh: "GioiHan"):
        self._gh = gh
        self._da_tra = False

    @property
    def da_tra(self) -> bool:
        return self._da_tra

    def tra(self) -> None:
        if self._da_tra:
            return
        self._da_tra = True
        self._gh._nha()


class GioiHan:
    """Đếm đồng thời + tần suất. An toàn khi nhiều luồng gọi (uvicorn dùng threadpool).

    `now` tiêm được để test không phải ngủ thật.
    """

    def __init__(self, *, max_dong_thoi: int = 2, rpm: int = 120,
                 now: Callable[[], float] = time.monotonic):
        self.max_dong_thoi = max(1, int(max_dong_thoi))
        self.rpm = max(0, int(rpm))          # 0 = tắt chốt tần suất
        self._now = now
        self._khoa = threading.Lock()
        self._dang_chay = 0
        self._moc: deque = deque()

    # ── đọc trạng thái, cho `/health` ────────────────────────────────────────
    def trang_thai(self) -> dict:
        with self._khoa:
            self._cuon(self._now())
            return {"dang_chay": self._dang_chay,
                    "max_dong_thoi": self.max_dong_thoi,
                    "trong_phut_qua": len(self._moc),
                    "rpm": self.rpm}

    def _cuon(self, t: float) -> None:
        """Bỏ các mốc cũ hơn 60 giây. Cửa sổ trượt, không phải ô cố định.

        Ô cố định cho phép gấp đôi hạn mức quanh ranh giới phút — chuyện nhỏ với
        một API web, chuyện thật với một GPU chỉ chạy được một lượt một lúc.
        """
        while self._moc and t - self._moc[0] > 60.0:
            self._moc.popleft()

    # ── cổng vào ─────────────────────────────────────────────────────────────
    def _xin_vao(self) -> PhanXuGioiHan:
        """Hỏi VÀ chiếm chỗ trong cùng một lần giữ khoá.

        ⛔ RIÊNG TƯ CÓ CHỦ Ý. Nó tăng bộ đếm nhưng không giao lại thứ gì để trả
           lại — gọi nó trực tiếp là rò một suất, mỗi lần một suất, cho tới khi
           cổng trả 429 vĩnh viễn. `cap_suat()` là cửa duy nhất.
        """
        t = self._now()
        with self._khoa:
            self._cuon(t)

            if self._dang_chay >= self.max_dong_thoi:
                # Đợi một lượt LLM xong mất hàng chục giây, nên gợi ý thử lại
                # cũng phải cùng thang đó. Bảo khách quay lại sau 1 giây là mời
                # họ tạo thêm một vòng lặp bận.
                return PhanXuGioiHan(
                    False,
                    f"dang chay {self._dang_chay}/{self.max_dong_thoi} luot",
                    thu_lai_sau_s=15)

            if self.rpm and len(self._moc) >= self.rpm:
                cho = max(1, int(61.0 - (t - self._moc[0])))
                return PhanXuGioiHan(
                    False, f"vuot {self.rpm} luot moi phut", thu_lai_sau_s=cho)

            self._dang_chay += 1
            self._moc.append(t)
            return PhanXuGioiHan(True)

    def cap_suat(self) -> tuple[PhanXuGioiHan, Optional[Suat]]:
        """Xin và cấp trong một nhịp. Được thì trả `(cho_qua, Suat)`.

        ⛔ Với phản hồi streaming, gọi `suat.tra()` khi **luồng kết thúc**, không
           phải khi hàm xử lý trả về — `StreamingResponse` về ngay lập tức trong
           khi token còn chảy hàng chục giây sau đó.
        """
        px = self._xin_vao()
        return (px, Suat(self) if px.cho_qua else None)

    def _nha(self) -> None:
        """Chỉ `Suat.tra()` được gọi. Gọi thẳng là bỏ qua chốt một-lần."""
        with self._khoa:
            self._dang_chay = max(0, self._dang_chay - 1)


def boc_luong(luong, suat: Suat):
    """Bọc một luồng SSE sao cho suất được trả khi luồng **kết thúc hoặc bị bỏ**.

    ⭐ TÁCH RA KHỎI `api.py` VÌ NÓ PHẢI ĐO ĐƯỢC THẲNG. `TestClient` của Starlette
       hút cạn thân phản hồi **trước cả khi** trả `status_code` về — tôi đã viết
       một test HTTP tưởng là chứng minh được "suất còn giữ giữa luồng", chạy nó,
       và nó đo một thứ khác hẳn cái ghi trên nhãn. Ở đây thì câu hỏi rõ ràng:
       generator này nhả suất vào đúng lúc nào.

    ⛔ `finally` chứ không phải "sau vòng lặp". Khách đóng kết nối giữa chừng thì
       Starlette gọi `.aclose()`, Python ném `GeneratorExit` vào ngay chỗ `yield`,
       và nhánh sau vòng lặp **không bao giờ chạy**. Một khách hay bấm Stop sẽ rò
       hết số suất trong vài phút, và triệu chứng là 429 vĩnh viễn với GPU rảnh.
    """
    try:
        for phan in luong:
            yield phan
    finally:
        suat.tra()
