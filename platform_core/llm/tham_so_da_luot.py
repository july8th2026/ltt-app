"""tham_so_da_luot.py — tham số chính sách đa lượt của model nhà, MỘT chỗ. (multijob)

⭐ Đọc từ biến môi trường, có mặc định = giá trị khởi đầu của spec §12. Chủ dự án
   chốt 11/09: mở vận hành trước, phân tích sổ lượt (`llm_waiters`) sau rồi mới
   tối ưu — nên mọi ngưỡng ở đây phải **đổi được bằng cấu hình**, không bằng deploy.

⭐ PHƯƠNG ÁN C (bước 2, 17/09/2026) — hai loại số, hai nơi, không chồng nhau:

   * **số của MODEL** (slot, pool KV, ngưỡng whale, đệm ước, token đặt chỗ mỗi
     ảnh) — app khai trong `AdmissionModel` (`platform_core/registry.py`), nguồn
     chân lý là hồ sơ của app (`apps/ltt_llm/ngan_sach.HO_SO`). ⛔ KHÔNG ở đây.
   * **số THỜI GIAN / HÀNG** (trần chờ, backfill, lão hoá, whale nhường, nhịp,
     trần người chờ, số lần xếp lại) — env đọc ở `doc()`, mặc định **chỉ ở
     `doc()`**. Không chữ ký hàm nào khác được mang mặc định số của chúng
     (`luat_nhan.ThamSo`, `admission.xet_va_giu`, `phong_cho` đều bắt truyền).

   🔴 ĐÃ GỠ (17/09): `LTT_LLM_NGUONG_WHALE` (16.384 chung cho hai model — O-06),
      `LTT_LLM_DEM_DAT_TRUOC` (trùng nghĩa `LE` — O-08), `LTT_LLM_TOKEN_MOI_ANH`
      (O-11). Đặt chúng trong `app.env` nay KHÔNG có tác dụng gì.

⚠️ Dịch vụ Windows (nssm) nướng env lúc CÀI — đổi `app.env` rồi restart là KHÔNG đủ,
   phải `setup/nap_lai_env.ps1` (memory "nssm nướng ENV lúc CÀI").
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - chỉ cho kiểu
    from platform_core.llm.luat_nhan import ThamSo
    from platform_core.registry import AdmissionModel


def _so(ten: str, mac_dinh: float) -> float:
    try:
        return float((os.environ.get(ten) or "").strip() or mac_dinh)
    except ValueError:
        return float(mac_dinh)


@dataclass(frozen=True)
class ThamSoDaLuot:
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
    #: Nhịp tim SSE trong lúc chờ (dưới đồng hồ im lặng 100 s của Cloudflare).
    nhip_tim_cho_s: float
    #: Chờ quá bấy nhiêu giây thì được xếp lên trước (chống đói — như `jobs.FAIR_AGING`).
    lao_hoa_s: float
    #: Cửa stream: trần chờ RIÊNG của lượt whale (L-12b). Whale chạy nối tiếp,
    #: một lượt 150K trên 3.8 prefill ~230 s (`apps/ltt_llm/ngan_sach.py`
    #: `DUONG_PREFILL_TOK_S`) — 300 s chung sẽ đuổi whale thứ hai GIỮA SSE.
    #: ⛔ An toàn chỉ vì nhịp SSE `nhip_tim_cho_s` giữ Cloudflare (100 s) sống.
    cho_stream_whale_toi_da_s: float
    #: BACKFILL có chặn (L-12b, chủ dự án chốt 17/09): lượt đứng trước chưa vừa
    #: NGÂN SÁCH KV được nhường lượt sau VỪA ngân sách tối đa bấy nhiêu giây; quá
    #: thì nó CHẶN mọi lượt trẻ hơn tới khi đủ chỗ (chống bỏ đói lượt lớn).
    cho_backfill_toi_da_s: float
    #: Máy B trả 429 cho một lượt A ĐÃ nhận (phương án C bước 1, O-04): A nhả
    #: suất và XẾP LẠI dòng chờ (giữ `created_at`) tối đa bấy nhiêu lần, trong
    #: hạn chờ của cửa. Quá ⇒ kết cục bận cũ (`overloaded`/503), 0 khoản giữ.
    #: ⭐ Vì sao có: hai sổ slot/pool (A nhả ~0,05 s, B nhả khi luồng đóng) lệch
    #:    nhịp — một khe ngắn mà trước đây thành "429 SAU 200", khách mất lượt chờ.
    so_lan_xep_lai_toi_da: int
    #: Nghỉ bấy nhiêu giây trước khi xếp lại — cho máy B kịp nhả suất cũ, không
    #: thì A nhận lại ngay nửa giây sau và B 429 lần nữa vì cùng một khe.
    cho_xep_lai_s: float
    #: Phần cố định của hạn ước prefill (L-29) — hàng đợi/mạng A→B→engine trước
    #: token prompt đầu. Xem `han_prefill_s`.
    san_han_prefill_s: float

    def han_cho_stream(self, la_whale: bool) -> float:
        """Trần chờ cửa stream của MỘT lượt — một chỗ tính, mọi cửa đọc."""
        return self.cho_stream_whale_toi_da_s if la_whale else self.cho_stream_toi_da_s


class DatChoVuotPool(ValueError):
    """Một lượt đặt chỗ NHIỀU HƠN cả pool KV — không bao giờ nhận được.

    🔴 THAY phép KẸP IM LẶNG cũ (`min(pool, dat)`, phương án C bất biến 1). Kẹp
       che lỗi: đặt chỗ nhỏ hơn thứ lượt thật dùng ⇒ Σ đặt chỗ "vừa" pool trong
       khi engine tràn `-kvu` và giết MỌI slot (llama.cpp b10689). Và nó che luôn
       chính lỗi cấu hình gây ra nó (đệm ước lệch trần vào — O-08).
    ⭐ Cửa gọi dịch sang lỗi "quá dài" (trước 200, công khai 400 / job hỏng không thử lại):
       lượt này quá lớn với model ở cấu hình hiện tại, thử lại không bao giờ được.
    """

    def __init__(self, dat: int, pool: int):
        super().__init__(f"dat cho {dat} token vuot pool KV {pool}")
        self.dat = int(dat)
        self.pool = int(pool)


def luat_cho(suc: "AdmissionModel | None", *, lop: str, token_vao_uoc: int,
             xin_ra: int, token_anh: int = 0,
             token_prefill_moi: int | None = None) -> dict:
    """Tham số đa lượt cho `admission.acquire`/`xet_va_giu` — MỘT phép tính đặt chỗ.

    `suc` là `AdmissionModel` ĐÃ giải theo model (`tool.admission_cho(alias)`);
    `None` hoặc `token_pool <= 0` ⇒ `{}` ⇒ đúng hành vi cũ (tool không khai
    ngân sách KV — đếm slot).

        dat_cho = vào_ước + xin_ra + dem_uoc + token_anh
        whale   = token_prefill_moi ≥ nguong_whale   (nguong_whale > 0)

    ⭐ MỘT chỗ gắn cờ whale cho MỌI cửa (O-07): stream/ChatLTT truyền
       `token_prefill_moi` ước qua tiền tố (`uoc_moi`); đồng bộ, job, planner
       không có lịch sử tiền tố nên để `None` ⇒ dùng `token_vao_uoc` (ước CAO —
       hướng an toàn: nghi là whale thì chỉ chờ lâu hơn, không tràn).
    ⛔ NÉM `DatChoVuotPool` thay vì kẹp về pool — xem lớp ấy.
    ⛔ NÉM `ValueError` khi pool > 0 mà thiếu `dem_uoc`: bản khai ngân sách KV
       không có đệm ước là bản khai hỏng, không phải "đệm 0".
    """
    pool = int(getattr(suc, "token_pool", 0) or 0) if suc is not None else 0
    if pool <= 0:
        return {}
    dem = int(getattr(suc, "dem_uoc", 0) or 0)
    if dem <= 0:
        raise ValueError(f"tai nguyen {getattr(suc, 'resource', '')!r} khai pool {pool} "
                         f"ma khong khai dem_uoc")
    # ⭐ 28/09/2026: `token_anh` là **tổng đã ĐO** (`Σ anh_token.token_anh(w, h)`),
    #    không còn là `số ảnh × một hằng`. Hàm này không nhân gì nữa — nó chỉ cộng.
    #
    # 🔴 VÌ SAO ĐỔI: hằng phẳng 2.048 sai CẢ HAI CHIỀU (đo 14/14 ô, 28/09): thừa
    #    25× ở ảnh 320×240 (82 token thật) và **THIẾU 2×** ở 2048×2048 (4.098) —
    #    vốn đúng bằng cỡ tối đa client LTTCODE gửi. Thiếu là chiều
    #    `DatChoVuotPool` sinh ra để chặn, và chiều mà một lần tràn `-kvu` giết
    #    MỌI slot (llama.cpp b10689).
    #
    # ⛔ Không còn phép kiểm "nhận ảnh mà không khai hằng": người ĐO ảnh là
    #    `luong.do_anh`, và nó fail-closed ở đó (thiếu trần engine ⇒ không đo ⇒
    #    từ chối ảnh). Kiểm lại ở đây là kiểm hai lần một điều, ở chỗ không có
    #    thông tin để nói câu chẩn đoán đúng.
    dat = int(token_vao_uoc) + int(xin_ra) + dem + max(0, int(token_anh))
    if dat > pool:
        raise DatChoVuotPool(dat, pool)
    moi = int(token_vao_uoc) if token_prefill_moi is None else int(token_prefill_moi)
    nguong = int(getattr(suc, "nguong_whale", 0) or 0)
    return dict(lop=lop, token_pool=pool, token_dat_truoc=dat,
                token_prefill_moi=moi, la_whale=bool(nguong > 0 and moi >= nguong))


def han_prefill_s(token_moi: int, toc_prefill_tok_s: float, san_s: float) -> float:
    """Hạn ƯỚC một lượt còn đang prefill, tính từ lúc được nhận (L-29, Task 17).

        hạn = san_s + token_moi / toc_prefill_tok_s

    Dùng khi A KHÔNG có tín hiệu "byte đầu về" (cửa đồng bộ, job, planner) và làm
    lưới cho cửa stream (mất tín hiệu thì lượt không kẹt "đang prefill" mãi).
    `toc_prefill_tok_s` là tốc độ BẢO THỦ của hồ sơ model (`HO_SO[m]
    .toc_prefill_uoc_tok_s` — dưới điểm chậm nhất của đường cong đo) ⇒ hạn dài
    hơn thật: sai về phía whale chờ lâu hơn, không về phía hai prefill dài chồng.
    `toc ≤ 0` ⇒ vô hạn (không khai tốc độ ⇒ không có lưới thời gian).
    """
    if toc_prefill_tok_s <= 0:
        return float("inf")
    return float(san_s) + max(0, int(token_moi)) / float(toc_prefill_tok_s)


def tham_so_nhan(*, so_slot: int, pool: int, residency_mo: bool,
                 ts: ThamSoDaLuot | None = None,
                 mot_prefill_dai: bool = False) -> "ThamSo":
    """`luat_nhan.ThamSo` dựng từ MỘT `ThamSoDaLuot` — ánh xạ DUY NHẤT.

    🔴 O-09 (17/09): `admission.xet_va_giu` từng dựng `ThamSo` tay và quên
       `lao_hoa_s` ⇒ env `LTT_LLM_LAO_HOA_S` không có hiệu lực, luôn là mặc định
       300 nằm trong chữ ký `luat_nhan.ThamSo`. Nay `ThamSo` không còn mặc định
       số và mọi trường thời gian đi qua đây.
    """
    from platform_core.llm.luat_nhan import ThamSo

    ts = ts or doc()
    return ThamSo(so_slot=int(so_slot), pool=int(pool),
                  cho_whale_toi_da_s=ts.cho_whale_toi_da_s, lao_hoa_s=ts.lao_hoa_s,
                  cho_backfill_toi_da_s=ts.cho_backfill_toi_da_s,
                  residency_mo=bool(residency_mo),
                  mot_prefill_dai=bool(mot_prefill_dai))


def doc() -> ThamSoDaLuot:
    return ThamSoDaLuot(
        cho_whale_toi_da_s=_so("LTT_LLM_CHO_WHALE_S", 30.0),
        cho_stream_toi_da_s=_so("LTT_LLM_CHO_STREAM_S", 300.0),
        cho_dong_bo_toi_da_s=_so("LTT_LLM_CHO_DONG_BO_S", 60.0),
        so_nguoi_cho_toi_da=int(_so("LTT_LLM_SO_NGUOI_CHO", 32)),
        so_ca_voi_cho_toi_da=max(1, int(_so("LTT_LLM_SO_CA_VOI_CHO", 2))),
        nhip_tim_cho_s=_so("LTT_LLM_NHIP_TIM_CHO_S", 15.0),
        lao_hoa_s=_so("LTT_LLM_LAO_HOA_S", 300.0),
        cho_stream_whale_toi_da_s=_so("LTT_LLM_CHO_STREAM_WHALE_S", 900.0),
        cho_backfill_toi_da_s=_so("LTT_LLM_CHO_BACKFILL_S", 120.0),
        so_lan_xep_lai_toi_da=max(0, int(_so("LTT_LLM_SO_LAN_XEP_LAI", 3))),
        cho_xep_lai_s=max(0.0, _so("LTT_LLM_CHO_XEP_LAI_S", 1.0)),
        san_han_prefill_s=max(0.0, _so("LTT_LLM_SAN_HAN_PREFILL_S", 5.0)),
    )
