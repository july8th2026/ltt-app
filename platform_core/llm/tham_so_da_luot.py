"""tham_so_da_luot.py — tham số chính sách đa lượt của model nhà, MỘT chỗ. (multijob)

⭐ Đọc từ biến môi trường, có mặc định = giá trị khởi đầu của spec §12. Chủ dự án
   chốt 11/09: mở vận hành trước, phân tích sổ lượt (`llm_waiters`) sau rồi mới
   tối ưu — nên mọi ngưỡng ở đây phải **đổi được bằng cấu hình**, không bằng deploy.

⛔ Số slot và pool KV KHÔNG ở đây: chúng thuộc từng tool (`ToolSpec.admission_slots`,
   `admission_token_pool`) và nguồn chân lý là `apps/ltt_llm/ngan_sach.py`.

⚠️ Dịch vụ Windows (nssm) nướng env lúc CÀI — đổi `app.env` rồi restart là KHÔNG đủ,
   phải `setup/nap_lai_env.ps1` (memory "nssm nướng ENV lúc CÀI").
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _so(ten: str, mac_dinh: float) -> float:
    try:
        return float((os.environ.get(ten) or "").strip() or mac_dinh)
    except ValueError:
        return float(mac_dinh)


@dataclass(frozen=True)
class ThamSoDaLuot:
    #: Token cần prefill MỚI từ mức này trở lên là "whale" (D-05). 16.384 ⇒ 7,6 %
    #: lượt thật 22/08–11/09 (`docs/multijob/00_BASELINE.md` §3).
    nguong_whale: int
    #: Whale nhường lượt tương tác đang chạy tối đa bấy nhiêu giây, rồi thành "chặn".
    cho_whale_toi_da_s: float
    #: Cửa stream chờ trong SSE tối đa (D-06).
    cho_stream_toi_da_s: float
    #: Cửa đồng bộ chờ trước header tối đa (TD-7; còn bị kẹp bởi ngân sách thời gian).
    cho_dong_bo_toi_da_s: float
    #: Trần số người chờ (cửa tương tác) — chạm thì 429 TRƯỚC 200.
    so_nguoi_cho_toi_da: int
    #: Trần số WHALE còn sống trong phòng chờ của MỘT tài nguyên (L-12b, 17/09/2026).
    #:
    #: 🔴 THAY `token_prefill_cho_toi_da` (57.000, env `LTT_LLM_TOKEN_PREFILL_CHO`,
    #:    ĐÃ GỠ). Trần ấy cộng token prefill MỚI của NGƯỜI CHỜ rồi 429 trước 200 —
    #:    chồng lên luật ngân sách thật (`luat_nhan` luật 2: Σ token đặt chỗ của
    #:    lượt ĐANG CHẠY + lượt này ≤ pool KV). Hai luật cho một câu hỏi, và luật
    #:    thừa đuổi oan: một whale 68K đang chờ làm MỌI lượt mới 429 (68K + x >
    #:    57K), lượt >57K thứ hai 429 dù model nhận được 171.458.
    #: ⭐ Whale chạy NỐI TIẾP (≤1 mỗi tài nguyên) nên hàng whale được chặn bằng SỐ
    #:    NGƯỜI, không bằng token: 2 ≈ hai lượt 150K (~4,5 phút mỗi lượt) nằm trong
    #:    `cho_stream_whale_toi_da_s`. Quá ⇒ 429 TRƯỚC 200, khách thử lại được.
    so_ca_voi_cho_toi_da: int
    #: Đệm đặt chỗ mỗi lượt (≈ `n_batch` của llama.cpp, như patch 0011 của lab).
    dem_dat_truoc: int
    #: Token đặt chỗ thêm cho mỗi ảnh (M-2: ảnh 1024×768 ≈ 800 token prompt).
    token_moi_anh: int
    #: Nhịp tim SSE trong lúc chờ (dưới đồng hồ im lặng 100 s của Cloudflare).
    nhip_tim_cho_s: float
    #: Chờ quá bấy nhiêu giây thì được xếp lên trước (chống đói — như `jobs.FAIR_AGING`).
    lao_hoa_s: float
    #: Cửa stream: trần chờ RIÊNG của lượt whale (L-12b). Whale chạy nối tiếp,
    #: một lượt 150K trên 3.8 prefill ~230 s (`apps/ltt_llm/ngan_sach.py`
    #: `DUONG_PREFILL_TOK_S`) — 300 s chung sẽ đuổi whale thứ hai GIỮA SSE.
    #: ⛔ An toàn chỉ vì nhịp SSE `nhip_tim_cho_s` giữ Cloudflare (100 s) sống.
    cho_stream_whale_toi_da_s: float = 900.0
    #: BACKFILL có chặn (L-12b, chủ dự án chốt 17/09): lượt đứng trước chưa vừa
    #: NGÂN SÁCH KV được nhường lượt sau VỪA ngân sách tối đa bấy nhiêu giây; quá
    #: thì nó CHẶN mọi lượt trẻ hơn tới khi đủ chỗ (chống bỏ đói lượt lớn).
    cho_backfill_toi_da_s: float = 120.0

    def han_cho_stream(self, la_whale: bool) -> float:
        """Trần chờ cửa stream của MỘT lượt — một chỗ tính, mọi cửa đọc."""
        return self.cho_stream_whale_toi_da_s if la_whale else self.cho_stream_toi_da_s


def luat_cho(pool: int, *, lop: str, token_vao_uoc: int, xin_ra: int,
             so_anh: int = 0, token_prefill_moi: int = 0,
             la_whale: bool = False) -> dict:
    """Tham số đa lượt cho `admission.acquire`/`xet_va_giu` — MỘT phép tính đặt chỗ.

    `pool <= 0` ⇒ `{}` ⇒ đúng hành vi cũ (tool không khai ngân sách KV).

    ⛔ Kẹp về `pool`: một lượt dùng trọn cửa sổ + đệm + ảnh vượt pool và sẽ KHÔNG
       BAO GIỜ được nhận, trong khi engine vẫn phục vụ được nó khi chạy một mình.
    ⭐ Năm chỗ gọi (stream, ChatLTT, đồng bộ ×2, job, planner) cùng đi qua đây —
       năm bản sao của phép tính này là năm chỗ lệch nhau (memory "hai chỗ khai
       cùng một điều").
    """
    if int(pool or 0) <= 0:
        return {}
    ts = doc()
    dat = int(token_vao_uoc) + int(xin_ra) + ts.dem_dat_truoc + int(so_anh) * ts.token_moi_anh
    return dict(lop=lop, token_pool=int(pool), token_dat_truoc=min(int(pool), dat),
                token_prefill_moi=int(token_prefill_moi), la_whale=bool(la_whale))


def doc() -> ThamSoDaLuot:
    return ThamSoDaLuot(
        nguong_whale=int(_so("LTT_LLM_NGUONG_WHALE", 16_384)),
        cho_whale_toi_da_s=_so("LTT_LLM_CHO_WHALE_S", 30.0),
        cho_stream_toi_da_s=_so("LTT_LLM_CHO_STREAM_S", 300.0),
        cho_dong_bo_toi_da_s=_so("LTT_LLM_CHO_DONG_BO_S", 60.0),
        so_nguoi_cho_toi_da=int(_so("LTT_LLM_SO_NGUOI_CHO", 32)),
        so_ca_voi_cho_toi_da=max(1, int(_so("LTT_LLM_SO_CA_VOI_CHO", 2))),
        dem_dat_truoc=int(_so("LTT_LLM_DEM_DAT_TRUOC", 2_048)),
        # Khớp phép giữ chỗ của máy B (`llm_gateway.ngan_sach.TOKEN_MOI_ANH`).
        # Máy A thấp hơn máy B làm một lượt có ảnh qua hàng chờ rồi bị B từ chối.
        token_moi_anh=int(_so("LTT_LLM_TOKEN_MOI_ANH", 2_048)),
        nhip_tim_cho_s=_so("LTT_LLM_NHIP_TIM_CHO_S", 15.0),
        lao_hoa_s=_so("LTT_LLM_LAO_HOA_S", 300.0),
        cho_stream_whale_toi_da_s=_so("LTT_LLM_CHO_STREAM_WHALE_S", 900.0),
        cho_backfill_toi_da_s=_so("LTT_LLM_CHO_BACKFILL_S", 120.0),
    )
