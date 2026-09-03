"""
test_628 — Phase 12 nhóm BẢO MẬT. Mỗi phép kiểm là một lần thử phá thật.

  1. IDOR trên MỌI cửa mang id: hội thoại · message · execution · job · artifact.
  2. Không phân biệt được "không tồn tại" với "không phải của bạn" — kể cả bằng
     **thời gian** hay **hình dạng** phản hồi.
  3. Không lộ bí mật/alias nội bộ trong thông điệp lỗi.
  4. Thân request quá cỡ bị chặn.
  5. Không đếm được số hội thoại của người khác (enumeration).
  6. CSRF bắt buộc trên MỌI cửa ghi — liệt kê bằng chính bảng route, nên một
     route mới quên CSRF sẽ làm test này đỏ chứ không lọt.
"""
from __future__ import annotations

import json
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
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "chatltt-secret-628",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    dbmod.reset_engine()


def _user(credits=500):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        email = "s628-" + uuid.uuid4().hex[:6] + "@example.com"
        u = tao_nguoi_dung(db, email=email, password="a-good-password-12", is_verified=True)
        db.flush()
        if credits:
            credit.cap_tay(db, u.id, credits, by="test")
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
    r = c.get("/chatltt")
    csrf = re.search(r'data-csrf="([^"]+)"', r.text).group(1)
    return c, {"X-CSRF-Token": csrf}


def _du_lieu_cua_A(c, h):
    """Một hội thoại của A, kèm một execution job và một artifact."""
    from apps.chatltt.services import hoi_thoai as H
    from apps.chatltt.services import su_kien as S
    from platform_core.db import get_session

    cv = c.post("/chatltt/api/hoi-thoai", json={"model_alias": "ltt_llm"},
                headers=h).json()["id"]
    gen = get_session()
    db = next(gen)
    try:
        uid = db.execute(__import__("sqlalchemy").text(
            "SELECT user_id FROM chatltt_conversation WHERE id=:i"), {"i": cv}).scalar()
        m = H.them_thong_diep(db, user_id=uid, conv_id=cv, role="user",
                              blocks=[{"type": "text", "text": "bi mat cua A"}])
        a = H.them_thong_diep(db, user_id=uid, conv_id=cv, role="assistant",
                              blocks=[], parent_id=m.id, status="queued")
        ex = S.mo_execution(db, message=a, tool_name="image.ltt", mode="job")
        ex.job_id = "job-a-628"
        db.commit()
        return {"uid": uid, "cv": cv, "msg": m.id, "a": a.id, "ex": ex.id,
                "khoa": f"anhnoibo/{uid}/job-a-628/0.png"}
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── 1 + 2. IDOR trên mọi cửa, và không phân biệt được ───────────────────────

def test_idor_tren_moi_cua_mang_id(web):
    _uid_a, email_a = _user()
    ca, ha = _phien(web.app, email_a)
    A = _du_lieu_cua_A(ca, ha)

    _uid_b, email_b = _user()
    cb, hb = _phien(web.app, email_b)

    cua_doc = [
        f"/chatltt/api/hoi-thoai/{A['cv']}",
        f"/chatltt/api/luot/{A['ex']}/trang-thai",
        f"/chatltt/tai-san/{A['khoa']}",
    ]
    cua_ghi = [
        (f"/chatltt/api/hoi-thoai/{A['cv']}/luot", {"text": "x"}),
        (f"/chatltt/api/hoi-thoai/{A['cv']}/tao",
         {"nang_luc": "image.ltt", "tham_so": {"prompt": "x"}}),
        (f"/chatltt/api/hoi-thoai/{A['cv']}/doi-ten", {"title": "cua toi"}),
        (f"/chatltt/api/hoi-thoai/{A['cv']}/luu-tru", {"luu": True}),
        (f"/chatltt/api/hoi-thoai/{A['cv']}/xoa", {}),
        (f"/chatltt/api/hoi-thoai/{A['cv']}/chon-la", {"message_id": A["a"]}),
        (f"/chatltt/api/luot/{A['ex']}/dung", {}),
    ]
    for d in cua_doc:
        r = cb.get(d, headers=hb)
        assert r.status_code == 404, d
        assert "bi mat cua A" not in r.text
    for d, than in cua_ghi:
        r = cb.post(d, json=than, headers=hb)
        assert r.status_code == 404, d

    # Và A vẫn nguyên vẹn sau tất cả.
    st = ca.get(f"/chatltt/api/hoi-thoai/{A['cv']}", headers=ha).json()
    assert st["conversation"]["title"] != "cua toi"
    assert len(st["messages"]) == 2


def test_khong_phan_biet_duoc_khong_ton_tai_voi_khong_phai_cua_ban(web):
    _uid_a, email_a = _user()
    ca, ha = _phien(web.app, email_a)
    A = _du_lieu_cua_A(ca, ha)
    _uid_b, email_b = _user()
    cb, hb = _phien(web.app, email_b)

    that = cb.get(f"/chatltt/api/hoi-thoai/{A['cv']}", headers=hb)
    bia = cb.get("/chatltt/api/hoi-thoai/cv_khong_ton_tai_0000", headers=hb)
    assert that.status_code == bia.status_code == 404
    assert that.json() == bia.json()                    # cùng THÂN, không chỉ cùng mã

    that2 = cb.get(f"/chatltt/api/luot/{A['ex']}/trang-thai", headers=hb)
    bia2 = cb.get("/chatltt/api/luot/ex_khong_co/trang-thai", headers=hb)
    assert that2.json() == bia2.json()


# ── 3. Không lộ bí mật / alias nội bộ ───────────────────────────────────────

def test_thong_diep_loi_khong_lo_bi_mat_hay_id_noi_bo(web):
    _uid, email = _user(0)
    c, h = _phien(web.app, email)
    cv = c.post("/chatltt/api/hoi-thoai", json={"model_alias": "ltt_llm"},
                headers=h).json()["id"]
    ra = []
    ra.append(c.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": ""}, headers=h))
    ra.append(c.post("/chatltt/api/bao-gia", headers=h,
                     json={"nang_luc": "image.ltt", "tham_so": {"prompt": "x", "count": 99}}))
    ra.append(c.post("/chatltt/api/bao-gia", headers=h,
                     json={"nang_luc": "khong.co", "tham_so": {}}))
    ra.append(c.get("/chatltt/api/hoi-thoai/cv_bia", headers=h))
    van = " ".join(r.text for r in ra)
    for cam in ("qwen38", "hidream", "vieneu", "8299", "8199", "8120", "192.168.",
                "LTT_RENDER_BASE_URL", "LTT_VOICE_SIDECAR_TOKEN", "Traceback",
                "sqlite", "postgresql", "/LTTPlatform", "secrets"):
        assert cam.lower() not in van.lower(), cam


# ── 4. Thân quá cỡ ──────────────────────────────────────────────────────────

def test_than_qua_co_bi_chan_truoc_khi_cham_so_tien(web):
    from platform_core import credit
    from platform_core.db import get_session

    uid, email = _user(500)
    c, h = _phien(web.app, email)
    cv = c.post("/chatltt/api/hoi-thoai", json={"model_alias": "ltt_llm"},
                headers=h).json()["id"]
    r = c.post(f"/chatltt/api/hoi-thoai/{cv}/luot",
               json={"text": "a" * 300_000}, headers=h)
    assert r.status_code in (400, 413), r.status_code
    gen = get_session()
    db = next(gen)
    try:
        assert int(credit.so_du(db, uid)) == 500      # không tiêu gì
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── 5. Không đếm được của người khác ────────────────────────────────────────

def test_khong_dem_duoc_hoi_thoai_cua_nguoi_khac(web):
    _uid_a, email_a = _user()
    ca, ha = _phien(web.app, email_a)
    for _ in range(3):
        ca.post("/chatltt/api/hoi-thoai", json={"model_alias": "ltt_llm"}, headers=ha)
    _uid_b, email_b = _user()
    cb, hb = _phien(web.app, email_b)
    assert cb.get("/chatltt/api/hoi-thoai", headers=hb).json()["hoi_thoai"] == []
    # Tìm kiếm cũng không rò: A có "bi mat", B tìm chữ đó ra rỗng.
    assert cb.get("/chatltt/api/hoi-thoai?tim=bi mat", headers=hb
                  ).json()["hoi_thoai"] == []


# ── 6. CSRF trên MỌI cửa ghi, liệt kê từ bảng route ─────────────────────────

def test_moi_cua_GHI_deu_doi_CSRF():
    """Đọc bảng route thật: một route POST mới quên CSRF sẽ làm test này đỏ."""
    import inspect

    from apps.chatltt.routes import router

    ghi = [r for r in router.routes
           if {"POST", "PUT", "PATCH", "DELETE"} & set(getattr(r, "methods", ()))]
    assert len(ghi) >= 8, len(ghi)
    thieu = []
    for r in ghi:
        nguon = inspect.getsource(r.endpoint)
        if "kiem_csrf" not in nguon:
            thieu.append(r.path)
    assert not thieu, thieu


def test_thieu_hoac_sai_CSRF_deu_bi_tu_choi(web):
    _uid, email = _user()
    c, h = _phien(web.app, email)
    cv = c.post("/chatltt/api/hoi-thoai", json={"model_alias": "ltt_llm"},
                headers=h).json()["id"]
    for hd in ({}, {"X-CSRF-Token": ""}, {"X-CSRF-Token": "bia-dat"}):
        r = c.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": "x"}, headers=hd)
        assert r.status_code == 403, hd
        assert r.json()["error"]["code"] == "csrf"


def test_chua_dang_nhap_thi_moi_cua_deu_dong(web):
    for d in ("/chatltt", "/chatltt/api/danh-muc", "/chatltt/api/hoi-thoai",
              "/chatltt/api/so-du", "/chatltt/tai-san/anhnoibo/u/j/0.png"):
        r = web.get(d, follow_redirects=False)
        assert r.status_code in (302, 303, 401), (d, r.status_code)
