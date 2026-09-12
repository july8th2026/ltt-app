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

    def run(self, db, params, *, timeout_s, on_dispatch=None, on_rejected=None):
        kwargs = {"timeout_s": timeout_s}
        if on_dispatch is not None:
            kwargs["on_dispatch"] = on_dispatch
        if on_rejected is not None:
            kwargs["on_rejected"] = on_rejected
        return features.chay(db, params, **kwargs)

    def model_id(self, alias):
        return self.aliases()[alias]


EXECUTOR = _Executor()
