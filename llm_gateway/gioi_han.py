"""
gioi_han.py — rào VẬT LÝ của một engine: số chuỗi và bể KV. (H38, V9 → phương án C)

⭐ MÁY A QUYẾT ĐỊNH, CỔNG NÀY CHỈ CHẶN THỨ ENGINE KHÔNG TỰ CHẶN ĐƯỢC
   (`docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md` §3, bước 3). Hai bất biến:

     số lượt đang chạy ≤ `-np`      — quá thì llama.cpp xếp một hàng đợi vô hình
     Σ token đặt chỗ   ≤ `-c`       — quá thì KV `-kvu` cạn và engine huỷ MỌI slot

   Hai con số đến từ `llama-swap.yaml` (`vat_ly.py`), không từ env.

⛔ KHÔNG CÒN LUẬT CÔNG BẰNG/NHỊP Ở ĐÂY. Đã gỡ ở bước 3:
     · khoá whale "một lượt cá voi một lúc" (O-01) — A tắt cờ khi byte đầu về,
       B giữ tới hết lượt ⇒ 429 sau 200 cho whale thứ hai A đã cho chờ tới 900 s;
     · RPM 120 lượt/phút (O-03) — sinh từ thời `--parallel 1`, A không có luật
       tương ứng ⇒ lượt thứ 121 bị 429 sau 200.
   Công bằng prefill và hạn mức theo khách là việc của máy A (`luat_nhan`,
   `public_api/limits.py`). Hai nơi cùng quyết một điều thì chúng lệch nhau.

⛔ ĐẦY THÌ TRẢ **429**, KHÔNG PHẢI 503. Máy A đọc 429 là *bận* và XẾP HÀNG LẠI
   lượt đó (O-04, bước 1); đọc 5xx là *hỏng* và đánh dấu lỗi cho khoá. Nhầm chỗ
   này thì khoá model nhà tự tắt sau 5 lần đông khách — cùng cái bẫy D-005.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger("llm_gateway.gioi_han")

#: Hạn giữ một suất trước khi coi nó là suất chết.
#:
#: 1.200 giây = 20 phút, rộng hơn `stream_timeout_s` (900) một biên dày. Phải
#: rộng hơn: thu hồi một suất **đang chạy thật** là cho thêm một lượt vào engine
#: đã đủ `-np` chuỗi (và trả lại phần KV nó vẫn đang chiếm), tức đổi một sự cố
#: tự khỏi lấy một sự cố tệ hơn.
#:
#: ⛔ Đừng hạ số này để "phát hiện sớm hơn". Muốn phát hiện sớm thì đọc
#:    `giu_lau_nhat_giay` ở `/health` — nó báo **ngay**, mà không đụng gì tới
#:    một lượt đang chạy.
HAN_GIU_MAC_DINH_S = 1200.0


@dataclass(frozen=True)
class PhanXuGioiHan:
    cho_qua: bool
    ly_do: str = ""
    #: Gợi ý cho header `Retry-After`, tính bằng giây.
    thu_lai_sau_s: int = 5
    #: Mã suất vừa cấp (0 khi từ chối). `cap_suat` dùng để dựng `Suat`.
    ma: int = 0


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

    __slots__ = ("_gh", "_ma", "_da_tra")

    def __init__(self, gh: "GioiHan", ma: int):
        self._gh = gh
        #: Mã riêng của suất này. Cần vì `GioiHan` nay giữ **thời điểm cấp của
        #: từng suất** để thu hồi suất quá hạn — một bộ đếm thuần không nói được
        #: suất nào đã treo bao lâu.
        self._ma = ma
        self._da_tra = False

    @property
    def da_tra(self) -> bool:
        return self._da_tra

    def tra(self) -> None:
        if self._da_tra:
            return
        self._da_tra = True
        self._gh._nha(self._ma)


class GioiHan:
    """Đếm chuỗi + bể KV của MỘT engine. An toàn khi nhiều luồng gọi (threadpool).

    `max_dong_thoi` = `-np`, `token_pool` = `-c` (đường thật dựng qua
    `SoTheoModel.tu_vat_ly`). `now` tiêm được để test không phải ngủ thật.
    """

    def __init__(self, *, max_dong_thoi: int = 1,
                 token_pool: int = 0,
                 han_giu_s: float = HAN_GIU_MAC_DINH_S,
                 now: Callable[[], float] = time.monotonic):
        self.max_dong_thoi = max(1, int(max_dong_thoi))
        #: Ngân sách KV **tính bằng token** của engine này. 0 = tắt.
        #:
        #: 🔴 VÌ SAO ĐẾM TOKEN CHỨ KHÔNG CHỈ ĐẾM SUẤT. `llama-server` chạy `-kvu`
        #:    (KV hợp nhất): mọi slot chia **một** bể `-c` token. Ba lượt vừa số
        #:    slot nhưng cộng lại vượt bể thì KV cạn — và khi KV cạn,
        #:    `server-context.cpp:3688-3724` **huỷ MỌI slot**, không chỉ slot gây
        #:    ra chuyện đó. Tức một khách xin prompt khổng lồ làm rơi lượt của hai
        #:    khách khác. Đếm suất không nhìn thấy điều đó; đếm token thì thấy.
        self.token_pool = max(0, int(token_pool))
        self.han_giu_s = float(han_giu_s)
        self._now = now
        self._khoa = threading.Lock()
        #: mã suất → `(thời điểm cấp, token đặt trước)`.
        #: **Không phải một bộ đếm.** Một con số chỉ nói "đang giữ mấy suất";
        #: map này còn nói *từ bao giờ* (⇒ thu hồi suất treo, xem
        #: `_thu_hoi_qua_han`) và *chiếm bao nhiêu token* (⇒ trả lại phần đặt
        #: chỗ đúng bằng lúc nhả, không phải bằng một phép trừ ở chỗ khác).
        self._dang_giu: dict[int, tuple] = {}
        self._ma_ke = 0
        self._da_thu_hoi = 0

    # ── đọc trạng thái, cho `/health` ────────────────────────────────────────
    def trang_thai(self) -> dict:
        with self._khoa:
            t = self._now()
            gia_nhat = max((t - g[0] for g in self._dang_giu.values()), default=0.0)
            return {"dang_chay": len(self._dang_giu),
                    "max_dong_thoi": self.max_dong_thoi,
                    # Token ĐANG đặt trước / bể KV của engine. Hai số này là thứ
                    # duy nhất nói được "còn nhận nổi một prompt dài nữa không" —
                    # `dang_chay` thì không, vì ba lượt ngắn và ba lượt 70K token
                    # cho cùng một con số 3.
                    "token_dat": sum(g[1] for g in self._dang_giu.values()),
                    "token_pool": self.token_pool,
                    # 🔴 HAI SỐ NÀY LÀ CẢ LÝ DO SỰ CỐ 31/08 KÉO SÁU GIỜ.
                    #
                    #    Hôm đó `/health` trả `dang_chay: 1` — đúng, đầy đủ, và
                    #    **không phân biệt được** một lượt đang chạy 3 giây với
                    #    một suất đã treo sáu tiếng. Người trực nhìn vào chỉ thấy
                    #    "có một việc đang chạy", tức trạng thái bình thường.
                    #
                    #    `giu_lau_nhat_giay` biến chuyện đó thành hiển nhiên:
                    #    một lượt thật hiếm khi quá vài phút.
                    "giu_lau_nhat_giay": round(gia_nhat, 1),
                    "han_giu_s": self.han_giu_s,
                    # Đếm số lần đã phải tự cứu. **Khác 0 nghĩa là CÓ BUG**, chỉ
                    # là bug đó không còn gây sự cố. Tự lành mà im lặng thì chỉ
                    # đổi một sự cố nhìn thấy được lấy một sự cố vô hình.
                    "da_thu_hoi": self._da_thu_hoi}

    # ── cổng vào ─────────────────────────────────────────────────────────────
    def _xin_vao(self, token_dat_truoc: int = 0) -> PhanXuGioiHan:
        """Hỏi VÀ chiếm chỗ trong cùng một lần giữ khoá.

        ⛔ RIÊNG TƯ CÓ CHỦ Ý. Nó tăng bộ đếm nhưng không giao lại thứ gì để trả
           lại — gọi nó trực tiếp là rò một suất, mỗi lần một suất, cho tới khi
           cổng trả 429 vĩnh viễn. `cap_suat()` là cửa duy nhất.
        """
        t = self._now()
        token_dat_truoc = max(0, int(token_dat_truoc))
        with self._khoa:
            self._thu_hoi_qua_han(t)

            if len(self._dang_giu) >= self.max_dong_thoi:
                # Đợi một lượt LLM xong mất hàng chục giây, nên gợi ý thử lại
                # cũng phải cùng thang đó. Bảo khách quay lại sau 1 giây là mời
                # họ tạo thêm một vòng lặp bận.
                return PhanXuGioiHan(
                    False,
                    f"dang chay {len(self._dang_giu)}/{self.max_dong_thoi} luot",
                    thu_lai_sau_s=15)

            if self.token_pool > 0:
                # 🔴 MỘT SUẤT KHÔNG KHAI TOKEN LÀ MỘT SUẤT **VÔ HÌNH** VỚI NGÂN
                #    SÁCH. Nó chiếm KV thật nhưng cộng vào bể bằng 0, nên bể luôn
                #    trông còn chỗ — và cái chốt này thôi chốt trong im lặng,
                #    đúng lúc nó đang được tin nhất.
                #
                # ⛔ Nên THÀ TỪ CHỐI CÒN HƠN ĐOÁN. Đoán thấp thì KV cạn và
                #    llama.cpp huỷ **mọi** slot; đoán cao thì 429 oan. Cả hai đều
                #    là hậu quả của việc bên gọi không khai, nên nó phải khai —
                #    `api.py` luôn khai (header của máy A, hoặc số của chính
                #    `ngan_sach`), nên đường này chỉ nổ khi có người nối dây sai.
                if token_dat_truoc <= 0:
                    return PhanXuGioiHan(
                        False,
                        "luot khong khai token dat truoc (pool KV dang bat) — "
                        "mot suat vo hinh voi ngan sach thi ngan sach thoi chot",
                        thu_lai_sau_s=5)
                da_dat = sum(g[1] for g in self._dang_giu.values())
                if da_dat + token_dat_truoc > self.token_pool:
                    return PhanXuGioiHan(
                        False,
                        f"vuot pool KV: dang dat {da_dat} + xin {token_dat_truoc} "
                        f"> {self.token_pool} token",
                        thu_lai_sau_s=15)

            self._ma_ke += 1
            self._dang_giu[self._ma_ke] = (t, token_dat_truoc)
            return PhanXuGioiHan(True, ma=self._ma_ke)

    def _thu_hoi_qua_han(self, t: float) -> None:
        """Thu lại suất giữ quá `han_giu_s`. **Gọi khi đã cầm khoá.**

        🔴 ĐÂY LÀ LƯỚI CUỐI, KHÔNG PHẢI ĐƯỜNG SỬA CHÍNH.

           Đường sửa chính là mọi lối ra đều trả suất, và `Suat` đã lo tính
           một-lần cho việc đó. Nhưng ngày 31/08 chứng minh rằng "mọi lối ra"
           là một danh sách người ta **tưởng** mình đã liệt kê đủ: `boc_luong`
           canh đúng ba đường (chạy hết · khách ngắt giữa chừng · thượng nguồn
           vỡ) và trượt đường thứ tư — generator **chưa bao giờ chạy**, nên khối
           `try` chưa từng được vào và `finally` không tồn tại về mặt thực thi.

           Hậu quả: một suất treo, `max_dong_thoi = 1`, và cổng trả 429 suốt
           **sáu giờ** trong khi GPU rảnh và model còn chưa nạp.

        ⭐ Nên lưới này KHÔNG cố đoán các đường rò. Nó chỉ khẳng định một điều
           yếu hơn nhưng đúng với mọi đường: **không lượt nào chạy lâu hơn
           `han_giu_s`**, nên suất nào giữ lâu hơn thế đều là suất chết.

        ⛔ VÀ NÓ PHẢI ỒN ÀO. Thu hồi trong im lặng chỉ đổi một sự cố nhìn thấy
           được lấy một sự cố vô hình — cổng vẫn chạy, không ai biết có bug, và
           lần rò tiếp theo lại mất đúng `han_giu_s` mỗi lượt.
        """
        if not self._dang_giu:
            return
        chet = [ma for ma, g in self._dang_giu.items() if t - g[0] > self.han_giu_s]
        for ma in chet:
            tuoi = t - self._dang_giu.pop(ma)[0]
            self._da_thu_hoi += 1
            log.warning(
                "THU HOI suat treo #%d: giu %.0f giay > han %.0f giay. "
                "Mot duong ra nao do da KHONG tra suat - day la BUG, cong chi "
                "dang tu cuu. Tong so lan thu hoi: %d",
                ma, tuoi, self.han_giu_s, self._da_thu_hoi)

    def cap_suat(self, token_dat_truoc: int = 0) -> tuple[PhanXuGioiHan, Optional[Suat]]:
        """Xin và cấp trong một nhịp. Được thì trả `(cho_qua, Suat)`.

        `token_dat_truoc` = số token KV lượt này sẽ chiếm ở **đỉnh** (số máy A
        khai qua `X-LTT-Token-Dat`, xem `vat_ly.token_giu`).

        ⛔ Với phản hồi streaming, gọi `suat.tra()` khi **luồng kết thúc**, không
           phải khi hàm xử lý trả về — `StreamingResponse` về ngay lập tức trong
           khi token còn chảy hàng chục giây sau đó. Phần token đặt trước được
           nhả **cùng lúc** với suất, vì nó nằm trong cùng một bản ghi.
        """
        px = self._xin_vao(token_dat_truoc)
        return (px, Suat(self, px.ma) if px.cho_qua else None)

    def _nha(self, ma: int) -> None:
        """Chỉ `Suat.tra()` được gọi. Gọi thẳng là bỏ qua chốt một-lần.

        `pop` chứ không phải trừ một: nếu suất này đã bị `_thu_hoi_qua_han` lấy
        đi thì bản ghi không còn, và trừ một lần nữa sẽ **cắt vào suất của người
        khác** — đúng cái lỗi âm-bộ-đếm mà `Suat` sinh ra để chặn.
        """
        with self._khoa:
            self._dang_giu.pop(ma, None)


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
