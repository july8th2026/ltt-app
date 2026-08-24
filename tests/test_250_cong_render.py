"""
test_250 — client phía máy A gọi cổng render máy B (`platform_core/image_gen/cong_render.py`).

Toàn bộ chạy trên máy A, **không cần máy B**. Mỗi test neo vào một luật đã trả giá
để học, không vào một ý thích thiết kế.
"""
from __future__ import annotations

import pytest

from platform_core.image_gen import cong_render as CR


def _cong(kich_ban):
    """`kich_ban` = dict {(method, path): (status, body)} hoặc callable."""
    goi_da_gui = []

    def goi(method, path, *, json=None, timeout=None):
        goi_da_gui.append((method, path, json))
        v = kich_ban(method, path, json) if callable(kich_ban) else kich_ban.get((method, path))
        if v is None:
            return 404, {}
        return v

    c = CR.CongRender(goi=goi)
    c._da_gui = goi_da_gui          # type: ignore[attr-defined]
    return c


# ─────────────── LUẬT 1: 429 là BẬN, không phải hỏng ────────────────────────
def test_429_nem_BanError_chu_KHONG_nem_CongRenderError():
    """⛔ Cạm bẫy đắt nhất của H37. Máy B dùng chung GPU với dự án video; một tối
    chạy video là hàng chục lượt 429. Coi 429 là lỗi provider ⇒ `api_pool` cooldown
    rồi **disable key sau 5 lần** ⇒ model nhà TỰ TẮT VĨNH VIỄN vì hàng xóm bận."""
    c = _cong({("POST", "/v1/images/generations"):
               (429, {"error": {"code": "busy", "message": "video dang chay"},
                      "eta_s": 900, "busy": True})})
    with pytest.raises(CR.BanError) as e:
        c.gui(job_id="j1", model="hidream-o1", mode="t2i", prompt="x",
              put_urls=["https://r2/put"])
    assert e.value.eta_s == 900
    assert "video" in e.value.ly_do
    # Va no KHONG duoc la CongRenderError - neu la thi bat chung se coi no la loi.
    assert not isinstance(e.value, CR.CongRenderError)


def test_ban_khong_biet_bao_lau_thi_eta_None_chu_khong_bia_so():
    """"Không biết" phải nói là không biết. Bịa một con số nhỏ là hứa với khách
    một thứ mình không biết — luật không-bao-giờ-lạc-quan của `busy.py`."""
    c = _cong({("POST", "/v1/images/generations"):
               (429, {"error": {"message": "dang ban"}})})
    with pytest.raises(CR.BanError) as e:
        c.gui(job_id="j1", model="m", mode="t2i", prompt="x", put_urls=["u"])
    assert e.value.eta_s is CR.ETA_KHONG_BIET


def test_mat_lien_lac_thi_coi_la_BAN_chu_khong_bao_ranh():
    """Hỏi được mà không trả lời ⇒ **không** được kết luận là rảnh rồi gửi việc."""
    def chet(*a, **k):
        raise OSError("mang dut")
    c = CR.CongRender(goi=chet)
    ban, ly_do, eta = c.dang_ban()
    assert ban and eta is CR.ETA_KHONG_BIET


# ─────────────── LUẬT 3: job_id là khoá idempotency ─────────────────────────
def test_thieu_job_id_thi_TU_CHOI_ngay_khong_gui_di():
    """`job_id` là khoá idempotency của cổng. Thiếu nó thì mỗi lần thử lại là một
    lần vẽ mới — D-018 đã đốt ~100 giây GPU mỗi lượt vì đúng chuyện này."""
    c = _cong({})
    with pytest.raises(CR.CongRenderError):
        c.gui(job_id="", model="m", mode="t2i", prompt="x", put_urls=["u"])
    assert c._da_gui == [], "khong duoc cham vao mang khi biet chac se sai"


def test_gui_lai_cung_job_id_tra_200_thi_KHONG_coi_la_loi():
    """Cổng trả 200 (thay vì 202) khi job đã biết. Đó là idempotency chạy đúng,
    không phải lỗi."""
    c = _cong({("POST", "/v1/images/generations"):
               (200, {"job_id": "j1", "status": "generating"})})
    t = c.gui(job_id="j1", model="m", mode="t2i", prompt="x", put_urls=["u"])
    assert t.status == "generating"


# ─────────────── put_urls: máy B không giữ khoá R2 (Q102) ───────────────────
def test_thieu_put_urls_thi_TU_CHOI():
    """Máy B **không giữ bí mật nào của nền tảng**. Không có URL PUT thì nó không
    có đường nào trả ảnh về — gửi đi là chắc chắn hỏng giữa chừng."""
    c = _cong({})
    with pytest.raises(CR.CongRenderError):
        c.gui(job_id="j1", model="m", mode="t2i", prompt="x", put_urls=[])
    assert c._da_gui == []


def test_than_gui_mang_du_truong_cong_can():
    c = _cong({("POST", "/v1/images/generations"): (202, {"status": "queued"})})
    c.gui(job_id="j1", model="hidream-o1", mode="edit", prompt="p",
          negative_prompt="n", put_urls=["u1"], image_keys=["k1"],
          refs=[{"url": "g1", "role": "edit"}], params={"steps": 30})
    than = c._da_gui[0][2]
    assert than["job_id"] == "j1" and than["mode"] == "edit"
    assert than["put_urls"] == ["u1"] and than["image_keys"] == ["k1"]
    assert than["refs"] == [{"url": "g1", "role": "edit"}]
    assert than["params"] == {"steps": 30}


# ─────────────────────────── trạng thái job ─────────────────────────────────
def test_doc_trang_thai_va_ma_loi():
    c = _cong({("GET", "/v1/jobs/j1"):
               (200, {"job_id": "j1", "status": "failed",
                      "error_code": "oom", "error_message": "het VRAM"})})
    t = c.trang_thai("j1")
    assert t.xong and not t.thanh_cong and t.error_code == "oom"


def test_job_xong_thi_co_image_keys():
    c = _cong({("GET", "/v1/jobs/j1"):
               (200, {"job_id": "j1", "status": "completed",
                      "image_keys": ["a/b.png"]})})
    t = c.trang_thai("j1")
    assert t.thanh_cong and t.image_keys == ("a/b.png",)


def test_may_B_khong_biet_job_thi_bao_loi_ro_rang():
    c = _cong({})           # moi duong deu 404
    with pytest.raises(CR.CongRenderError) as e:
        c.trang_thai("j-la")
    assert "j-la" in str(e.value)


# ─────────────────────── không nuốt ngoại lệ lạ ─────────────────────────────
def test_moi_hong_mang_deu_thanh_CongRenderError_chu_khong_lot_ra():
    """Worker không được chết vì một `httpx.ReadTimeout` lọt lên. Mọi thứ hỏng ở
    tầng mạng phải quy về một loại ngoại lệ mà bên gọi biết trước."""
    def chet(*a, **k):
        raise TimeoutError("qua han")
    c = CR.CongRender(goi=chet)
    for goi_thu in (lambda: c.health(), lambda: c.models(), lambda: c.trang_thai("j1")):
        with pytest.raises(CR.CongRenderError):
            goi_thu()


def test_models_doc_duoc_khuon_data():
    """Cổng trả `{"data": [...]}` để `providers_live.parse_models` của nền tảng đọc
    được mà không phải thêm nhánh phân tích mới."""
    c = _cong({("GET", "/v1/models"): (200, {"data": [{"id": "hidream-o1"}]})})
    assert c.models() == [{"id": "hidream-o1"}]


def test_health_bao_ban_kem_ly_do_de_UI_noi_duoc_voi_khach():
    c = _cong({("GET", "/health"):
               (200, {"busy": True, "reason": "co 1 tien trinh khac dang tinh tren GPU",
                      "eta_s": 300.0})})
    ban, ly_do, eta = c.dang_ban()
    assert ban and eta == 300.0 and "GPU" in ly_do


# ═════════ provider `ltt_image` trong registry — fail-closed (H37/G8) ════════

def test_provider_ltt_image_co_trong_registry():
    from platform_core import providers as P
    p = P.get("ltt_image")
    assert p is not None and p.async_poll and p.auth_style == P.AUTH_BEARER


def test_base_url_KHONG_viet_cung_dia_chi_LAN_vao_ma_nguon():
    """⛔ Thư mục này vừa là mã nguồn vừa là BỘ CÀI được chép sang máy khác. Một IP
    nội bộ viết cứng sẽ đi theo sang máy không có nó, và hỏng ở nơi khó truy nhất."""
    from pathlib import Path
    src = Path("platform_core/providers.py").read_text(encoding="utf-8")
    assert "192.168." not in src, "dia chi LAN phai lay tu bien moi truong"
    assert "LTT_RENDER_BASE_URL" in src


def test_model_noi_bo_DA_MO_va_do_la_mot_QUYET_DINH():
    """Model nội bộ **đã bật** ngày 24/08 (G10).

    ⚠️ Bản trước của test này khoá cứng `not is_active` với lý do *"chỉ được bật ở
       G10, sau khi qua cổng G6b"*. Cổng đó **đã chạy** (D-045, chấm mù), chủ sản
       phẩm đã đọc kết quả và quyết bán, và G10 là chỗ ta đang đứng.

    ⛔ Nhưng lật một biến `True` rồi thôi là **vứt mất một bánh cóc**. Thứ chốt cũ
       thật sự bảo vệ không phải giá trị `False` — mà là *"một cờ không bao giờ đủ
       để phục vụ khách"*. Nên test này giữ đúng điều đó, ở dạng còn kiểm được.
    """
    from platform_core import providers as P
    m = P.get("ltt_image").models[0]
    assert m.id == "hidream-o1" and m.is_active, (
        "mo lai model noi bo phai la mot thay doi CO CHU Y, hien ra trong diff")


def test_BAT_is_active_KHONG_du_de_phuc_vu_khach():
    """🔴 Chốt thật của mục này: **bốn cổng độc lập** (D-034).

    `is_active=True` chỉ nói *model dùng được*. Nó KHÔNG mở bề mặt công khai —
    `LTT_PUBLIC_API_TOOLS` vẫn phải liệt kê tên tool. Nếu ngày nào đó bật một cờ
    mà tự nhiên tool ra công khai thì fail-closed đã vỡ, và test này là chỗ biết.
    """
    import os

    from platform_core import registry
    from platform_core.public_api import catalog
    from platform_core.public_api.config import load_public_api_config

    cu = {k: os.environ.get(k) for k in ("LTT_PUBLIC_API", "LTT_PUBLIC_API_TOOLS")}
    os.environ["LTT_PUBLIC_API"] = "1"
    os.environ["LTT_PUBLIC_API_TOOLS"] = ""        # cong tac van hanh: RONG
    try:
        ra = catalog.build_catalog(load_public_api_config(), registry.discover())
    finally:
        for k, v in cu.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    ten = [getattr(t, "name", None) for t in ra]
    assert "image.ltt" not in ten, (
        "is_active=True da tu mo be mat cong khai — fail-closed cua Q92 da vo")


def test_capabilities_CHI_khai_thu_DA_DO():
    """⛔ Chỉ khai chế độ **đã đo thật**. `edit`/`subject` từng KHÔNG được khai vì
    chưa đo VRAM (D-024); G5 đo xong 22/08 (D-032) thì mới khai. Thứ tự đó là điều
    test này giữ — không phải danh sách cụ thể."""
    from platform_core import providers as P
    cap = P.get("ltt_image").models[0].capabilities
    assert cap["modes"] == ["t2i", "edit", "subject"]
    # Chế độ tham chiếu đắt hơn HẲN — con số đó phải có mặt để giao diện nói được.
    assert cap["do_duoc"]["giay_moi_anh_tham_chieu_s30"] >            3 * cap["do_duoc"]["giay_moi_anh_s30"]
    assert [2560, 1440] in cap["buckets"]
    assert cap["do_duoc"]["vram_dinh_mb"] == 17946


def test_capabilities_NOI_RA_gioi_han_chu_khong_giau():
    """D-027: model không hiểu prompt tiếng Việt, và vẽ sai dấu tiếng Việt. Giới
    hạn phải nằm trong bản khai để giao diện nói được với khách, chứ không giấu."""
    from platform_core import providers as P
    cb = " ".join(P.get("ltt_image").models[0].capabilities["canh_bao"])
    assert "tiếng Anh" in cb and "dấu" in cb


def test_them_provider_khong_lam_vo_registry_cu():
    from platform_core import providers as P
    assert {"gemini", "apiai", "cheapkeyai", "byteplus", "plenx"} <= set(P.provider_ids())
