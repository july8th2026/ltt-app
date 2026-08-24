"""
test_257_giam_sat_vlm — cảnh báo khi cổng VLM máy B im lặng. (H38, V5)

⭐ VÌ SAO HẠNG MỤC NÀY TỒN TẠI: rà soát 22/08 chấm **quan sát được 4/10** — yếu
   nhất trong mười hạng mục. Nền tảng có thể **xanh hoàn toàn** trong khi model
   ngôn ngữ nhà không phục vụ được ai, vì nó là một tiến trình khác trên một máy
   khác. Trước cái này, cách duy nhất biết máy B chết là có người thử rồi thấy hỏng.

Ba tính chất neo ở đây:

  1. **Chưa khai địa chỉ ⇒ không đoán, không báo.** Một cài đặt dev không có máy B.
  2. 🔴 **BẬN ≠ IM LẶNG.** 429 là trạng thái bình thường của một máy chia GPU với
     việc ảnh và video. Đếm nó vào cảnh báo thì người trực bị đánh thức mỗi tối
     dự án video chạy — và sẽ ngừng đọc cảnh báo. Đó là cách làm hỏng một kênh
     cảnh báo cho tốt.
  3. **Thăm `/live`, không `/health`.** Phép thăm dò sống/chết không nên phải
     mang bí mật, và không nên đọc được trạng thái vận hành.
"""
from __future__ import annotations

import sys
import types

import pytest


def _dat_httpx(monkeypatch, *, ma=None, nem=None):
    """Thay `httpx` bằng bản giả và ghi lại URL đã gọi."""
    da_goi = {}

    class R:
        def __init__(self, status_code):
            self.status_code = status_code

    def get(url, timeout=None):
        da_goi["url"] = url
        da_goi["timeout"] = timeout
        if nem is not None:
            raise nem
        return R(ma)

    monkeypatch.setitem(sys.modules, "httpx", types.SimpleNamespace(get=get))
    return da_goi


def _dat_metrics(monkeypatch):
    """Đếm các lần `metrics.increment` được gọi.

    ⚠️ VÁ **HÀM**, KHÔNG VÁ `sys.modules`. Bản đầu tôi thay cả module trong
       `sys.modules`, và nó chỉ ăn khi chạy riêng lẻ: `job_runner` viết
       `from platform_core.public_api import metrics`, mà dạng đó lấy **thuộc
       tính `metrics` của gói cha** khi gói cha đã được nạp. Chỉ cần một test
       nào đó chạy trước có `import platform_core.public_api.metrics` là thuộc
       tính thật đã nằm sẵn trên gói, bản giả bị bỏ qua, và 19 test đỏ trong
       một lượt chạy đầy đủ — trong khi chạy lẻ thì xanh hết.

       Test chỉ xanh lúc cô lập thì chưa phải bằng chứng.
    """
    from platform_core.public_api import metrics
    dem = []
    monkeypatch.setattr(metrics, "increment", lambda ten: dem.append(ten))
    return dem


# ── 1. Chưa khai địa chỉ thì im lặng hoàn toàn ──────────────────────────────

def test_chua_khai_dia_chi_thi_khong_tham_va_khong_bao(monkeypatch):
    from platform_core import job_runner
    monkeypatch.delenv("LTT_LLM_BASE_URL", raising=False)
    da_goi = _dat_httpx(monkeypatch, ma=200)
    dem = _dat_metrics(monkeypatch)
    assert job_runner._tham_cong_vlm() is True
    assert da_goi == {}, "chua khai thi dung goi di dau ca"
    assert dem == []


# ── 2. Cổng sống ────────────────────────────────────────────────────────────

def test_cong_song_thi_khong_dem_gi(monkeypatch):
    from platform_core import job_runner
    monkeypatch.setenv("LTT_LLM_BASE_URL", "http://192.168.2.66:8299")
    da_goi = _dat_httpx(monkeypatch, ma=200)
    dem = _dat_metrics(monkeypatch)
    assert job_runner._tham_cong_vlm() is True
    assert da_goi["url"] == "http://192.168.2.66:8299/live"
    assert dem == []


def test_tham_do_LIVE_chu_khong_phai_HEALTH(monkeypatch):
    """`/health` doi bearer va tra danh sach model + trang thai trong tai.
    Mot phep tham do song/chet khong nen mang bi mat."""
    from platform_core import job_runner
    monkeypatch.setenv("LTT_LLM_BASE_URL", "http://may-b:8299/")
    da_goi = _dat_httpx(monkeypatch, ma=200)
    _dat_metrics(monkeypatch)
    job_runner._tham_cong_vlm()
    assert da_goi["url"].endswith("/live")
    assert "/health" not in da_goi["url"]


# ── 3. 🔴 BẬN ≠ IM LẶNG ─────────────────────────────────────────────────────

def test_429_KHONG_duoc_dem_la_im_lang(monkeypatch):
    """🔴 429 = may B dang ban voi viec anh/video. Do la BINH THUONG.

    Dem no vao canh bao thi nguoi truc bi danh thuc moi toi du an video chay,
    va se ngung doc canh bao. Do la cach lam hong mot kenh canh bao cho tot.

    (`/live` khong bao gio tra 429 — no khong di qua trong tai. Nhung neu mot ban
    sau nay doi hanh vi do, test nay se do va bat duoc.)"""
    from platform_core import job_runner
    monkeypatch.setenv("LTT_LLM_BASE_URL", "http://may-b:8299")
    _dat_httpx(monkeypatch, ma=429)
    dem = _dat_metrics(monkeypatch)
    job_runner._tham_cong_vlm()
    assert "ltt_llm:cong_im_lang" not in dem, \
        "ban khong phai im lang — xem QT-2"


# ── 4. Cổng chết thì phải đếm ───────────────────────────────────────────────

def test_khong_ket_noi_duoc_thi_dem(monkeypatch):
    from platform_core import job_runner
    monkeypatch.setenv("LTT_LLM_BASE_URL", "http://may-b:8299")
    _dat_httpx(monkeypatch, nem=OSError("connection refused"))
    dem = _dat_metrics(monkeypatch)
    assert job_runner._tham_cong_vlm() is False
    assert dem == ["ltt_llm:cong_im_lang"]


@pytest.mark.parametrize("ma", [500, 502, 503, 404])
def test_ma_loi_thi_dem(monkeypatch, ma):
    from platform_core import job_runner
    monkeypatch.setenv("LTT_LLM_BASE_URL", "http://may-b:8299")
    _dat_httpx(monkeypatch, ma=ma)
    dem = _dat_metrics(monkeypatch)
    assert job_runner._tham_cong_vlm() is False
    assert dem == ["ltt_llm:cong_im_lang"]


# ── 5. Ngưỡng cảnh báo ──────────────────────────────────────────────────────

def test_nguong_la_2_khong_phai_1():
    """Mot lan chop mang khong nen dung nguoi truc day; hai vong bao tri lien
    tiep im lang la that. Cung ly do voi `nexus:relay_im_lang`."""
    from platform_core.public_api.ops_alerts import NGUONG
    assert NGUONG["ltt_llm:cong_im_lang"] == 2


def test_vong_bao_tri_co_goi_pheps_tham():
    """Neu ai do go loi goi khoi `_mot_luot_bao_tri` thi canh bao im lang mai
    mai — va khong ai biet, vi dau hieu duy nhat la SU VANG MAT cua canh bao."""
    import inspect
    from platform_core import job_runner
    nguon = inspect.getsource(job_runner)
    assert "_tham_cong_vlm()" in nguon
    # Phai nam trong cung ham voi `_tham_relay_nexus` — do la vong bao tri sau lease.
    i_relay = nguon.index("_tham_relay_nexus()")
    i_vlm = nguon.index("_tham_cong_vlm()")
    assert abs(i_vlm - i_relay) < 200, "phai o cung vong bao tri voi relay Nexus"
