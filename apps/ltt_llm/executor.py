"""Synchronous protocol adapter for the LTT LLM app.

The HTTP layer only knows this narrow contract through the app manifest.  The
business rules remain in ``features.py``; this module is the app-owned bridge.
"""
from __future__ import annotations

from apps.ltt_llm import features


class _Executor:
    #: ⛔ `default_max_tokens` KHÔNG còn tồn tại — nó là gốc của lỗi 30/08.
    #:
    #:    Một tên chung chung khiến cửa **stream** lấy ngân sách 1.024 của cửa
    #:    **đồng bộ** mà không ai phải nói mình đang ở cửa nào; mọi câu trả lời
    #:    dài cụt ở đúng 1.024 token, im lặng. Nay bên gọi **bắt buộc nêu cửa**.
    parameter_error = features.ThamSoSai

    @staticmethod
    def mac_dinh_cho(cua: str) -> int:
        """Token ra mặc định của một cửa: `"sync"`, `"stream"` hoặc `"job"`."""
        from apps.ltt_llm.ngan_sach import mac_dinh_cho
        return mac_dinh_cho(cua)

    def aliases(self):
        return dict(features.ALIAS_SANG_ID)

    def validate(self, params):
        return features.kiem_tham_so(params)

    def validate_generation(self, params):
        """Kiem CHI tham so sinh — cho cua STREAM, noi `messages` co hinh khac.

        🔴 Do 14/09/2026 tren production, cung mot gia tri sai `top_p=5`:

               POST /api/v1/chat/completions (dong bo) -> 400 invalid_request
               POST /api/v1/messages         (stream)  -> 200, chay binh thuong

           Cua stream khong goi `validate`: `runtime_noi_bo/luong.tien_kiem` lam
           `gui = dict(than)` — chep ca than request len may B. Mot hop dong
           cong bo, hai cua tra loi khac nhau.

        ⛔ Va no KHONG the goi `validate`: `/messages` mang `system`,
           `/responses` mang `input` co the la chuoi tran; dua chung qua bo kiem
           day du la tai dien loi 500 ma `_tin_that` da ghi ("moi phan tu cua
           messages phai co role").

        ⭐ Khuon cua cong dong: vLLM khai MOT `ChatCompletionRequest` trong do
           `stream` chi la mot truong, va moi validator chay TRUOC khi re nhanh
           stream. Day la cach ap khuon ay ma van giu duoc ranh gioi tang:
           `platform_core` khong duoc import `apps/` (.importlinter), nen cua
           stream hoi qua chinh executor cua app.
        """
        return features.kiem_tham_so_sinh(params)

    def check_output_floor(self, params):
        """Tu choi `max_tokens` thap den muc chac chan tra RONG.

        ⛔ TACH KHOI `validate` co chu y: phep kiem nay phai chay SAU 413, va
           `validate` chay TRUOC. Ly do day du o `features.kiem_san_token_ra`.
        """
        features.kiem_san_token_ra(params)

    def estimate_input(self, messages, tools=None):
        return (features.uoc_token_vao(messages) if tools is None
                else features.uoc_token_vao(messages, tools))

    def sync_output_cap(self, token_input, budget_seconds):
        return features.tran_token_ra_dong_bo(token_input, budget_seconds)

    def context_output_cap(self, token_input, alias=None):
        """Trần token RA còn lại trong ngữ cảnh — **theo model** khi biết model.

        ⛔ `alias=None` KHÔNG rơi về model mặc định: nó rơi về **cửa sổ hẹp
           nhất** trong các model đang bán (`ngan_sach.CUA_SO_HEP_NHAT`). Bên gọi
           không nêu model là bên gọi không biết mình ở model nào; kẹp rộng hơn
           cửa sổ thật của model đang chạy là để model tự cắt ngữ cảnh — hỏng
           không sạch, và đó đúng là lớp lỗi F-02.

        ⭐ Nhận **bí danh công khai** (`ltt-3.8`), không phải id nội bộ: id nội bộ
           không bao giờ được rời máy A (INV-015), nên bên gọi ở nền tảng chỉ
           cầm bí danh. Bí danh lạ ⇒ `KeyError`, không đoán.
        """
        from apps.ltt_llm.manifest import tran_theo_ngu_canh
        model_id = None if alias is None else features.ALIAS_SANG_ID[alias]
        return tran_theo_ngu_canh(token_input, model_id)

    def input_cap(self, alias):
        """Trần token VÀO của một alias (theo model: vision nhỏ hơn text).

        multijob D-06: cửa stream nay gửi 200 TRƯỚC khi chạm máy B, nên "quá dài
        ⇒ 413" phải được nền tảng hỏi trước 200 — Codex/Claude Code dựa vào HTTP
        413 để TỰ NÉN hội thoại. Nền tảng không import app; nó hỏi qua đây.
        """
        from apps.ltt_llm.ngan_sach import tran_vao_cua
        return tran_vao_cua(features.ALIAS_SANG_ID[alias])

    def run(self, db, params, *, timeout_s, on_dispatch=None, on_rejected=None,
            ma_luot: str = "", budget_suy_nghi=None):
        """Chạy một lượt. `ma_luot` là **tên để cắt lượt này từ ngoài**.

        🔴 THIẾU `ma_luot` LÀ ĐƯỜNG HỦY CHỈ LÀM MỘT TRONG BA VIỆC (L-06, 13/09).

           `dieu_phoi._dong()` — đường hủy đầy đủ của một lượt — làm ba việc:

               1. `huy_luot.danh_dau(ma_luot)`      chỉ khi CÓ mã
               2. `client.close()`                  luôn luôn
               3. `_bao_may_b_huy(..., ma_luot)`    chỉ khi CÓ mã

           Cửa job truyền mã nên đủ ba. Cửa đồng bộ **không** truyền, nên nó chỉ
           làm việc 2 — mà `httpx.Client.close()` **không cắt** một request đang
           bay ở luồng khác. Máy B cứ sinh chữ tới hết, luồng gọi cứ chờ, và
           `chay_canh_ngat` chờ luồng ấy trước khi ném `KhachNgat`.

           Đo được trên production: khách cắt kết nối rồi mà slot vẫn bị giữ
           **15,4 s / 17,2 s / 31,9 s** với `max_tokens` 900 / 1024 / 2000 — gần
           tỉ lệ thuận, tức đúng bằng thời gian sinh hết. Ngưỡng cổng M là 2 s.
           Và khách **vẫn bị tính tiền** cho phần token họ không nhận được.

        ⛔ Rỗng vẫn hợp lệ (bên gọi nội bộ không cần cắt), nhưng cửa nào phục vụ
           **khách** thì phải truyền — không thì tính năng hủy chết lặng lẽ, và
           nó chỉ lộ ra ở hoá đơn.
        """
        kwargs = {"timeout_s": timeout_s}
        if on_dispatch is not None:
            kwargs["on_dispatch"] = on_dispatch
        if on_rejected is not None:
            kwargs["on_rejected"] = on_rejected
        if ma_luot:
            kwargs["ma_luot"] = ma_luot
        if budget_suy_nghi is not None:
            kwargs["budget_suy_nghi"] = budget_suy_nghi
        return features.chay(db, params, **kwargs)

    def sync_thinking_budget(self, params):
        """Budget suy nghĩ máy chủ đặt cho một lượt cửa ĐỒNG BỘ (L-26), hoặc None.

        Gọi SAU khi `max_tokens` đã qua trần thời gian của cửa. Xem
        `ngan_sach.budget_suy_nghi_dong_bo`.
        """
        from apps.ltt_llm.ngan_sach import budget_suy_nghi_dong_bo
        return budget_suy_nghi_dong_bo(params.get("model"), params["max_tokens"],
                                       params.get("reasoning_effort"))

    def model_id(self, alias):
        return self.aliases()[alias]


EXECUTOR = _Executor()
