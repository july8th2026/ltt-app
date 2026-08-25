"""Q4 — luồng lần đầu (C), giấu lỗi cấu hình (D), nối Playground với Khoá (G).

Ba hạng mục khác nhau nhưng cùng một câu hỏi: **một người lạ có tự đi hết được
không, hay đến một chỗ thì mắc kẹt mà không biết bước tiếp theo là gì.**
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'api-q4.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-api-q4")
    monkeypatch.setenv("LTT_PUBLIC_API", "1")
    # Playground chi dung khoi bieu mau khi co tool DANG MO — fail-closed
    # cua Q92: bat co mot minh khong mo tool nao.
    monkeypatch.setenv("LTT_PUBLIC_API_TOOLS", "image.thumbnail")
    monkeypatch.setenv("LTT_API_KEY_PEPPER", "p" * 40)
    monkeypatch.setenv("LTT_BASE_URL", "https://api.thu-nghiem.example")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models   # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield dbmod
    dbmod.reset_engine()


def _client():
    from fastapi.testclient import TestClient
    from server.app import create_app
    return TestClient(create_app(), base_url="https://testserver",
                      follow_redirects=False)


def _tao_khach(dbmod, credit_ban_dau=20_000):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="q4@test.com", password="matkhau-tot-12",
                           is_verified=True)
        db.flush()
        credit.nap(db, u.id, credit_ban_dau)
        db.commit()
        return u.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _tok(text):
    return re.search(r'name="csrf_token" value="([^"]+)"', text).group(1)


def _dang_nhap(client):
    client.post("/login", data={"username": "q4@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": _tok(client.get("/login").text)})


def _tao_khoa(client, *, mode="test", name="khoa-thu"):
    trang = client.get("/developers/keys")
    du = {t: "" for t in
          set(re.findall(r'<(?:input|select)[^>]*name="([^"]+)"', trang.text))}
    du.update({"csrf_token": _tok(trang.text), "name": name, "mode": mode})
    return client.post("/developers/keys", data=du)


# ── C · luồng lần đầu có trạng thái THẬT ───────────────────────────────────

def test_ba_buoc_doc_trang_thai_that_chu_khong_phai_ba_lien_ket(moi_truong):
    """Trước 25/08 đây là ba liên kết rời — một cái menu, không phải hướng dẫn."""
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)

        # Chưa có gì: cả ba bước còn là việc phải làm.
        t = client.get("/developers").text
        assert "Tạo khóa trong project đó" in t
        assert "(cần khóa ở bước trên trước)" in t, (
            "buoc goi thu phai noi ro no dang cho buoc truoc, "
            "khong duoc hien mot lenh curl khong chay duoc")

        # Có khoá: bước 1 và 2 xong, bước 3 hiện lệnh chạy được.
        _tao_khoa(client)
        t = client.get("/developers").text
        assert "Đã có project" in t and "Đã có khóa đang hoạt động" in t
        assert "(cần khóa ở bước trên trước)" not in t
        assert "curl -s https://api.thu-nghiem.example/api/v1/tools" in t, (
            "lenh mau phai dung goc URL THAT cua may chu nay")
    finally:
        client.close()


def test_lenh_mau_khong_viet_cung_dia_chi(moi_truong, monkeypatch):
    """Viết cứng `app.lttstudios.com` thì lệnh SAI trên mọi cài đặt khác.

    Và nó sai im lặng: khách chép, chạy, nhận lỗi mạng, và không nghĩ rằng
    chính trang hướng dẫn đưa nhầm địa chỉ.
    """
    monkeypatch.setenv("LTT_BASE_URL", "https://mot-noi-khac.example")
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        _tao_khoa(client)
        t = client.get("/developers").text
        assert "https://mot-noi-khac.example/api/v1/tools" in t
        assert "app.lttstudios.com" not in t
    finally:
        client.close()


def test_da_goi_API_KHONG_suy_ra_tu_so_job(moi_truong):
    """Phần lớn lượt gọi đầu tiên là `GET /tools` — nó không tạo job nào.

    Suy trạng thái từ số job sẽ nói *"chưa gọi bao giờ"* với người vừa gọi
    xong, và đó là kiểu sai làm người ta ngờ cả phần còn lại của trang.
    """
    from server.routes.developer import _overview_counts
    import platform_core.db as dbmod
    from platform_core.models import User

    user_id = _tao_khach(moi_truong)
    gen = dbmod.get_session()
    db = next(gen)
    try:
        user = db.get(User, user_id)
        counts = _overview_counts(db, user)
        assert counts["da_goi_api"] is False
        assert counts["api_jobs"] == 0
        # Hai con số này phải là hai câu hỏi khác nhau, không phải một.
        assert "da_goi_api" in counts and "api_jobs" in counts
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── D · lỗi cấu hình của TA không được hiện cho khách ──────────────────────

def test_thieu_pepper_khong_lo_ten_bien_moi_truong(moi_truong, monkeypatch):
    """Khách học được tên một biến môi trường của ta, và vẫn không làm gì được.

    Đó không phải việc của họ. Chi tiết đi vào log; khách nhận một câu nói rõ
    đây là lỗi phía chúng tôi.
    """
    monkeypatch.delenv("LTT_API_KEY_PEPPER", raising=False)
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        r = _tao_khoa(client)
        assert r.status_code == 200
        assert "LTT_API_KEY_PEPPER" not in r.text, "lo ten bien moi truong"
        assert "lỗi phía chúng tôi" in r.text, (
            "phai noi ro day khong phai loi cua khach")
    finally:
        client.close()


def test_loi_KHACH_SUA_DUOC_thi_van_hien_nguyen_van(moi_truong):
    """Giấu lỗi cấu hình KHÔNG được kéo theo việc giấu lỗi khách sửa được.

    Một thông báo chung chung cho mọi thứ là cách biến một lỗi sửa được thành
    một lỗi không sửa được.
    """
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        trang = client.get("/developers/keys")
        du = {t: "" for t in
              set(re.findall(r'<(?:input|select)[^>]*name="([^"]+)"', trang.text))}
        du.update({"csrf_token": _tok(trang.text), "name": "x",
                   "project_id": "khong-ton-tai-dau"})
        r = client.post("/developers/keys", data=du)
        assert "Không tìm thấy project." in r.text
        assert "lỗi phía chúng tôi" not in r.text
    finally:
        client.close()


# ── G · Playground nối với trang Khoá ──────────────────────────────────────

def test_playground_khong_khoa_thi_chi_ro_loi_ra(moi_truong):
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        t = client.get("/developers/playground").text
        assert "Bạn chưa có khóa nào dùng được." in t
        assert "/developers/keys" in t, "khong co duong toi cho tao khoa"
        assert "không tốn credit nào" in t, (
            "khong noi khoa Test khong ton tien — dung thu nguoi vao "
            "Playground muon nghe nhat")
    finally:
        client.close()


def test_playground_co_khoa_thi_liet_ke_NUA_CONG_KHAI(moi_truong):
    """Liệt kê `key_id` là an toàn; chuỗi bí mật thì không tồn tại ở đâu cả."""
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        r = _tao_khoa(client, mode="test", name="khoa-playground")
        bi_mat = re.search(r"\b(ltt_[a-z]k_[A-Za-z0-9_\-]{10,})", r.text)
        assert bi_mat, "khong tao duoc khoa"

        t = client.get("/developers/playground").text
        assert "Khóa đang dùng được của bạn" in t
        assert "khoa-playground" in t
        assert "Bạn chưa có khóa nào dùng được." not in t
        # Chuỗi bí mật KHÔNG được lặp lại ở đây: nó chỉ tồn tại trong một phản
        # hồi duy nhất, lúc tạo.
        assert bi_mat.group(1) not in t, "trang lap lai chuoi bi mat"
    finally:
        client.close()


def test_playground_van_KHONG_tu_dien_khoa(moi_truong):
    """Chốt điều KHÔNG được đổi.

    Trang cố ý không điền hộ khoá: máy chủ chỉ giữ dấu vân tay một chiều, và
    một cổng nội bộ mượn phiên đăng nhập để gọi thay sẽ là **đường thứ hai**
    tới đường tính tiền — nền tảng cố ý chỉ có một.
    """
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        _tao_khoa(client)
        t = client.get("/developers/playground").text
        m = re.search(r'<input id="pg-key"[^>]*>', t)
        assert m, "khong con o nhap khoa"
        assert "value=" not in m.group(0), "trang dang dien ho khoa"
        assert 'type="password"' in m.group(0)
    finally:
        client.close()
