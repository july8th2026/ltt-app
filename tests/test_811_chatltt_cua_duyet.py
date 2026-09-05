"""
test_811 — hai cửa HTTP của duyệt. (H44 P04)

`test_809` đã ghim luật ở tầng service. Tệp này ghim thứ **chỉ hỏng ở tầng
route**: một handler quên truyền `user_id` xuống, một enum nhận chuỗi tuỳ ý,
một mã lỗi nói quá nhiều.

⭐ Vì sao phải có cả hai tầng: `test_628::test_idor_tren_moi_cua_mang_id` liệt
kê cửa bằng một **danh sách chép tay** — nó không tự biết có cửa mới. Cửa duyệt
mang id, nên nó phải được thử IDOR ở đâu đó, và đây là chỗ đó.
"""
from __future__ import annotations

import re
import uuid

import pytest


@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "s.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    from fastapi.testclient import TestClient
    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "chatltt-secret-811",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    dbmod.reset_engine()


def _user():
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        email = "s811-" + uuid.uuid4().hex[:6] + "@example.com"
        u = tao_nguoi_dung(db, email=email, password="a-good-password-12",
                           is_verified=True)
        db.commit()
        return u.id, email
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _phien(app, email):
    from fastapi.testclient import TestClient
    c = TestClient(app, base_url="https://testserver")
    r = c.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    c.post("/login", data={"username": email, "password": "a-good-password-12",
                           "csrf_token": m.group(1), "next": "/chatltt"},
           follow_redirects=True)
    csrf = re.search(r'data-csrf="([^"]+)"', c.get("/chatltt").text).group(1)
    return c, {"X-CSRF-Token": csrf}


def _phieu(user_id, *, step="st_1", gia=12):
    """Một phiếu chờ thuộc `user_id`, tạo thẳng ở tầng service."""
    from apps.chatltt.services import duyet as D
    from platform_core.db import get_session
    gen = get_session()
    db = next(gen)
    try:
        p = D.xin_duyet(db, user_id=user_id, run_id="run_811", step_id=step,
                        tool_name="image.ltt", doi_so={"prompt": "meo"},
                        policy_class="PAID", bao_gia_credit=gia,
                        phien_ban_gia="ltt-vlm-2026-08-22", bam_trung="bam-" + step)
        db.commit()
        return p.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── 1. Đọc: dựng lại được sau reload ───────────────────────────────────────

def test_dang_cho_tra_ve_phieu_cua_chinh_minh(web):
    uid, email = _user()
    c, h = _phien(web.app, email)
    ap = _phieu(uid)
    ds = c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"]
    assert len(ds) == 1
    assert ds[0]["approval_id"] == ap and ds[0]["credit"] == 12


def test_dang_cho_KHONG_thay_phieu_cua_nguoi_khac(web):
    uid_a, email_a = _user()
    _phieu(uid_a)
    _uid_b, email_b = _user()
    cb, hb = _phien(web.app, email_b)
    assert cb.get("/chatltt/api/duyet/dang-cho", headers=hb).json()["items"] == []


def test_dang_cho_no_store(web):
    """Một phiếu duyệt bị Cloudflare cache là một nút bấm cho một việc đã xong."""
    _uid, email = _user()
    c, h = _phien(web.app, email)
    r = c.get("/chatltt/api/duyet/dang-cho", headers=h)
    assert "no-store" in r.headers.get("Cache-Control", "")


def test_chua_dang_nhap_thi_khong_doc_duoc(web):
    from fastapi.testclient import TestClient
    r = TestClient(web.app, base_url="https://testserver").get(
        "/chatltt/api/duyet/dang-cho", follow_redirects=False)
    assert r.status_code in (302, 303, 401)


# ── 2. Ghi: IDOR, CSRF, enum ───────────────────────────────────────────────

def test_IDOR_nguoi_khac_khong_duyet_duoc_phieu_cua_toi(web):
    """🔴 Cửa mang id ⇒ phải thử IDOR. Và mã trả về phải là **404**, không phải
    403: nói "không có quyền" là xác nhận phiếu ấy tồn tại."""
    uid_a, _email_a = _user()
    ap = _phieu(uid_a)
    _uid_b, email_b = _user()
    cb, hb = _phien(web.app, email_b)
    r = cb.post(f"/chatltt/api/duyet/{ap}", json={"quyet_dinh": "duyet"}, headers=hb)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "khong_tim_thay"


def test_phieu_khong_co_that_va_phieu_nguoi_khac_TRA_VE_GIONG_NHAU(web):
    """⛔ Hai phản hồi khác nhau là một kênh đếm: người ngoài dò được phiếu nào
    tồn tại. Cùng luật `test_628` mục 2."""
    uid_a, _ = _user()
    ap = _phieu(uid_a)
    _uid_b, email_b = _user()
    cb, hb = _phien(web.app, email_b)
    r1 = cb.post(f"/chatltt/api/duyet/{ap}", json={"quyet_dinh": "duyet"}, headers=hb)
    r2 = cb.post("/chatltt/api/duyet/ap_khong_ton_tai",
                 json={"quyet_dinh": "duyet"}, headers=hb)
    assert (r1.status_code, r1.json()) == (r2.status_code, r2.json())


@pytest.mark.parametrize("hd", [{}, {"X-CSRF-Token": ""}, {"X-CSRF-Token": "bia"}])
def test_thieu_hoac_sai_CSRF_bi_tu_choi(web, hd):
    uid, email = _user()
    c, _h = _phien(web.app, email)
    ap = _phieu(uid)
    r = c.post(f"/chatltt/api/duyet/{ap}", json={"quyet_dinh": "duyet"}, headers=hd)
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf"


@pytest.mark.parametrize("gt", ["", "Duyet", "DUYET", " duyet ", "yes", "ok",
                                "1", "tu-choi", "tuchoi", None, 1, True, ["duyet"]])
def test_quyet_dinh_la_ENUM_DONG(web, gt):
    """🔴 So `== "duyet"` rồi coi mọi thứ khác là từ chối thì một lỗi chính tả ở
    client trở thành một quyết định thay người dùng. Ở đây giá trị lạ là **400**,
    không phải một quyết định.

    ⭐ Kể cả `"Duyet"` — thứ không mơ hồ với người đọc. Chuẩn ở kho này cho một
       giá trị **có hậu quả** đã đặt ở `co_v3.BAT`: chỉ vài cách viết, mọi thứ
       khác là không. Client là app React của chính ta gửi một hằng số, nên một
       `400` ở đây là lỗi lập trình bị bắt sớm, không phải người dùng bị chặn.

    ⚠️ `True` có mặt vì Python coi `True == 1`; một phép so lỏng sẽ cho nó lọt.
    """
    uid, email = _user()
    c, h = _phien(web.app, email)
    ap = _phieu(uid)
    r = c.post(f"/chatltt/api/duyet/{ap}", json={"quyet_dinh": gt}, headers=h)
    assert r.status_code == 400 and r.json()["error"]["code"] == "tham_so"

    from apps.chatltt.services import duyet as D
    ds = c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"]
    assert len(ds) == 1, f"phieu phai CON CHO sau mot {D.CHO!r} khong hop le"


def test_duyet_thanh_cong(web):
    uid, email = _user()
    c, h = _phien(web.app, email)
    ap = _phieu(uid)
    r = c.post(f"/chatltt/api/duyet/{ap}", json={"quyet_dinh": "duyet"}, headers=h)
    assert r.status_code == 200
    assert r.json() == {"type": "approval.granted", "approval_id": ap}
    assert c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"] == []


def test_tu_choi_thanh_cong(web):
    uid, email = _user()
    c, h = _phien(web.app, email)
    ap = _phieu(uid)
    r = c.post(f"/chatltt/api/duyet/{ap}", json={"quyet_dinh": "tu_choi"}, headers=h)
    assert r.json()["type"] == "approval.denied"


def test_bam_LAN_HAI_tra_409_khong_phai_400(web):
    """⭐ 409 chứ không 400: yêu cầu **hợp lệ**, chỉ là thế giới đã đổi. Client
    phân biệt được "tôi gửi sai" với "ai đó đã bấm trước tôi" — và hai câu ấy
    hiện ra cho người dùng phải khác nhau."""
    uid, email = _user()
    c, h = _phien(web.app, email)
    ap = _phieu(uid)
    c.post(f"/chatltt/api/duyet/{ap}", json={"quyet_dinh": "duyet"}, headers=h)
    r = c.post(f"/chatltt/api/duyet/{ap}", json={"quyet_dinh": "tu_choi"}, headers=h)
    assert r.status_code == 409 and r.json()["error"]["code"] == "da_quyet"


def test_doi_so_da_sua_di_qua_va_hien_o_phan_hoi(web):
    uid, email = _user()
    c, h = _phien(web.app, email)
    ap = _phieu(uid)
    r = c.post(f"/chatltt/api/duyet/{ap}",
               json={"quyet_dinh": "duyet", "doi_so_da_sua": {"prompt": "cho"}},
               headers=h)
    assert r.json()["doi_so_da_sua"] == {"prompt": "cho"}


def test_doi_so_da_sua_KHONG_phai_object_thi_400(web):
    """Nhận một chuỗi rồi `dict(...)` nó là một `ValueError` ở tầng CSDL — xa
    chỗ gây ra, và thông điệp không nói được gì cho người gọi."""
    uid, email = _user()
    c, h = _phien(web.app, email)
    ap = _phieu(uid)
    r = c.post(f"/chatltt/api/duyet/{ap}",
               json={"quyet_dinh": "duyet", "doi_so_da_sua": "prompt=cho"}, headers=h)
    assert r.status_code == 400


def test_loi_KHONG_lo_gi_ve_ben_trong(web):
    """Thông điệp lỗi không được mang tên bảng, đường dẫn, hay alias nội bộ."""
    _uid_a, _ = _user()
    _uid_b, email_b = _user()
    cb, hb = _phien(web.app, email_b)
    chu = cb.post("/chatltt/api/duyet/ap_x", json={"quyet_dinh": "duyet"},
                  headers=hb).text.lower()
    for cam in ("chatltt_approval", "sqlite", "traceback", "select ", "d:\\"):
        assert cam not in chu, cam


# ── 3. Cửa mới phải nằm trong bảng route ───────────────────────────────────

def test_hai_cua_da_dang_ky(web):
    from apps.chatltt.routes import router
    duong = {r.path for r in router.routes}
    assert "/api/duyet/dang-cho" in duong
    assert "/api/duyet/{approval_id}" in duong
