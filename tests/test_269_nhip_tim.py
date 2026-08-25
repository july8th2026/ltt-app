"""
test_269_nhip_tim — nhịp tim SSE giữ cho Codex và Claude Code không tự ngắt. (H38)

🔴 VÌ SAO BỘ TEST NÀY TỒN TẠI. Cả hai CLI đặt đồng hồ trên **khoảng lặng của
   luồng**: Codex `stream_idle_timeout_ms` mặc định 300.000 ms, Claude Code đếm
   từng byte và bỏ luồng sau 300 giây im lặng. `llama-server` **không phát gì
   trong lúc prefill**, và prompt hệ thống của Codex đo được là **~21.936
   token**. Ngày 23/08 tôi thấy tận mắt: Codex gọi 14:18:25, im lặng, thử lại
   14:23:27 — cách nhau đúng 300 giây.

Bốn tính chất neo ở đây, và cái thứ hai là cái đắt nhất nếu sai:

  1. Lặng thì có nhịp; có dữ liệu thì không chèn gì thừa.
  2. **Thứ tự và nội dung của luồng gốc không đổi một byte.** Cổng này là đường
     ống, không phải bộ dịch.
  3. Luồng gốc nổ giữa chừng thì lỗi phải **nổi lên đúng chỗ**, không bị nuốt.
  4. Khách ngắt thì luồng gốc phải được **đóng**, nếu không GPU sinh chữ tiếp
     cho một câu trả lời không ai đọc.
"""
from __future__ import annotations

import threading
import time

import pytest

from llm_gateway.nhip_tim import NHIP_MAC_DINH, boc_nhip_tim


class LuongTay:
    """Luồng do test điều khiển: chỉ nhả khối khi được bảo."""

    def __init__(self):
        self._hang = []
        self._co = threading.Condition()
        self._het = False
        self.da_dong = False

    def day(self, khoi):
        with self._co:
            self._hang.append(khoi)
            self._co.notify_all()

    def ket_thuc(self, loi=None):
        with self._co:
            self._het = loi or True
            self._co.notify_all()

    def __iter__(self):
        return self

    def __next__(self):
        with self._co:
            while not self._hang and self._het is False:
                self._co.wait(5)
            if self._hang:
                return self._hang.pop(0)
            if isinstance(self._het, BaseException):
                raise self._het
            raise StopIteration

    def close(self):
        self.da_dong = True
        self.ket_thuc()


# ── 1. Lặng thì có nhịp ─────────────────────────────────────────────────────

def test_lang_thi_co_nhip():
    """Đây là toàn bộ lý do file này tồn tại."""
    src = LuongTay()
    g = boc_nhip_tim(src, moi_giay=0.05)
    assert next(g) == NHIP_MAC_DINH
    assert next(g) == NHIP_MAC_DINH
    src.day(b"data: x\n\n")
    assert next(g) == b"data: x\n\n"
    src.ket_thuc()
    with pytest.raises(StopIteration):
        next(g)


def test_nhip_la_CHU_THICH_sse_khong_phai_su_kien():
    """⭐ Chú thích được đặc tả SSE bảo đảm là bỏ qua, nên an toàn cho **cả ba**
    giao thức cổng này phục vụ. Một sự kiện `ping` chỉ hợp lệ ở Anthropic, và
    gửi nó TRƯỚC `message_start` là đặt cược vào việc client dễ tính."""
    assert NHIP_MAC_DINH.startswith(b":")
    assert b"event:" not in NHIP_MAC_DINH
    assert NHIP_MAC_DINH.endswith(b"\n\n"), "phai la mot 'su kien' tron ven"


def test_co_du_lieu_thi_KHONG_chen_gi():
    src = LuongTay()
    for i in range(5):
        src.day(b"data: %d\n\n" % i)
    src.ket_thuc()
    ra = list(boc_nhip_tim(src, moi_giay=30.0))
    assert ra == [b"data: %d\n\n" % i for i in range(5)]


# ── 2. Không đổi một byte của luồng gốc ─────────────────────────────────────

def test_giu_nguyen_thu_tu_va_noi_dung():
    """⛔ Cổng là đường ống, không phải bộ dịch. Bỏ nhịp ra thì phải còn y hệt."""
    khoi = [b"event: message_start\n\n", b"data: {\"a\":1}\n\n", b"x" * 5000]
    src = LuongTay()
    for k in khoi:
        src.day(k)
    src.ket_thuc()
    ra = [k for k in boc_nhip_tim(src, moi_giay=30.0) if k != NHIP_MAC_DINH]
    assert ra == khoi


def test_tat_bang_0_thi_tra_dung_luong_goc():
    """⛔ `moi_giay <= 0` phải là TẮT HẲN, không phải 'nhịp mỗi 0 giây' — cái sau
    là một vòng lặp bận đốt CPU và làm ngập luồng."""
    src = iter([b"a", b"b"])
    assert boc_nhip_tim(src, moi_giay=0) is src


# ── 3. Lỗi phải nổi lên, không bị nuốt ──────────────────────────────────────

def test_luong_goc_no_thi_loi_NOI_LEN_dung_thu_tu():
    """Nuốt lỗi ở đây thì một luồng vỡ giữa chừng trông y hệt một luồng kết thúc
    bình thường, và khách nhận nửa câu trả lời mà tưởng là đủ."""
    src = LuongTay()
    src.day(b"data: mot nua\n\n")
    src.ket_thuc(ConnectionError("thuong nguon dut"))
    g = boc_nhip_tim(src, moi_giay=30.0)
    assert next(g) == b"data: mot nua\n\n"
    with pytest.raises(ConnectionError):
        next(g)


# ── 4. Khách ngắt thì đóng luồng gốc ────────────────────────────────────────

def test_khach_ngat_thi_DONG_luong_goc():
    """Không đóng thì `llama-server` chạy tiếp tới hết `max_tokens` trên một câu
    trả lời không ai còn đọc, và GPU bị giữ vô ích."""
    src = LuongTay()
    src.day(b"data: dau\n\n")
    g = boc_nhip_tim(src, moi_giay=30.0)
    next(g)
    assert not src.da_dong
    g.close()
    assert src.da_dong


# ── 5. Bài toán thật: prefill lâu hơn trần của CLI ──────────────────────────

def test_prefill_dai_van_giu_duoc_luong():
    """Mô phỏng đúng ca đã làm Codex tự ngắt: im lặng dài trước token đầu tiên.

    Trần thật là 300 giây; ở đây rút tỉ lệ xuống cho test chạy nhanh, nhưng câu
    hỏi giữ nguyên: trong khoảng lặng đó, cổng có phát byte nào không?"""
    src = LuongTay()
    g = boc_nhip_tim(src, moi_giay=0.05)

    def prefill():
        time.sleep(0.4)                    # "prefill" 22k token
        src.day(b"event: content_block_delta\n\n")
        src.ket_thuc()

    threading.Thread(target=prefill, daemon=True).start()
    ra = list(g)
    nhip = [k for k in ra if k == NHIP_MAC_DINH]
    assert len(nhip) >= 3, "khoang lang khong duoc lap day -> CLI se tu ngat"
    assert ra[-1] == b"event: content_block_delta\n\n"


# ── 6. Cắm vào cổng thật ────────────────────────────────────────────────────

def test_cong_bat_nhip_tim_mac_dinh():
    from llm_gateway.config import Config
    import os
    cu = os.environ.pop("LTT_LLM_NHIP_TIM_S", None)
    try:
        assert Config.from_env().nhip_tim_giay == 15.0, \
            "mac dinh phai BAT: 15s la mot phan hai muoi tran 300s cua ca hai CLI"
    finally:
        if cu is not None:
            os.environ["LTT_LLM_NHIP_TIM_S"] = cu


def test_health_bao_nhip_tim():
    from tests.test_250_llm_gateway import _cfg, _client
    c, _ = _client(cfg=_cfg(nhip_tim_giay=15.0))
    assert c.get("/health").json()["nhip_tim_giay"] == 15.0
