"""
test_270_tren_gpu — bắt được ca "model bò trên CPU". (H38, sau sự cố 23/08)

🔴 CA THẬT MÀ BỘ TEST NÀY DỰNG LẠI. Máy B tắt không sạch lúc 13:16 ngày 23/08,
   CUDA hỏng cả máy, `llama.cpp` **lặng lẽ rơi về CPU**. Trong hơn một giờ:

     /live                 -> {"ok": true}
     /health thuong_nguon  -> ma 200
     llama-swap /running   -> state "ready"
     moi luot goi          -> 200
     llama-server.exe      -> giu 23 GB RAM CHU
     GPU                   -> 1.153 MiB / 24.576, tai 3 %

   Mọi chốt sống/chết đều xanh. Chỉ VRAM nói thật. Sự cố chỉ lộ ra vì tình cờ có
   người đo một việc khác.

Bốn tính chất neo ở đây:

  1. Có model nạp + VRAM thấp ⇒ **đáng lo**.
  2. **"Không biết" KHÔNG phải "đáng lo".** Cảnh báo dựa trên phỏng đoán sẽ bị
     người trực học cách bỏ qua, và lúc đó kênh cảnh báo chết (QT-2).
  3. Không model nào nạp ⇒ VRAM thấp là **bình thường**.
  4. Chốt này **KHÔNG** được dùng để từ chối yêu cầu — model chạy CPU vẫn trả lời
     đúng, chỉ chậm.
"""
from __future__ import annotations

import pytest

from llm_gateway.tren_gpu import VRAM_TOI_THIEU_MB, kiem


def test_ca_that_23_08_bi_bat():
    """Đúng số đo hôm đó: model 'ready', GPU 1.153 MiB."""
    px = kiem(co_model_nap=True, doc_vram=lambda: 1153)
    assert px.tren_gpu is False
    assert px.dang_lo is True
    assert "CPU" in px.ly_do and "1153" in px.ly_do


def test_nap_dung_thi_khong_bao():
    """Cấu hình đích đo 22/08: ~20 GB lúc nghỉ, chạm 23,9 GB ở đỉnh."""
    for vram in (15_000, 19_973, 23_725):
        px = kiem(co_model_nap=True, doc_vram=lambda v=vram: v)
        assert px.tren_gpu is True and px.dang_lo is False, vram


def test_KHONG_DO_DUOC_thi_KHONG_bao():
    """⛔ 'Không biết' phải là `None`, không phải `False`.

    Biến nó thành cảnh báo là dạy người trực bỏ qua cảnh báo — cùng lý do
    `job_runner` không đếm 429 vào kênh im lặng."""
    px = kiem(co_model_nap=True, doc_vram=lambda: None)
    assert px.tren_gpu is None
    assert px.dang_lo is False


def test_khong_co_model_nao_nap_thi_VRAM_thap_la_BINH_THUONG():
    px = kiem(co_model_nap=False, doc_vram=lambda: 1153)
    assert px.tren_gpu is None and px.dang_lo is False


def test_nguong_nam_giua_nen_desktop_va_model_that():
    """Nền desktop đo được 1.515–1.612 MiB; model 27B Q4 nạp đúng là 15–24 GB.
    Ngưỡng phải nằm gọn giữa hai vùng, không sát mép nào."""
    assert 2_000 < VRAM_TOI_THIEU_MB < 14_000


@pytest.mark.parametrize("vram", [VRAM_TOI_THIEU_MB - 1, VRAM_TOI_THIEU_MB])
def test_bien_nguong(vram):
    px = kiem(co_model_nap=True, doc_vram=lambda: vram)
    assert px.dang_lo is (vram < VRAM_TOI_THIEU_MB)


# ── Cắm vào /health ─────────────────────────────────────────────────────────

def test_health_bao_khoi_gpu():
    from tests.test_250_llm_gateway import _client
    c, _ = _client()
    g = c.get("/health").json()["gpu"]
    assert set(g) >= {"tren_gpu", "vram_dung_mb", "co_model_nap", "dang_lo"}


def test_chot_nay_KHONG_tu_choi_yeu_cau():
    """⛔ Chốt QUAN SÁT, không phải chốt vào cửa. Model chạy CPU vẫn trả lời đúng,
    chỉ chậm; từ chối phục vụ sẽ biến sự cố hiệu năng thành sự cố ngừng dịch vụ."""
    from tests.test_250_llm_gateway import FakeUpstream, _client
    import llm_gateway.don_dep as dd

    goc = dd.doc_vram_dung_mb
    dd.doc_vram_dung_mb = lambda: 1153          # GPU trong nhu luc su co
    try:
        c, up = _client(up=FakeUpstream())
        r = c.post("/v1/chat/completions", json={
            "model": "qwen38-ops",
            "messages": [{"role": "user", "content": "hi"}]})
        assert r.status_code == 200, r.text
        assert up.goi, "da tu choi phuc vu chi vi model dang o CPU"
    finally:
        dd.doc_vram_dung_mb = goc


# ── Cảnh báo phía máy A ─────────────────────────────────────────────────────

def test_nguong_canh_bao_ban_NGAY_lan_dau():
    """Khác `cong_im_lang` (ngưỡng 2) vì ba lẽ: không có dương tính giả, không tự
    khỏi, và mỗi vòng chờ là tiền của khách."""
    from platform_core.public_api.ops_alerts import NGUONG
    assert NGUONG["ltt_llm:tren_cpu"] == 1
    assert NGUONG["ltt_llm:cong_im_lang"] == 2
