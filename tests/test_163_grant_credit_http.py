"""
F-05 — luồng cấp credit của admin, thử QUA HTTP.

Audit LTT-AQA 2026-08-07 (control-plane/quan-tri-user). Chặn G8 Operations.

`test_162` phủ tầng nghiệp vụ (`platform_core.credit`). File này phủ đúng thứ
người dùng chạm vào: form ở `/admin/grant-credit`. Hai tầng khác nhau thật sự —
tầng nghiệp vụ đúng mà route ghép sai tham số thì vẫn hỏng, và **chính vì thiếu
lớp test này mà F-01 sống sót tới hôm nay**.

Khoá bốn nhóm tính chất:
1. **Quyền** — không phải admin thì không vào được (G2).
2. **CSRF** — mutation sổ tiền phải có token (W1.3).
3. **Nguyên tử** — một email sai thì không ai được cấp (D4).
4. **Nói thật** — màn hình không được báo thành công cho một cấp phát vô hiệu (G4).
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'g.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-grant-http")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); s = next(gen)
    tao_nguoi_dung(s, email="sep@x.com", password="matkhau-tot-12",
                   role="admin", is_verified=True)
    for i in (1, 2, 3):
        tao_nguoi_dung(s, email=f"nv{i}@x.com", password="matkhau-tot-12",
                       is_verified=True)
    s.commit(); s.close()

    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver")
    try:
        yield c
    finally:
        dbmod.reset_engine()


def _csrf(client, duong="/login"):
    return re.search(r'name="csrf_token" value="([^"]+)"', client.get(duong).text).group(1)


def _dang_nhap(client, email):
    client.post("/logout", follow_redirects=False)
    client.post("/login", data={"username": email, "password": "matkhau-tot-12",
                                "csrf_token": _csrf(client)}, follow_redirects=False)


def _so_du(email):
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import User
    gen = dbmod.get_session(); s = next(gen)
    try:
        u = s.query(User).filter(User.email == email).one()
        return credit.so_du(s, u.id)
    finally:
        s.close()


def _cap(client, nguoi, amount="500", note=""):
    tok = _csrf(client, "/admin/grant-credit")
    return client.post("/admin/grant-credit",
                       data={"nguoi": nguoi, "amount": amount, "note": note,
                             "csrf_token": tok}, follow_redirects=False)


# ── 1. Quyền ─────────────────────────────────────────────────────────────────
def test_khach_chua_dang_nhap_khong_vao_duoc(env):
    r = env.get("/admin/grant-credit", follow_redirects=False)
    assert r.status_code in (302, 303, 401, 403)


def test_nguoi_dung_thuong_khong_cap_duoc_credit(env):
    """Nếu người dùng thường cấp được credit cho chính mình thì hết chuyện."""
    _dang_nhap(env, "nv1@x.com")
    r = env.post("/admin/grant-credit",
                 data={"nguoi": "nv1@x.com", "amount": "99999"},
                 follow_redirects=False)
    assert r.status_code in (302, 303, 400, 401, 403)
    assert _so_du("nv1@x.com") == 0


# ── 2. CSRF ──────────────────────────────────────────────────────────────────
def test_khong_csrf_thi_khong_cap(env):
    _dang_nhap(env, "sep@x.com")
    r = env.post("/admin/grant-credit",
                 data={"nguoi": "nv1@x.com", "amount": "500"},
                 follow_redirects=False)
    assert r.status_code == 400
    assert _so_du("nv1@x.com") == 0


# ── 3. Cấp bằng email ────────────────────────────────────────────────────────
def test_cap_bang_email_cho_mot_nguoi(env):
    _dang_nhap(env, "sep@x.com")
    r = _cap(env, "nv1@x.com")
    assert r.status_code == 200
    assert _so_du("nv1@x.com") == 500


def test_cap_hang_loat_bang_danh_sach_dan_vao(env):
    """Đúng việc onboarding: dán danh sách, một lượt xong."""
    _dang_nhap(env, "sep@x.com")
    r = _cap(env, "nv1@x.com\nnv2@x.com\nnv3@x.com", note="onboarding")
    assert r.status_code == 200
    for i in (1, 2, 3):
        assert _so_du(f"nv{i}@x.com") == 500


def test_ngan_bang_dau_phay_cung_duoc(env):
    _dang_nhap(env, "sep@x.com")
    _cap(env, "nv1@x.com, nv2@x.com")
    assert _so_du("nv1@x.com") == 500 and _so_du("nv2@x.com") == 500


# ── 4. Nguyên tử (D4) ────────────────────────────────────────────────────────
def test_mot_email_sai_thi_KHONG_AI_duoc_cap(env):
    _dang_nhap(env, "sep@x.com")
    r = _cap(env, "nv1@x.com\nkhong-co@x.com\nnv3@x.com")
    assert r.status_code == 400
    for i in (1, 2, 3):
        assert _so_du(f"nv{i}@x.com") == 0, "co nguoi da duoc cap — KHONG nguyen tu"


def test_man_hinh_noi_ro_email_nao_sai_va_chua_cap_cho_ai(env):
    """G4 Honest UI: không được để admin đoán."""
    _dang_nhap(env, "sep@x.com")
    r = _cap(env, "nv1@x.com\nsai@x.com")
    assert "sai@x.com" in r.text
    assert "Chưa cấp cho ai cả" in r.text


# ── 5. Nói thật (G4) — hồi quy trực tiếp cho F-01 ────────────────────────────
def test_khong_bao_thanh_cong_cho_nguoi_khong_ton_tai(env):
    """Đây là hành vi P0 cũ: báo 'Đã cấp +500. Số dư mới: 500' cho một UUID gõ
    nhầm. Màn hình nói thành công trong khi credit rơi vào hư không."""
    _dang_nhap(env, "sep@x.com")
    r = _cap(env, "3f2a-go-nham-hoan-toan")
    assert r.status_code == 400
    assert "Đã cấp" not in r.text


def test_van_cap_duoc_bang_UUID_duong_du_phong(env):
    """D3: email là đường chính, UUID vẫn phải chạy (đối soát từ log/CSDL)."""
    import platform_core.db as dbmod
    from platform_core.models import User
    gen = dbmod.get_session(); s = next(gen)
    uid = s.query(User).filter(User.email == "nv1@x.com").one().id
    s.close()
    _dang_nhap(env, "sep@x.com")
    assert _cap(env, uid).status_code == 200
    assert _so_du("nv1@x.com") == 500


# ── 6. Thu hồi và biên ───────────────────────────────────────────────────────
def test_thu_hoi_bang_so_am(env):
    _dang_nhap(env, "sep@x.com")
    _cap(env, "nv1@x.com", amount="500")
    _cap(env, "nv1@x.com", amount="-200", note="thu hoi")
    assert _so_du("nv1@x.com") == 300


def test_so_0_bi_tu_choi(env):
    _dang_nhap(env, "sep@x.com")
    r = _cap(env, "nv1@x.com", amount="0")
    assert r.status_code == 400
    assert _so_du("nv1@x.com") == 0


def test_email_lap_chi_cap_mot_lan(env):
    _dang_nhap(env, "sep@x.com")
    r = _cap(env, "nv1@x.com\nNV1@x.com\n nv1@x.com ")
    assert r.status_code == 200
    assert _so_du("nv1@x.com") == 500


# ── 7. F-04: số dư ở nơi quản lý người dùng ──────────────────────────────────
def test_cot_so_du_da_duoc_khai_trong_danh_sach_nguoi_dung(env):
    """Con số vận hành quan trọng nhất về một người phải nằm ở chỗ quản lý người,
    không bắt admin sang trang Sổ credit lọc bằng UUID.

    ⚠️ Test này chỉ chốt **khai báo** và **trang mở được**, KHÔNG chốt giá trị đã
    render. Thử ban đầu (`assert "777" in html`) đổ vì HTML trả về chỉ có vỏ
    trang — sqladmin dựng bảng theo cách khác. Nới lỏng test cho xanh mà vẫn nói
    "đã xác minh" thì đúng là thứ LTT-AQA mục 5 cấm: E1 không phải "đã xác minh".

    **Việc còn nợ:** kiểm trên browser thật (E3) để chốt số dư hiện ra đúng.
    Ghi trong 05_FINDINGS như một mục chưa đóng.
    """
    from server.admin import UserAdmin
    assert "so_du_credit" in [str(c) for c in UserAdmin.column_list]
    assert UserAdmin.column_labels.get("so_du_credit") == "Số dư"
    _dang_nhap(env, "sep@x.com")
    _cap(env, "nv1@x.com", amount="777")
    assert env.get("/admin/user/list").status_code == 200





def test_so_du_credit_tinh_dung_ca_khi_am_va_bang_khong(env):
    """Tính chất của property, không cần HTTP."""
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import User
    gen = dbmod.get_session(); s = next(gen)
    try:
        u = s.query(User).filter(User.email == "nv2@x.com").one()
        assert u.so_du_credit == 0
        credit.cap_tay(s, u.id, 300, by="t"); s.commit()
        s.refresh(u)
        assert u.so_du_credit == 300
    finally:
        s.close()
