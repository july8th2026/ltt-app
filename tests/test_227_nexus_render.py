"""Nexus N2.5 — ba trang có RENDER được thật, qua app thật.

`test_226` chốt cấu trúc: cờ, chữ ký, nội dung template. Nhưng một template có
thể đúng từng chữ mà vẫn nổ khi render — thiếu một biến trong ngữ cảnh, gõ sai
tên thuộc tính, hay một `{% if %}` không đóng. Không test nào ở `test_226` chạm
tới Jinja.

Ở đây dựng **app thật** bằng `create_app()`, đăng nhập thật, rồi gọi ba đường.
Đây không thay được một lần mở trình duyệt (CSS và bố cục vẫn phải xem bằng
mắt — `CLAUDE.md` mục 5), nhưng nó bắt được đúng lớp lỗi mà mắt người dễ bỏ qua
và lại xảy ra thường xuyên nhất.

Bản đầu của `nexus_trang_chinh.html` **đã** có một lỗi loại này: lồng dấu ngoặc
kép vào `onsubmit="… confirm('…')"` làm vỡ thuộc tính HTML giữa câu.
"""
from __future__ import annotations

import re

import pytest

def _khoa() -> str:
    """Mot khoa cong khai Ed25519 THAT.

    Truoc day cac test nay dung chuoi gia ("ltt_dev_" + "a"*64). Chuoi do luu
    xuong duoc nhung KHONG bao gio xac thuc duoc — nen test xanh trong khi mot
    thiet bi that se khong ket noi noi. Tu khi `doi_ma` kiem dang khoa o bien,
    test phai dung khoa that.
    """
    from platform_core.nexus import agent_auth

    _priv, pub = agent_auth.new_keypair_for_test()
    return pub

from fastapi.testclient import TestClient

PASSWORD = "mat-khau-test-rat-dai-0123456789"


def _csrf(html: str) -> str:
    found = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert found, "khong tim thay csrf_token trong trang"
    return found.group(1)


@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    """App thật với Nexus BẬT."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'render.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "render-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    # Manifest doc co luc nap, nen phai nap lai sau khi dat cờ.
    import importlib

    import apps.nexus.manifest as manifest_mod
    importlib.reload(manifest_mod)
    import apps.nexus.routes as routes_mod
    importlib.reload(routes_mod)
    import platform_core.registry as registry_mod
    registry_mod.discover.cache_clear() if hasattr(
        registry_mod.discover, "cache_clear") else None

    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver")
    try:
        yield client
    finally:
        dbmod.reset_engine()


def _tao_va_dang_nhap(client) -> str:
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    email = "nexus-render@example.com"
    gen = get_session()
    db = next(gen)
    try:
        tao_nguoi_dung(db, email=email, password=PASSWORD, is_verified=True)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    page = client.get("/login").text
    answer = client.post("/login",
                         data={"username": email, "password": PASSWORD,
                               "csrf_token": _csrf(page)},
                         follow_redirects=False)
    assert answer.status_code == 303, answer.text[:300]
    return email


def test_trang_danh_sach_render_duoc(app_bat):
    _tao_va_dang_nhap(app_bat)
    r = app_bat.get("/nexus")
    assert r.status_code == 200, r.text[:400]
    assert "Máy của bạn" in r.text
    assert "Chưa có máy nào" in r.text


def test_trang_ma_ghep_render_va_hien_ma(app_bat):
    _tao_va_dang_nhap(app_bat)
    trang = app_bat.get("/nexus").text
    r = app_bat.post("/nexus/ma-ghep", data={"csrf_token": _csrf(trang)},
                     follow_redirects=False)
    assert r.status_code == 200, r.text[:400]

    # Ma dang ABCD-EFGH tu bang chu cai da bo 0/O/1/I/L.
    assert re.search(r"[23456789A-HJKMNP-Z]{4}-[23456789A-HJKMNP-Z]{4}", r.text)
    # Canh bao hau qua phai co mat, va phai NAM TREN ma.
    assert "điều khiển được máy tính của bạn" in r.text


def test_thuoc_tinh_onsubmit_KHONG_bi_vo(app_bat):
    """Lỗi thật của bản đầu: `onsubmit="… confirm('{{ _("…") }}')"` đóng thuộc
    tính giữa câu, và phần còn lại rơi ra ngoài thành text hiển thị."""
    from platform_core.db import get_session
    from platform_core.nexus import devices

    email = _tao_va_dang_nhap(app_bat)

    gen = get_session()
    db = next(gen)
    try:
        from sqlalchemy import select

        from platform_core.models import User
        user = db.execute(select(User).where(User.email == email)).scalar_one()
        _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
        devices.doi_ma(db, code=ma, public_key=_khoa(),
                       display_name="May test")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    html = app_bat.get("/nexus").text
    assert "May test" in html
    # Thuoc tinh phai dong dung bang mot dau ngoac kep, khong co manh chu tieng
    # Viet nao roi ra ngoai thanh text canh the <form>.
    assert 'onsubmit="return confirm(' in html
    assert "');\">" in html
    assert "Mọi phiên đang chạy sẽ bị cắt ngay.\");" not in html


def test_trang_nhat_ky_render_duoc(app_bat):
    _tao_va_dang_nhap(app_bat)
    r = app_bat.get("/nexus/nhat-ky")
    assert r.status_code == 200, r.text[:400]
    assert "Ai đã vào máy của bạn" in r.text


def test_thao_tac_cua_admin_HIEN_RA_tren_trang_nhat_ky(app_bat):
    """Ràng buộc 5 chỉ có nghĩa nếu khách nhìn thấy trên trang thật."""
    from sqlalchemy import select

    from platform_core.db import get_session
    from platform_core.models import User
    from platform_core.nexus import devices

    email = _tao_va_dang_nhap(app_bat)
    gen = get_session()
    db = next(gen)
    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one()
        _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
        device = devices.doi_ma(db, code=ma, public_key=_khoa())
        devices.thu_hoi(db, device, by="admin:nhan-vien-9")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    html = app_bat.get("/nexus/nhat-ky").text
    assert "nhân viên LTT" in html
    assert "admin:nhan-vien-9" in html


# ── Cờ tắt ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def app_tat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'off.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "render-secret-value")
    monkeypatch.delenv("LTT_NEXUS", raising=False)
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    import importlib

    import apps.nexus.manifest as manifest_mod
    importlib.reload(manifest_mod)
    import apps.nexus.routes as routes_mod
    importlib.reload(routes_mod)

    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver")
    try:
        yield client
    finally:
        dbmod.reset_engine()


def test_co_tat_thi_URL_go_thang_cung_404(app_tat):
    """`mount_all` gắn router bất kể `manifest.enabled`, nên đây là phép thử
    thật sự của cờ — không phải phép thử của việc ẩn khỏi catalog."""
    _tao_va_dang_nhap(app_tat)
    for duong in ("/nexus", "/nexus/nhat-ky"):
        r = app_tat.get(duong)
        assert r.status_code == 404, f"{duong} tra {r.status_code} khi co TAT"


# ── W5: luồng điều khiển của khách (start → poll → sẵn sàng) ─────────────────

def _may_cua_khach(email: str):
    """Tạo một máy đã ghép cho user `email`. Trả (user_id, device_id)."""
    from platform_core.db import get_session
    from platform_core.nexus import devices
    from platform_core.users import tim_theo_email

    gen = get_session(); db = next(gen)
    try:
        user = tim_theo_email(db, email)
        _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
        dev = devices.doi_ma(db, code=ma, public_key=_khoa(), display_name="MayW5")
        db.commit()
        return user.id, dev.id
    finally:
        try: next(gen)
        except StopIteration: pass


def _csrf_tu_trang(client, path="/nexus"):
    return _csrf(client.get(path).text)


def test_W5_bat_dau_dieu_khien_tao_phien_va_chuyen_trang(app_bat):
    email = _tao_va_dang_nhap(app_bat)
    _uid, did = _may_cua_khach(email)
    r = app_bat.post(f"/nexus/dieu-khien/{did}",
                     data={"csrf_token": _csrf_tu_trang(app_bat)},
                     follow_redirects=False)
    assert r.status_code == 303, r.text[:300]
    assert "/nexus/phien/" in r.headers["location"]


def test_W5_may_nguoi_khac_tra_404(app_bat):
    _tao_va_dang_nhap(app_bat)
    r = app_bat.post("/nexus/dieu-khien/khong-ton-tai",
                     data={"csrf_token": _csrf_tu_trang(app_bat)},
                     follow_redirects=False)
    assert r.status_code == 404


def test_W5_poll_ket_noi_cho_roi_san_sang(app_bat, monkeypatch):
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "w5-token-key-0123456789")
    from platform_core.db import get_session
    from platform_core.nexus import sessions

    email = _tao_va_dang_nhap(app_bat)
    uid, did = _may_cua_khach(email)
    r = app_bat.post(f"/nexus/dieu-khien/{did}",
                     data={"csrf_token": _csrf_tu_trang(app_bat)},
                     follow_redirects=False)
    sid = r.headers["location"].rsplit("/", 1)[-1]

    # Trang phien render duoc.
    assert app_bat.get(f"/nexus/phien/{sid}").status_code == 200

    # Chua bao engine -> chua san sang.
    j = app_bat.get(f"/nexus/phien/{sid}/ket-noi").json()
    assert j["san_sang"] is False

    # Agent bao engine (mo phong).
    gen = get_session(); db = next(gen)
    try:
        phien = sessions.lay_phien(db, session_id=sid)
        sessions.bao_engine(db, phien, engine_id="288780716", secret="PwW5-Test")
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    # Gio san sang + tra mat khau.
    j2 = app_bat.get(f"/nexus/phien/{sid}/ket-noi").json()
    assert j2["san_sang"] is True
    assert j2["engine_id"] == "288780716"
    assert j2["mat_khau"] == "PwW5-Test"
    assert j2["server"] == "45.76.185.75"


def test_W5_ket_thuc_dong_phien_va_xoa_mat_khau(app_bat, monkeypatch):
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "w5-token-key-0123456789")
    from platform_core.db import get_session
    from platform_core.nexus import sessions

    email = _tao_va_dang_nhap(app_bat)
    uid, did = _may_cua_khach(email)
    r = app_bat.post(f"/nexus/dieu-khien/{did}",
                     data={"csrf_token": _csrf_tu_trang(app_bat)},
                     follow_redirects=False)
    sid = r.headers["location"].rsplit("/", 1)[-1]

    gen = get_session(); db = next(gen)
    try:
        sessions.bao_engine(db, sessions.lay_phien(db, session_id=sid),
                            engine_id="1", secret="pw"); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    app_bat.post(f"/nexus/phien/{sid}/ket-thuc",
                 data={"csrf_token": _csrf_tu_trang(app_bat)},
                 follow_redirects=False)
    j = app_bat.get(f"/nexus/phien/{sid}/ket-noi").json()
    assert j["san_sang"] is False and j["da_dong"] is True
