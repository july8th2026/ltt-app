"""
dem_token_luong.py — đếm token từ một luồng SSE **đang chảy**. (H38, Q107, C5)

🔴 VÌ SAO KHÔNG ĐỢI TỚI CUỐI. Với một lượt không streaming, `usage` nằm gọn trong
   phản hồi và đọc lúc nào cũng được. Với streaming thì **luồng có thể không bao
   giờ tới cuối**: khách bấm Ctrl-C, mạng đứt, Cloudflare rớt. Mà GPU thì **đã
   đốt rồi**. Không đếm dọc đường thì ta chỉ còn hai lựa chọn tồi:

     - thu trọn phần đã giữ  ->  lỗi tiền im lặng, đúng cái đã tìm ra ở cửa job
     - không thu gì cả       ->  cho không một lượt sinh đã tốn điện và GPU

   Đếm dọc đường cho ta lựa chọn thứ ba, và là lựa chọn đúng: **thu đúng phần đã
   sinh ra**.

⛔ ĐÂY LÀ ỐNG NHÒM, KHÔNG PHẢI BỘ LỌC. Nó **không** sửa, không cắt, không dựng
   lại byte nào. Bên gọi vẫn chuyển tiếp nguyên xi; lớp này chỉ **nhìn** qua.
   Cộng đồng đã mất thời gian vì đúng lỗi ngược lại — một harness dùng regex cắt
   delta ở dấu nháy đã thoát, làm mất chữ giữa dòng (`upstream.stream`).

⛔ KHỐI SSE CẮT GIỮA DÒNG LÀ CHUYỆN THƯỜNG. `iter_raw()` trả về byte theo nhịp
   mạng, không theo nhịp dòng: một `data: {...}` hoàn toàn có thể tới làm ba
   khối. Phân tích từng khối rời rạc là hỏng ngẫu nhiên theo tải — loại lỗi chỉ
   hiện ra ở production. Nên lớp này **đệm cho tới khi thấy đủ một dòng**.

⭐ HAI GIAO THỨC, MỘT BỘ ĐẾM. Anthropic Messages và OpenAI Responses đặt `usage` ở
   hai chỗ khác nhau, nhưng cả hai đều là JSON trên dòng `data:`. Thay vì viết
   hai bộ phân tích, lớp này **quét mọi khối `usage` bắt gặp** và giữ giá trị lớn
   nhất từng thấy — xem `_gop`.
"""
from __future__ import annotations

import json
import logging
from typing import Iterator

log = logging.getLogger("platform_core.llm.dem_token_luong")

#: Tên các khoá `usage` mà hai giao thức dùng, quy về một mối.
#:
#: Anthropic:  input_tokens · output_tokens · cache_read_input_tokens
#: Responses:  input_tokens · output_tokens · (cache trong input_tokens_details)
VAO = ("input_tokens", "prompt_tokens")
RA = ("output_tokens", "completion_tokens")
CACHE = ("cache_read_input_tokens", "cached_tokens")


class DemToken:
    """Nhìn qua một luồng SSE và nhớ số token lớn nhất từng thấy.

    Dùng:

        dem = DemToken()
        for khoi in luong:
            dem.nhin(khoi)
            yield khoi                 # nguyen xi, khong sua gi
        su_dung = dem.su_dung()
    """

    __slots__ = ("_du", "token_vao", "token_ra", "token_cache", "_thay_usage")

    def __init__(self) -> None:
        self._du = b""
        self.token_vao = 0
        self.token_ra = 0
        self.token_cache = 0
        self._thay_usage = False

    @property
    def do_duoc(self) -> bool:
        """Đã thấy **ít nhất một** khối `usage` chưa.

        ⛔ Đây là câu hỏi khác với "token_ra > 0". Một luồng bị cắt ngay sau
           `message_start` có `output_tokens: 0` **và** đã thấy usage — đo được,
           và câu trả lời đúng là *không sinh chữ nào*. Còn một luồng vỡ trước cả
           `message_start` thì **không đo được**, và luật là không thu.
        """
        return self._thay_usage

    def nhin(self, khoi: bytes) -> None:
        """Nhìn một khối byte. Không trả về gì, không sửa gì."""
        if not khoi:
            return
        self._du += khoi
        # Chỉ xử lý phần ĐÃ trọn dòng; phần đuôi dở giữ lại cho khối sau.
        *dong, self._du = self._du.split(b"\n")
        for d in dong:
            self._mot_dong(d)

    def _mot_dong(self, dong: bytes) -> None:
        d = dong.strip()
        if not d.startswith(b"data:"):
            return                              # `event:`, chú thích, dòng trống
        than = d[5:].strip()
        if not than or than == b"[DONE]":
            return
        try:
            goi = json.loads(than)
        except (ValueError, TypeError):
            # Không phải JSON thì không phải thứ ta quan tâm. KHÔNG log ở mức
            # cảnh báo: luồng hợp lệ vẫn có những dòng ta không hiểu, và làm ngập
            # log là cách chắc nhất để không ai đọc log nữa.
            return
        self._quet(goi, 0)

    def _quet(self, x, sau: int) -> None:
        """Tìm mọi khối `usage` trong một cây JSON.

        ⭐ QUÉT THAY VÌ BIẾT TRƯỚC ĐƯỜNG DẪN. Anthropic để `usage` trong
           `message` ở `message_start` rồi ở gốc tại `message_delta`; Responses
           để nó trong `response` tại `response.completed`. Ghim đường dẫn nghĩa
           là mỗi lần một giao thức đổi chỗ là một lần thu tiền sai **mà không ai
           biết**. Quét thì đắt hơn vài micro giây và đúng ở cả ba.

        `sau` chặn đệ quy trên một cây dị thường — không phải phòng xa vô cớ:
        đầu vào ở đây đến từ mạng.
        """
        if sau > 6:
            return
        if isinstance(x, list):
            for m in x:
                self._quet(m, sau + 1)
            return
        if not isinstance(x, dict):
            return
        u = x.get("usage")
        if isinstance(u, dict):
            self._gop(u)
        # llama-server để số token **trúng cache** ở `timings.cache_n`, NGOÀI
        # `usage` — cùng chỗ `cong_vlm.doc_su_dung` đọc cho đường không stream.
        # Trước 03/09 lớp này bỏ qua nó ⇒ mọi lượt stream trả giá token vào
        # đầy đủ (50/1M) cho cả phần đã cache (10/1M): sai về phía khách, và
        # sai ở đường duy nhất mà khách agentic (Codex, ChatLTT) dùng.
        t = x.get("timings")
        if isinstance(t, dict):
            self.token_cache = max(self.token_cache, _so(t.get("cache_n")))
        for v in x.values():
            if isinstance(v, (dict, list)):
                self._quet(v, sau + 1)

    def _gop(self, u: dict) -> None:
        """Gộp một khối `usage`, lấy **giá trị lớn nhất** từng thấy.

        🔴 LẤY LỚN NHẤT, KHÔNG LẤY CÁI CUỐI. Anthropic phát `output_tokens: 0`
           trong `message_start` rồi số thật trong `message_delta`. Lấy cái cuối
           là đúng ở đây — nhưng chỉ đúng **khi luồng chạy tới cuối**. Một luồng
           bị cắt có thể để lại cái cuối là số 0 của `message_start`, và ta sẽ
           thu 0 cho một lượt đã sinh vài trăm token.

           Lấy lớn nhất đúng ở **cả hai** trường hợp, vì hai giao thức này chỉ
           tăng dần, không bao giờ giảm.
        """
        self._thay_usage = True
        # 🔴 (16/09, S4 R-04) Khối có `cache_read_input_tokens` là ngữ nghĩa ANTHROPIC:
        #    `input_tokens` LOẠI TRỪ cache (đo b10883: input 4 + cache 8826). Responses/Chat
        #    thì GỒM cache. Quy về một nghĩa — `token_vao` = tổng prompt — tại đây, vì
        #    `SuDung.token_vao_moi = token_vao - token_vao_cache` giả định nghĩa ấy.
        la_anthropic = "cache_read_input_tokens" in u
        cache_a = _so(u.get("cache_read_input_tokens"))
        for ten in VAO:
            gt = _so(u.get(ten))
            if la_anthropic and ten == "input_tokens":
                gt += cache_a
            self.token_vao = max(self.token_vao, gt)
        for ten in RA:
            self.token_ra = max(self.token_ra, _so(u.get(ten)))
        for ten in CACHE:
            self.token_cache = max(self.token_cache, _so(u.get(ten)))
        chi_tiet = u.get("input_tokens_details")
        if isinstance(chi_tiet, dict):
            for ten in CACHE:
                self.token_cache = max(self.token_cache, _so(chi_tiet.get(ten)))

    def su_dung(self):
        """Trả `SuDung` để `gia_token`/`thanh_toan` tính tiền.

        `dang_tin` = đã thấy usage. Không thấy ⇒ **không thu**, cùng luật
        `thanh_toan.quyet_toan_hoac_hoan`.
        """
        from platform_core.llm.cong_vlm import SuDung

        return SuDung(token_vao=self.token_vao, token_ra=self.token_ra,
                      token_vao_cache=min(self.token_cache, self.token_vao),
                      dang_tin=self._thay_usage)


def _so(x) -> int:
    return int(x) if isinstance(x, int) and not isinstance(x, bool) else 0


def dem_qua(luong: Iterator[bytes], dem: DemToken) -> Iterator[bytes]:
    """Bọc một luồng: nhìn qua từng khối rồi giao lại **nguyên xi**.

    ⛔ Không nuốt lỗi. Luồng vỡ giữa chừng thì lỗi phải nổi lên — nhưng `dem` vẫn
       giữ những gì đã đếm được tới lúc đó, và đó chính là số dùng để thu tiền.
    """
    for khoi in luong:
        dem.nhin(khoi)
        yield khoi
