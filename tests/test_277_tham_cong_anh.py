"""
test_277 — thăm dò cổng ẢNH trên máy B: sống/chết, và GPU-hay-CPU. (H37/L2, L3)

Không mạng, không GPU, không CSDL thật.

🔴 VÌ SAO. Trước H37/L2, máy A **không có phép thăm dò nào** cho cổng render.
   Cổng ảnh chết lúc 2 giờ sáng thì đường duy nhất để biết là có khách thử vẽ
   rồi thấy hỏng. Cổng VLM đã có `_tham_cong_vlm` + `_tham_gpu_may_b` từ H38;
   phía ảnh không có gì cả, dù nó chạy trên cùng cái máy đó.

⛔ VÀ HAI CHỐT KHÔNG ĐƯỢC GỘP. Máy B chạy hai dịch vụ riêng (:8199 và :8299),
   khởi động riêng, chết riêng. Gộp là tạo ra điểm mù đúng bằng nửa số dịch vụ.
"""
from __future__ import annotations

import pytest


# ── Chốt GPU/CPU thuần, không mạng ──────────────────────────────────────────

def test_khong_co_job_thi_KHONG_dang_lo():
    """Cổng vừa khởi động, chưa vẽ gì, VRAM thấp — đó là BÌNH THƯỜNG.

    ComfyUI chỉ giữ model thường trú **sau** lượt vẽ đầu tiên. Báo động ở đây là
    dương tính giả mỗi lần khởi động lại dịch vụ.
    """
    from render_gateway import tren_gpu
    px = tren_gpu.kiem(giay_dang_chay=None, doc_vram=lambda: 800)
    assert px.dang_lo is False and px.tren_gpu is None


def test_job_moi_chay_thi_CHUA_ket_luan():
    """Job vừa nộp còn xếp hàng / còn nạp trọng số. Chưa loại trừ được."""
    from render_gateway import tren_gpu
    px = tren_gpu.kiem(giay_dang_chay=5.0, doc_vram=lambda: 800)
    assert px.dang_lo is False and px.tren_gpu is None


def test_khong_doc_duoc_vram_thi_KHONG_doan():
    """"Không biết" không phải "đáng lo" — cảnh báo phỏng đoán làm chết kênh."""
    from render_gateway import tren_gpu
    px = tren_gpu.kiem(giay_dang_chay=300.0, doc_vram=lambda: None)
    assert px.dang_lo is False and px.tren_gpu is None


def test_dang_ve_lau_ma_vram_thap_thi_DANG_LO():
    """🔴 Chốt chính. Đang vẽ 5 phút mà card gần trống ⇒ đã rơi về CPU."""
    from render_gateway import tren_gpu
    px = tren_gpu.kiem(giay_dang_chay=300.0, doc_vram=lambda: 1_600)
    assert px.dang_lo is True and px.tren_gpu is False
    assert "CPU" in px.ly_do


def test_dang_ve_va_vram_cao_thi_yen_tam():
    from render_gateway import tren_gpu
    px = tren_gpu.kiem(giay_dang_chay=300.0, doc_vram=lambda: 20_000)
    assert px.dang_lo is False and px.tren_gpu is True


def test_nguong_du_cao_de_khong_nham_voi_nen_desktop():
    """Nền desktop máy B đo được 1.515–1.612 MiB. Ngưỡng phải ở trên hẳn."""
    from render_gateway import tren_gpu
    assert tren_gpu.VRAM_TOI_THIEU_MB > 3_000


def test_lau_toi_thieu_ngan_hon_mot_luot_ve():
    """Bắt được ngay trong lượt đầu, không phải chờ lượt thứ hai.

    Một lượt t2i đo thật là 96 giây; ngưỡng phải nhỏ hơn con số đó.
    """
    from render_gateway import tren_gpu
    assert tren_gpu.CHAY_LAU_TOI_THIEU_S < 96


# ── JobStore biết job đang chạy bao lâu ─────────────────────────────────────

def test_store_do_tuoi_job_cu_nhat():
    """Lấy job CŨ NHẤT, không phải mới nhất.

    Lấy mới nhất thì một luồng việc đều đặn sẽ giữ chốt mãi không chín.
    """
    from render_gateway import jobs as J

    dong_ho = {"t": 1_000.0}
    store = J.JobStore(now=lambda: dong_ho["t"])
    assert store.chay_lau_nhat_s() is None

    store.create_or_get("j1", "p1")
    dong_ho["t"] = 1_100.0
    store.create_or_get("j2", "p2")
    assert store.chay_lau_nhat_s() == pytest.approx(100.0)

    dong_ho["t"] = 1_200.0
    store.set_status("j1", J.COMPLETED, image_keys=["k"])
    # j1 xong rồi ⇒ chỉ còn j2 (nộp lúc 1.100)
    assert store.chay_lau_nhat_s() == pytest.approx(100.0)

    store.set_status("j2", J.COMPLETED, image_keys=["k"])
    assert store.chay_lau_nhat_s() is None


# ── Cổng: /live không cần khoá, /health có chốt GPU ─────────────────────────

def _cong(monkeypatch, tmp_path, *, vram=20_000):
    from render_gateway.api import create_app
    from render_gateway.config import Config
    from fastapi.testclient import TestClient

    class _Comfy:
        def alive(self):
            return True

        def queue_prompt_ids(self):
            return ([], [])

        def system_stats(self):
            return {"devices": [{"vram_total": 25_769_803_776,
                                 "vram_free": 25_769_803_776}]}

    cfg = Config(comfy_url="http://x", comfy_input_dir=tmp_path, host="127.0.0.1",
                 port=8199, token="bi-mat", max_concurrent=1, job_timeout_s=600.0,
                 ram_trong_toi_thieu_gb=48.0, work_dir=tmp_path)
    # Tiêm nguồn VRAM giả: mặc định gọi `nvidia-smi` THẬT, và máy chạy test có
    # GPU — không tiêm thì test phụ thuộc vào việc máy đang bận hay rảnh.
    app = create_app(cfg, _Comfy(), doc_vram_mb=lambda: vram,
                     dem_python_gpu=lambda: 0)
    return TestClient(app)


def test_live_KHONG_can_khoa(monkeypatch, tmp_path):
    """Phép thăm dò sống/chết không nên phải mang theo bí mật."""
    c = _cong(monkeypatch, tmp_path)
    r = c.get("/live")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_live_KHONG_lo_trang_thai_van_hanh(monkeypatch, tmp_path):
    """Nó cố ý chỉ nói `{ok, version}` — không VRAM, không hàng đợi, không model."""
    c = _cong(monkeypatch, tmp_path)
    goi = c.get("/live").json()
    assert set(goi) == {"ok", "version"}


def test_health_VAN_can_khoa(monkeypatch, tmp_path):
    c = _cong(monkeypatch, tmp_path)
    assert c.get("/health").status_code == 401


def test_health_co_chot_gpu(monkeypatch, tmp_path):
    c = _cong(monkeypatch, tmp_path)
    goi = c.get("/health", headers={"Authorization": "Bearer bi-mat"}).json()
    assert "gpu" in goi and "dang_lo" in goi["gpu"]


# ── Vòng bảo trì phía máy A ─────────────────────────────────────────────────

def test_chua_khai_dia_chi_thi_KHONG_bao(monkeypatch):
    """Cài đặt dev không có máy B. Đoán mò rồi báo động là làm hỏng kênh."""
    from platform_core import job_runner
    monkeypatch.delenv("LTT_RENDER_BASE_URL", raising=False)
    assert job_runner._tham_cong_render() is True


def test_cong_im_lang_thi_DEM(monkeypatch):
    from platform_core import job_runner
    monkeypatch.setenv("LTT_RENDER_BASE_URL", "http://may-b:8199")

    dem = []
    import httpx
    monkeypatch.setattr(httpx, "get",
                        lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("x")))
    from platform_core.public_api import metrics
    monkeypatch.setattr(metrics, "increment", lambda ten, **k: dem.append(ten))

    assert job_runner._tham_cong_render() is False
    assert "ltt_image:cong_im_lang" in dem


def test_429_KHONG_dem(monkeypatch):
    """🔴 D-005. Cổng render trả 429 mỗi tối dự án video chiếm card.

    Đếm nó vào cảnh báo thì người trực bị đánh thức hằng đêm, và sẽ ngừng đọc
    cảnh báo. Đó là cách làm hỏng một kênh cảnh báo cho tốt.
    """
    from platform_core import job_runner
    monkeypatch.setenv("LTT_RENDER_BASE_URL", "http://may-b:8199")

    dem = []
    import httpx

    class _R:
        status_code = 429

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _R())
    from platform_core.public_api import metrics
    monkeypatch.setattr(metrics, "increment", lambda ten, **k: dem.append(ten))

    assert job_runner._tham_cong_render() is True
    assert dem == []


def test_hai_chot_la_HAI_metric_rieng():
    """Gộp là tạo điểm mù đúng bằng nửa số dịch vụ trên máy B."""
    from platform_core.public_api.ops_alerts import NGUONG
    for ten in ("ltt_image:cong_im_lang", "ltt_image:tren_cpu",
                "ltt_llm:cong_im_lang", "ltt_llm:tren_cpu"):
        assert ten in NGUONG, f"thieu nguong {ten}"
    # Trên CPU thì bắn NGAY: không có dương tính giả, và nó không tự khỏi.
    assert NGUONG["ltt_image:tren_cpu"] == 1
    # Im lặng thì chờ hai vòng: một cú chớp mạng không nên dựng người trực dậy.
    assert NGUONG["ltt_image:cong_im_lang"] == 2


# ═══════════ B4: chốt CPU-fallback phải BẮN được, không chỉ đếm được ═════════
#
# 🔴 Một cảnh báo chưa từng bắn là một cảnh báo chưa từng được kiểm. Ba mảnh phải
#    khớp nhau, và mỗi mảnh nằm ở một tệp khác: cổng đặt `dang_lo`, phép thăm dò
#    đếm metric, `ops_alerts` so với ngưỡng. Lệch tên metric ở bất kỳ đâu thì cả
#    dây im lặng — và im lặng trông y hệt "mọi thứ bình thường".

def test_dang_lo_tu_health_lam_TANG_metric(monkeypatch):
    """Mảnh 2: `/health` báo `dang_lo` ⇒ phép thăm dò phải đếm."""
    from platform_core import job_runner
    monkeypatch.setenv("LTT_RENDER_BASE_URL", "http://may-b:8199")

    class _R:
        status_code = 200

        @staticmethod
        def json():
            return {"gpu": {"dang_lo": True, "vram_dung_mb": 1600,
                            "ly_do": "dang ve 300s nhung VRAM chi 1600 MB"}}

    import httpx
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _R())

    dem = []
    # ⚠️ Vá HÀM trên chính mô-đun, không vá thuộc tính trên `job_runner`.
    #    `_tham_gpu_anh` dùng `from platform_core import api_pool` **bên trong**
    #    hàm, nên nó lấy mô-đun thật mỗi lượt — đặt `job_runner.api_pool = ...`
    #    không có tác dụng nào. (QT-12: 34 test từng xanh một mình, đỏ trong lô.)
    from platform_core import api_keys, api_pool
    monkeypatch.setattr(api_pool, "chon_key", lambda *a, **k: object())
    monkeypatch.setattr(api_keys, "lay_credential", lambda *a, **k: "tok")
    from platform_core.public_api import metrics
    monkeypatch.setattr(metrics, "increment", lambda ten, **k: dem.append(ten))

    assert job_runner._tham_gpu_anh(object()) is False
    assert dem == ["ltt_image:tren_cpu"]


def test_metric_do_BAN_ngay_lan_dau(monkeypatch):
    """Mảnh 3: một lần đếm là đủ để `ops_alerts` bắn.

    Ngưỡng 1 — khác `cong_im_lang` (2). Chốt này không có dương tính giả, không
    tự khỏi, và mỗi vòng chờ là tiền của khách.
    """
    from platform_core.public_api import ops_alerts
    ra = ops_alerts.danh_gia({"counters": {"ltt_image:tren_cpu": 1}},
                             {"counters": {}})
    ten = [x["ten"] for x in ra]
    assert "ltt_image:tren_cpu" in ten, "dem roi ma khong bao thi ca day im lang"


def test_cong_im_lang_MOT_lan_thi_CHUA_ban(monkeypatch):
    """Một cú chớp mạng không được dựng người trực dậy."""
    from platform_core.public_api import ops_alerts
    ra = ops_alerts.danh_gia({"counters": {"ltt_image:cong_im_lang": 1}},
                             {"counters": {}})
    assert "ltt_image:cong_im_lang" not in [x["ten"] for x in ra]
    ra2 = ops_alerts.danh_gia({"counters": {"ltt_image:cong_im_lang": 2}},
                              {"counters": {}})
    assert "ltt_image:cong_im_lang" in [x["ten"] for x in ra2]
