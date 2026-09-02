"""
test_625 — Phase 09: cua phuc vu tai san cua ChatLTT. Day la be mat NHAY CAM
nhat cua app: no doc thang tu kho theo mot khoa nguoi goi dua.

  1. Chu so huu doc duoc anh cua minh, dung kieu MIME.
  2. Nguoi khac va khoa bia deu tra CUNG mot 404 — khac nhau se noi cho ke do
     biet khoa nao co that.
  3. Path traversal, khoa la hinh, khoa cua app khac ⇒ 404.
  4. `kiem_so_huu_khoa` fail-closed: chi HAI hinh duoc phep.
"""
from __future__ import annotations

import io
import re
import uuid

import pytest

from apps.chatltt.services.tao_media import kiem_so_huu_khoa

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


# ── 4. Ham thuan: chi hai hinh ───────────────────────────────────────────────

def test_kiem_so_huu_khoa_chi_cho_hai_hinh():
    u = "u-1"
    assert kiem_so_huu_khoa(f"anhnoibo/{u}/job1/0.png", u) is True
    assert kiem_so_huu_khoa(f"voice/out/{u}/job1/tieng.wav", u) is True
    for xau in [
        f"anhnoibo/u-khac/job1/0.png",           # cua nguoi khac
        f"voice/out/u-khac/job1/tieng.wav",
        f"voice/{u}/source.wav",                 # clip GOC cua khach — khong phai cua nay
        f"anhnoibo/{u}/0.png",                   # thieu doan job
        f"thumbnail/{u}/job1/0.png",             # app khac
        f"staging/{u}/x.png",
        f"../anhnoibo/{u}/job1/0.png",
        f"anhnoibo/{u}/../../secrets/app.env",
        "", "/", f"anhnoibo//{u}/0.png",
    ]:
        assert kiem_so_huu_khoa(xau, u) is False, xau


# ── 1-3. Qua HTTP that ───────────────────────────────────────────────────────

@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    import platform_core.storage as st
    st._storage = None
    from fastapi.testclient import TestClient
    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "chatltt-secret-625",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    st._storage = None
    dbmod.reset_engine()


def _user():
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        email = "t625-" + uuid.uuid4().hex[:6] + "@example.com"
        u = tao_nguoi_dung(db, email=email, password="a-good-password-12", is_verified=True)
        db.commit()
        return u.id, email
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _dang_nhap(web, email):
    r = web.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    web.post("/login", data={"username": email, "password": "a-good-password-12",
                             "csrf_token": m.group(1), "next": "/chatltt"},
             follow_redirects=True)


def _dat_tep(khoa: str, data: bytes):
    from platform_core import storage
    storage.get_storage().put(khoa, io.BytesIO(data), content_type="application/octet-stream")


def test_chu_so_huu_doc_duoc_nguoi_khac_khong(web):
    from fastapi.testclient import TestClient
    uid_a, email_a = _user()
    _dang_nhap(web, email_a)
    khoa = f"anhnoibo/{uid_a}/job1/0.png"
    _dat_tep(khoa, PNG)
    khoa_tieng = f"voice/out/{uid_a}/job1/tieng.wav"
    _dat_tep(khoa_tieng, b"RIFF....WAVE")

    r = web.get(f"/chatltt/tai-san/{khoa}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content == PNG
    assert web.get(f"/chatltt/tai-san/{khoa_tieng}").headers["content-type"] == "audio/wav"

    # Nguoi B: cung tep, cung duong ⇒ 404. Va khoa BIA cung 404 — khong phan biet.
    uid_b, email_b = _user()
    b = TestClient(web.app, base_url="https://testserver")
    _dang_nhap(b, email_b)
    r_nguoi_khac = b.get(f"/chatltt/tai-san/{khoa}")
    r_khoa_bia = b.get(f"/chatltt/tai-san/anhnoibo/{uid_b}/job-khong-co/0.png")
    assert r_nguoi_khac.status_code == r_khoa_bia.status_code == 404
    assert r_nguoi_khac.json() == r_khoa_bia.json()      # cung mot cau, khong ro ri


def test_chua_dang_nhap_thi_khong_vao_duoc(web):
    uid, _email = _user()
    _dat_tep(f"anhnoibo/{uid}/job1/0.png", PNG)
    r = web.get(f"/chatltt/tai-san/anhnoibo/{uid}/job1/0.png", follow_redirects=False)
    assert r.status_code in (302, 303, 401)
    assert PNG not in r.content


@pytest.mark.parametrize("xau", [
    "../../secrets/app.env",
    "anhnoibo/../../data/config.json",
    "voice/mau/adam.wav",
    "staging/x.png",
])
def test_khoa_la_hinh_deu_404(web, xau):
    _uid, email = _user()
    _dang_nhap(web, email)
    assert web.get(f"/chatltt/tai-san/{xau}").status_code == 404
