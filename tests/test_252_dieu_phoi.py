"""
test_252 — điều phối một job sinh ảnh nội bộ từ đầu đến cuối. (H37/A7)

Không mạng, không GPU, không CSDL. Mỗi test chốt một ràng buộc mà nếu vi phạm thì
job vẫn "chạy" nhưng giao sai hàng — loại hỏng đắt nhất.
"""
from __future__ import annotations

import pytest

from platform_core.image_gen import cong_render as CR
from platform_core.image_gen import dieu_phoi as DP


class VeGia:
    def __init__(self, key, url):
        self.key, self.url = key, url
        self.method, self.headers = "PUT", {"Content-Type": "image/png"}


class StorageGia:
    """Backend R2 giả: cấp vé thật. `khong_co_ve=True` mô phỏng backend cục bộ."""

    def __init__(self, khong_co_ve=False, khong_co_url=False):
        self.khong_co_ve = khong_co_ve
        self.khong_co_url = khong_co_url
        self.da_cap = []

    def try_put_url(self, key, ttl_s=None, content_type=None):
        self.da_cap.append({"key": key, "ttl_s": ttl_s, "content_type": content_type})
        return None if self.khong_co_ve else VeGia(key, f"https://r2/put/{key}")

    def try_url_for(self, key, ttl_s=None):
        return None if self.khong_co_url else f"https://r2/get/{key}"


def _cong(kich_ban):
    goi = []

    def http(method, path, *, json=None, timeout=None):
        goi.append((method, path, json))
        v = kich_ban(method, path, json) if callable(kich_ban) else kich_ban.get((method, path))
        return v if v is not None else (404, {})

    c = CR.CongRender(goi=http)
    c._da_gui = goi          # type: ignore[attr-defined]
    return c


def _dp(cong, storage=None, goi_llm=None, **kw):
    return DP.DieuPhoi(cong=cong, storage=storage or StorageGia(),
                       goi_llm=goi_llm, sleep=lambda _: None,
                       now=_dong_ho(), **kw)


def _dong_ho():
    hop = {"t": 0.0}

    def now():
        hop["t"] += 1.0
        return hop["t"]
    return now


def _xong(image_keys):
    return {("POST", "/v1/images/generations"): (202, {"status": "queued"}),
            ("GET", "/v1/jobs/j1"): (200, {"job_id": "j1", "status": "completed",
                                           "image_keys": list(image_keys)})}


# ───────────────────────── đường đi trọn vẹn ────────────────────────────────
def test_duong_thanh_cong_tra_ve_khoa_R2():
    st = StorageGia()
    dp = _dp(_cong(_xong(["anh/j1/0.png"])), st,
             goi_llm=lambda t, h: "A calico cat on a windowsill")
    kq = dp.chay(job_id="j1", prompt="Con mèo tam thể ngủ trên bậu cửa sổ")
    assert kq.image_keys == ("anh/j1/0.png",) and kq.da_dich


def test_PROMPT_GUI_DI_la_ban_DA_DICH_chu_khong_phai_ban_goc():
    """⛔ Ràng buộc quan trọng nhất của tệp này. Gửi bản tiếng Việt thì model vẫn
    vẽ ra một tấm ảnh — chỉ là **không liên quan gì tới yêu cầu**, và không có lỗi
    nào báo. Khách trả tiền cho một tấm ảnh sai (D-027)."""
    cong = _cong(_xong(["anh/j1/0.png"]))
    _dp(cong, goi_llm=lambda t, h: "A calico cat sleeping on a windowsill").chay(
        job_id="j1", prompt="Con mèo tam thể ngủ trên bậu cửa sổ")
    than = [g[2] for g in cong._da_gui if g[1] == "/v1/images/generations"][0]
    assert than["prompt"] == "A calico cat sleeping on a windowsill"
    assert "mèo" not in than["prompt"]


def test_prompt_tieng_ANH_khong_goi_LLM():
    """Không dịch cái đã là tiếng Anh — đỡ một lượt gọi và một khoản credit."""
    goi = []
    dp = _dp(_cong(_xong(["anh/j1/0.png"])),
             goi_llm=lambda t, h: goi.append(t) or "khong nen goi")
    kq = dp.chay(job_id="j1", prompt="A calico cat sleeping on a windowsill")
    assert goi == [] and not kq.da_dich


# ═════ vé vào / vé ra — máy B không giữ khoá lưu trữ nào (Q102) ══════════════
def test_ve_PUT_rang_buoc_dung_content_type():
    """Vé presigned của R2 **ràng buộc `Content-Type`**; máy B gửi sai header là
    R2 trả 403 và ảnh mất giữa đường."""
    st = StorageGia()
    _dp(_cong(_xong(["anh/j1/0.png"])), st,
        goi_llm=lambda t, h: "x").chay(job_id="j1", prompt="A cat")
    assert st.da_cap[0]["content_type"] == "image/png"


def test_han_ve_PUT_phai_DAI_HON_tran_cho():
    """Vé hết hạn giữa lúc máy B đang vẽ thì công sức đổ sông: ảnh vẽ xong rồi
    nhưng không đẩy lên được."""
    assert DP.TTL_PUT_S > DP.TRAN_CHO_S


def test_cap_du_ve_cho_NHIEU_anh():
    st = StorageGia()
    cong = _cong({("POST", "/v1/images/generations"): (202, {"status": "queued"}),
                  ("GET", "/v1/jobs/j1"): (200, {"job_id": "j1", "status": "completed",
                                                 "image_keys": ["a", "b", "c"]})})
    _dp(cong, st, goi_llm=lambda t, h: "x").chay(job_id="j1", prompt="A cat", so_anh=3)
    than = [g[2] for g in cong._da_gui if g[1] == "/v1/images/generations"][0]
    assert len(than["put_urls"]) == 3 and len(than["image_keys"]) == 3


def test_luu_tru_cuc_bo_KHONG_cap_duoc_ve_thi_BAO_RO():
    """Backend cục bộ trả `None`. Gửi job đi lúc đó là gửi một thứ **chắc chắn
    hỏng giữa chừng** — nói thẳng ngay từ đầu."""
    dp = _dp(_cong({}), StorageGia(khong_co_ve=True), goi_llm=lambda t, h: "x")
    with pytest.raises(DP.DieuPhoiError) as e:
        dp.chay(job_id="j1", prompt="A cat")
    assert "R2" in str(e.value)


def test_anh_tham_chieu_duoc_cap_presigned_GET():
    cong = _cong(_xong(["anh/j1/0.png"]))
    _dp(cong, goi_llm=lambda t, h: "x").chay(
        job_id="j1", prompt="A cat", mode="edit", ref_keys=["upload/abc.png"])
    than = [g[2] for g in cong._da_gui if g[1] == "/v1/images/generations"][0]
    assert than["refs"] == [{"url": "https://r2/get/upload/abc.png", "role": "edit"}]


def test_khong_cap_duoc_URL_anh_tham_chieu_thi_BAO_RO():
    dp = _dp(_cong({}), StorageGia(khong_co_url=True), goi_llm=lambda t, h: "x")
    with pytest.raises(DP.DieuPhoiError) as e:
        dp.chay(job_id="j1", prompt="A cat", mode="edit", ref_keys=["u/a.png"])
    assert "tham chiếu" in str(e.value)


# ═════ BẬN không phải HỎNG — app phải phân biệt được ════════════════════════
def test_may_ban_thi_BanError_di_THANG_ra_ngoai():
    """⛔ Bọc `BanError` thành lỗi chung là app sẽ nói "sinh ảnh thất bại" trong khi
    sự thật là "máy nhà đang bận, còn N phút". Hai câu đó dẫn tới hai hành động
    khác hẳn nhau của khách."""
    cong = _cong({("POST", "/v1/images/generations"):
                  (429, {"error": {"message": "video dang chay"}, "eta_s": 600})})
    with pytest.raises(CR.BanError) as e:
        _dp(cong, goi_llm=lambda t, h: "x").chay(job_id="j1", prompt="A cat")
    assert e.value.eta_s == 600
    assert not isinstance(e.value, DP.DieuPhoiError)


def test_dieu_phoi_KHONG_tu_chuyen_sang_dam_may():
    """D-010: đổi model sau lưng khách là đánh tráo sản phẩm. Tầng này chỉ báo bận."""
    import inspect
    ma = inspect.getsource(DP)
    assert "gemini" not in ma.lower().replace("dich_gemini", ""), (
        "dieu_phoi khong duoc tu goi model dam may")


# ═════════════════════════ hỏng và hết giờ ══════════════════════════════════
def test_job_hong_thi_bao_ca_MA_LOI_de_con_truy_duoc():
    cong = _cong({("POST", "/v1/images/generations"): (202, {"status": "queued"}),
                  ("GET", "/v1/jobs/j1"): (200, {"job_id": "j1", "status": "failed",
                                                 "error_code": "oom",
                                                 "error_message": "het VRAM"})})
    with pytest.raises(DP.DieuPhoiError) as e:
        _dp(cong, goi_llm=lambda t, h: "x").chay(job_id="j1", prompt="A cat")
    assert "oom" in str(e.value)


def test_het_gio_thi_HUY_chu_khong_bo_may_B_ve_tiep():
    """Bỏ mặc là máy B vẽ tiếp một thứ **không ai còn chờ**, chiếm GPU của việc sau."""
    cong = _cong({("POST", "/v1/images/generations"): (202, {"status": "queued"}),
                  ("GET", "/v1/jobs/j1"): (200, {"job_id": "j1", "status": "generating"}),
                  ("POST", "/v1/jobs/j1/cancel"): (200, {"ok": True})})
    dp = _dp(cong, goi_llm=lambda t, h: "x", tran_cho_s=5.0)
    with pytest.raises(DP.DieuPhoiError):
        dp.chay(job_id="j1", prompt="A cat")
    assert any(g[1] == "/v1/jobs/j1/cancel" for g in cong._da_gui), "phai huy job"


def test_mot_cu_vap_mang_khong_lam_hong_job():
    """LAN vấp một nhịp là chuyện thường. Ba nhịp liên tiếp mới là máy B chết."""
    dem = {"n": 0}

    def kich_ban(method, path, json):
        if path == "/v1/images/generations":
            return 202, {"status": "queued"}
        dem["n"] += 1
        if dem["n"] == 1:
            return 599, {}                      # mot cu vap
        return 200, {"job_id": "j1", "status": "completed", "image_keys": ["k"]}

    kq = _dp(_cong(kich_ban), goi_llm=lambda t, h: "x").chay(job_id="j1", prompt="A cat")
    assert kq.image_keys == ("k",)


def test_dich_hong_thi_KHONG_gui_gi_cho_may_B():
    """Hỏng ở bước dịch thì phải hỏng TRƯỚC khi tiêu một giây GPU nào."""
    cong = _cong({})

    def hong(t, h):
        raise RuntimeError("het quota")
    with pytest.raises(DP.DieuPhoiError):
        _dp(cong, goi_llm=hong).chay(job_id="j1", prompt="Con mèo tam thể")
    assert cong._da_gui == [], "khong duoc cham vao may B khi dich da hong"
