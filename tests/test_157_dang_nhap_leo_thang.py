"""
Đăng nhập: leo thang sang THÁCH ĐỐ, không khoá tài khoản.

Bản trước khoá cứng theo tài khoản sau 5 lần sai/60 giây. Đó là một lỗ **từ chối
dịch vụ**: ai biết email của khách cũng khoá được họ vô thời hạn, chỉ cần bắn
vài lần thử rác mỗi phút. Chủ tài khoản gõ đúng mật khẩu vẫn không vào được.
OWASP nói thẳng điều này và khuyên thay bằng thách đố.

Tính chất phải giữ:
1. kẻ khác KHÔNG khoá được tài khoản của người thật — người thật vẫn vào được
   sau khi giải thách đố;
2. bot không giải được thách đố thì không tới bước kiểm mật khẩu;
3. chặn cứng chỉ theo IP và ngưỡng cao (CGNAT: rất nhiều người thật chung IP);
4. mở trang đăng nhập KHÔNG bị tính là một lần thử.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    url = f"sqlite:///{(tmp_path / 'a.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-leo-thang")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    # Turnstile BẬT — đây chính là thứ đang thử.
    monkeypatch.setenv("TURNSTILE_SITE_KEY", "site-test")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "secret-test")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); s = next(gen)
    tao_nguoi_dung(s, email="nan-nhan@x.com", password="matkhau-that", is_verified=True)
    s.commit(); s.close()

    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver")
    try:
        yield c
    finally:
        dbmod.reset_engine()


def _csrf(client) -> str:
    return re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text).group(1)


def _thu(client, email, matkhau, *, turnstile_token=""):
    data = {"username": email, "password": matkhau, "csrf_token": _csrf(client)}
    if turnstile_token:
        data["cf-turnstile-response"] = turnstile_token
    return client.post("/login", data=data, follow_redirects=False)


def _turnstile_that_bai(monkeypatch):
    monkeypatch.setattr("server.auth.turnstile.xac_minh",
                        lambda token, remote_ip="": False)


def _turnstile_thanh_cong(monkeypatch):
    monkeypatch.setattr("server.auth.turnstile.xac_minh",
                        lambda token, remote_ip="": True)


# ── Tính chất 1: KHÔNG khoá được tài khoản người khác ─────────────────────────
def test_ke_tan_cong_khong_khoa_duoc_tai_khoan_nguoi_that(env, monkeypatch):
    """Đây là hồi quy cho lỗ DoS. Kẻ tấn công bắn sai liên tục vào email nạn
    nhân; nạn nhân giải thách đố rồi PHẢI vào được bằng mật khẩu đúng."""
    client = env
    _turnstile_that_bai(monkeypatch)
    for _ in range(10):
        _thu(client, "nan-nhan@x.com", "mat-khau-bay")

    # Nạn nhân tới, gõ đúng mật khẩu, giải được thách đố.
    _turnstile_thanh_cong(monkeypatch)
    r = _thu(client, "nan-nhan@x.com", "matkhau-that", turnstile_token="ok")
    assert r.status_code == 303, (
        "tai khoan bi khoa boi ke khac — lo tu choi dich vu da quay lai")


def test_qua_nguong_thi_hien_thach_do_chu_khong_khoa(env, monkeypatch):
    client = env
    _turnstile_that_bai(monkeypatch)
    from server.routes.auth import NGUONG_THACH_DO
    for _ in range(NGUONG_THACH_DO):
        _thu(client, "nan-nhan@x.com", "sai")
    r = _thu(client, "nan-nhan@x.com", "sai")
    assert r.status_code == 401                      # khong phai 429 "bi khoa"
    assert "robot" in r.text                         # doi giai thach do
    assert "cf-turnstile" in r.text                  # widget co that trong form


# ── Tính chất 2: bot không qua được thách đố ──────────────────────────────────
def test_khong_giai_thach_do_thi_khong_toi_buoc_kiem_mat_khau(env, monkeypatch):
    """Kể cả mật khẩu ĐÚNG cũng không vào được nếu chưa qua thách đố — nếu không
    thì thách đố chỉ là trang trí."""
    client = env
    _turnstile_that_bai(monkeypatch)
    from server.routes.auth import NGUONG_THACH_DO
    for _ in range(NGUONG_THACH_DO):
        _thu(client, "nan-nhan@x.com", "sai")
    r = _thu(client, "nan-nhan@x.com", "matkhau-that")
    assert r.status_code == 401
    assert "robot" in r.text


def test_giai_hut_thach_do_khong_bi_tinh_them_lan_thu(env, monkeypatch):
    """Người thật giải hụt vài lần không được tự đẩy mình tới ngưỡng chặn cứng."""
    client = env
    _turnstile_that_bai(monkeypatch)
    from server.routes.auth import NGUONG_THACH_DO, NGUONG_CHAN_CUNG
    for _ in range(NGUONG_THACH_DO):
        _thu(client, "nan-nhan@x.com", "sai")
    for _ in range(NGUONG_CHAN_CUNG + 5):
        r = _thu(client, "nan-nhan@x.com", "matkhau-that")
        assert r.status_code != 429, "giai hut thach do bi tinh thanh lan thu"
    _turnstile_thanh_cong(monkeypatch)
    assert _thu(client, "nan-nhan@x.com", "matkhau-that",
                turnstile_token="ok").status_code == 303


# ── Tính chất 3: chặn cứng chỉ theo IP, ngưỡng cao ────────────────────────────
def test_chan_cung_theo_ip_o_nguong_cao(env, monkeypatch):
    client = env
    _turnstile_thanh_cong(monkeypatch)          # qua thach do, van dem lan thu
    from server.routes.auth import NGUONG_CHAN_CUNG
    ma = [_thu(client, f"ai-do-{i}@x.com", "sai", turnstile_token="ok").status_code
          for i in range(NGUONG_CHAN_CUNG + 2)]
    assert 429 in ma, "khong bao gio chan cung — script ban vo han"
    assert ma.index(429) >= NGUONG_CHAN_CUNG, (
        f"chan cung qua som ({ma.index(429)}) — CGNAT se khoa nham nguoi vo can")


def test_khong_co_turnstile_thi_lui_ve_tran_chat(tmp_path, monkeypatch):
    """Thiếu biến môi trường Turnstile KHÔNG được âm thầm nới phòng thủ.

    Không có thách đố thì không có gì để leo thang tới; giữ trần 20 lúc đó nghĩa
    là quên một biến môi trường = nới trần gấp bốn mà không ai hay.
    """
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'b.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-khong-turnstile")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    monkeypatch.delenv("TURNSTILE_SITE_KEY", raising=False)
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    try:
        from server.routes.auth import NGUONG_CHAN_CUNG_KHONG_THACH_DO
        ma = [_thu(client, "ai@x.com", "sai").status_code
              for _ in range(NGUONG_CHAN_CUNG_KHONG_THACH_DO + 2)]
        assert 429 in ma, "khong co Turnstile ma cung khong chan cung"
        assert ma.index(429) <= NGUONG_CHAN_CUNG_KHONG_THACH_DO + 1
        assert "cf-turnstile" not in client.get("/login").text
    finally:
        dbmod.reset_engine()


def test_khong_co_turnstile_thi_van_khoa_theo_tai_khoan_qua_nhieu_ip(tmp_path, monkeypatch):
    """Mất Turnstile thì khoá theo tài khoản là đường phòng thủ DUY NHẤT còn lại
    cho kiểu dò một tài khoản từ nhiều IP. Thà giữ phòng thủ thô còn hơn không."""
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-nhieu-ip")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    monkeypatch.delenv("TURNSTILE_SITE_KEY", raising=False)
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    try:
        from server.routes.auth import NGUONG_CHAN_CUNG_KHONG_THACH_DO
        for i in range(NGUONG_CHAN_CUNG_KHONG_THACH_DO):
            r = client.post("/login",
                            data={"username": "muc-tieu@x.com", "password": "sai",
                                  "csrf_token": _csrf(client)},
                            headers={"CF-Connecting-IP": f"10.0.0.{i}"})
            assert r.status_code == 401
        r = client.post("/login",
                        data={"username": "muc-tieu@x.com", "password": "sai",
                              "csrf_token": _csrf(client)},
                        headers={"CF-Connecting-IP": "10.0.0.250"})   # IP hoan toan moi
        assert r.status_code == 429
    finally:
        dbmod.reset_engine()


def test_co_turnstile_thi_nhieu_ip_KHONG_khoa_tai_khoan(env, monkeypatch):
    """Ngược lại: có Turnstile thì cùng kịch bản đó KHÔNG được khoá tài khoản —
    chỉ đòi thách đố. Đây là ranh giới giữa hai chế độ."""
    client = env
    _turnstile_that_bai(monkeypatch)
    for i in range(10):
        r = client.post("/login",
                        data={"username": "nan-nhan@x.com", "password": "sai",
                              "csrf_token": _csrf(client)},
                        headers={"CF-Connecting-IP": f"10.0.1.{i}"})
        assert r.status_code != 429, "tai khoan bi khoa — lo DoS quay lai"
    _turnstile_thanh_cong(monkeypatch)
    r = client.post("/login",
                    data={"username": "nan-nhan@x.com", "password": "matkhau-that",
                          "csrf_token": _csrf(client), "cf-turnstile-response": "ok"},
                    headers={"CF-Connecting-IP": "10.0.1.99"}, follow_redirects=False)
    assert r.status_code == 303


def test_nguong_chan_cung_du_cao_cho_cgnat(env):
    """Chốt con số: nhà mạng di động VN dùng CGNAT, nhiều người thật chung IP."""
    from server.routes.auth import NGUONG_CHAN_CUNG, NGUONG_THACH_DO
    assert NGUONG_CHAN_CUNG >= 20
    assert NGUONG_THACH_DO < NGUONG_CHAN_CUNG


# ── Tính chất 4: mở trang không bị tính là lần thử ────────────────────────────
def test_mo_trang_dang_nhap_khong_bi_tinh_la_lan_thu(env):
    client = env
    for _ in range(30):
        assert client.get("/login").status_code == 200


def test_dang_nhap_dung_ngay_lan_dau_khong_thay_thach_do(env):
    """Người dùng bình thường không bao giờ gặp thách đố."""
    client = env
    r = client.get("/login")
    assert "cf-turnstile" not in r.text
    assert _thu(client, "nan-nhan@x.com", "matkhau-that").status_code == 303


def test_dang_nhap_thanh_cong_xoa_bo_dem(env, monkeypatch):
    client = env
    _turnstile_thanh_cong(monkeypatch)
    for _ in range(3):
        _thu(client, "nan-nhan@x.com", "sai", turnstile_token="ok")
    assert _thu(client, "nan-nhan@x.com", "matkhau-that",
                turnstile_token="ok").status_code == 303
    client.post("/logout", data={"csrf_token": _csrf(client)}, follow_redirects=False)
    # Bo dem da xoa -> lan sau khong bi doi thach do ngay.
    assert "cf-turnstile" not in client.get("/login").text


# ── Bộ đếm: so_lan chỉ đọc, ghi_nhan không trần ───────────────────────────────
def test_so_lan_khong_lam_tang_bo_dem():
    from server.auth.rate_limit import RateLimiter
    lim = RateLimiter(max_attempts=5, window_seconds=60.0)
    lim.ghi_nhan("k")
    assert lim.so_lan("k") == 1
    assert lim.so_lan("k") == 1                 # doc lai van la 1
    assert lim.so_lan("k") == 1


def test_ghi_nhan_khong_co_tran():
    """`allow` gộp đếm với phán quyết nên không diễn tả được nhiều mức."""
    from server.auth.rate_limit import RateLimiter
    lim = RateLimiter(max_attempts=5, window_seconds=60.0)
    for i in range(1, 12):
        assert lim.ghi_nhan("k") == i


def test_reset_xoa_bo_dem():
    from server.auth.rate_limit import RateLimiter
    lim = RateLimiter(max_attempts=5, window_seconds=60.0)
    lim.ghi_nhan("k"); lim.ghi_nhan("k")
    lim.reset("k")
    assert lim.so_lan("k") == 0
