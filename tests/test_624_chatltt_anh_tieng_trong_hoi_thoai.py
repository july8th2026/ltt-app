"""
test_624 — Phase 09: tao anh/tieng trong hoi thoai ChatLTT.

  1. Bao gia truoc, KHONG giu tien; gia doi giua chung ⇒ tu choi, khong tru mot
     so khac voi so nguoi dung da dong y.
  2. Tao ⇒ 202 + job that; tien giu dung so da bao; `owner_id` bi ep.
  3. Dong bo: dang chay ⇒ tien do; xong ⇒ khoi artifact dung PHUONG THUC cua
     nang luc; thu theo `credit_cost` THAT, hoan phan du.
  4. Job hong/huy ⇒ khoi loi + hoan DU.
  5. Nang luc ngoai allowlist ⇒ 403 fail-closed.
  6. Reload: `su_that()` mang khoi artifact — trinh duyet khong giu gi.
"""
from __future__ import annotations

import re
import uuid

import pytest

TOOL_ANH = "image.ltt"
TOOL_TIENG = "speech.ltt"


@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "m.db").as_posix())
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
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "chatltt-secret-624",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    dbmod.reset_engine()


def _user(credits=1000):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        email = "m624-" + uuid.uuid4().hex[:6] + "@example.com"
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


def _dang_nhap(web, email):
    r = web.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    web.post("/login", data={"username": email, "password": "a-good-password-12",
                             "csrf_token": m.group(1), "next": "/chatltt"},
             follow_redirects=True)
    r = web.get("/chatltt")
    return {"X-CSRF-Token": re.search(r'data-csrf="([^"]+)"', r.text).group(1)}


def _so_du(user_id):
    from platform_core import credit
    from platform_core.db import get_session
    gen = get_session()
    db = next(gen)
    try:
        return int(credit.so_du(db, user_id))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _job(job_id):
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session()
    db = next(gen)
    try:
        return db.get(Job, job_id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _dat_job(job_id, **g):
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session()
    db = next(gen)
    try:
        j = db.get(Job, job_id)
        for k, v in g.items():
            setattr(j, k, v)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _tao_hoi_thoai(web, h):
    return web.post("/chatltt/api/hoi-thoai", json={"model_alias": "ltt_llm"},
                    headers=h).json()["id"]


# ── 1. Bao gia ───────────────────────────────────────────────────────────────

def test_bao_gia_khong_giu_tien_va_tu_choi_tham_so_sai(web):
    uid, email = _user(1000)
    h = _dang_nhap(web, email)
    r = web.post("/chatltt/api/bao-gia", headers=h, json={
        "nang_luc": TOOL_ANH, "tham_so": {"prompt": "mot con meo", "count": 2}})
    assert r.status_code == 200, r.text
    bg = r.json()
    assert bg["nang_luc"] == TOOL_ANH and bg["credit"] > 0
    assert bg["phien_ban_gia"]
    assert _so_du(uid) == 1000                       # chua tru gi

    # 4 anh dat hon 2 anh — gia phu thuoc tham so, khong phai gia phang.
    r4 = web.post("/chatltt/api/bao-gia", headers=h, json={
        "nang_luc": TOOL_ANH, "tham_so": {"prompt": "meo", "count": 4}})
    assert r4.json()["credit"] > bg["credit"]

    assert web.post("/chatltt/api/bao-gia", headers=h, json={
        "nang_luc": TOOL_ANH, "tham_so": {"prompt": "meo", "count": 99}},
    ).status_code == 400
    assert web.post("/chatltt/api/bao-gia", headers=h,
                    json={"nang_luc": TOOL_ANH, "tham_so": {}}).status_code == 400


def test_nang_luc_ngoai_allowlist_bi_tu_choi(web):
    _uid, email = _user(100)
    h = _dang_nhap(web, email)
    for ten in ("image.generate", "video.subtitle", "khong.co"):
        r = web.post("/chatltt/api/bao-gia", headers=h,
                     json={"nang_luc": ten, "tham_so": {"prompt": "x"}})
        assert r.status_code == 403, ten
        assert r.json()["error"]["code"] == "khong_duoc_phep"


# ── 2 + 3. Tao anh: giu tien, xong, thu theo so THAT ─────────────────────────

def test_tao_anh_giu_dung_so_da_bao_roi_thu_theo_anh_that(web):
    uid, email = _user(1000)
    h = _dang_nhap(web, email)
    cv = _tao_hoi_thoai(web, h)
    bg = web.post("/chatltt/api/bao-gia", headers=h, json={
        "nang_luc": TOOL_ANH, "tham_so": {"prompt": "meo", "count": 4}}).json()

    r = web.post(f"/chatltt/api/hoi-thoai/{cv}/tao", headers=h, json={
        "nang_luc": TOOL_ANH, "tham_so": {"prompt": "meo", "count": 4},
        "credit": bg["credit"]})
    assert r.status_code == 202, r.text
    kq = r.json()
    assert kq["credit"] == bg["credit"]
    assert _so_du(uid) == 1000 - bg["credit"]

    job = _job(kq["job_id"])
    assert job.app_slug == "anhnoibo" and job.job_type == "anhnoibo.generate"
    assert job.params["owner_id"] == uid                 # ep tu phien, khong tu than
    assert job.params["count"] == 4

    # Dang chay ⇒ tien do; chua thu gi.
    _dat_job(job.id, status="running", progress=40)
    st = web.get(f"/chatltt/api/luot/{kq['execution_id']}/trang-thai", headers=h).json()
    assert st["status"] == "queued" and st["usage"]["progress"] == 40
    assert _so_du(uid) == 1000 - bg["credit"]

    # Xong nhung chi 2 anh: thu theo `credit_cost` THAT, hoan phan du.
    from platform_core import credit as C
    from platform_core.db import get_session
    gen = get_session()
    db = next(gen)
    try:
        j = _job(kq["job_id"])
        thu_that = 6
        C.quyet_toan(db, uid, j.id, thu_that)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    _dat_job(kq["job_id"], status="done", result={
        "image_keys": [f"anhnoibo/{uid}/{kq['job_id']}/0.png",
                       f"anhnoibo/{uid}/{kq['job_id']}/1.png"],
        "prompt": "meo", "so_anh_xin": 4, "so_anh_that": 2, "credit_cost": 6})

    st = web.get(f"/chatltt/api/luot/{kq['execution_id']}/trang-thai", headers=h).json()
    assert st["status"] == "done"
    assert st["credit"]["thu"] == 6 and st["credit"]["hoan"] == bg["credit"] - 6

    # Khoi artifact vao message — reload thay ngay, khong giu gi o trinh duyet.
    su = web.get(f"/chatltt/api/hoi-thoai/{cv}", headers=h).json()
    tin = {m["id"]: m for m in su["messages"]}[kq["message_id"]]
    assert tin["status"] == "done"
    assert [k["type"] for k in tin["blocks"]] == ["image", "image"]
    assert all(k["key"].startswith(f"anhnoibo/{uid}/") for k in tin["blocks"])


def test_tao_tieng_sinh_khoi_audio(web):
    uid, email = _user(1000)
    h = _dang_nhap(web, email)
    cv = _tao_hoi_thoai(web, h)
    bg = web.post("/chatltt/api/bao-gia", headers=h, json={
        "nang_luc": TOOL_TIENG, "tham_so": {"text": "xin chao cac ban"}}).json()
    kq = web.post(f"/chatltt/api/hoi-thoai/{cv}/tao", headers=h, json={
        "nang_luc": TOOL_TIENG, "tham_so": {"text": "xin chao cac ban"},
        "credit": bg["credit"]}).json()
    khoa = f"voice/out/{uid}/{kq['job_id']}/tieng.wav"
    _dat_job(kq["job_id"], status="done",
             result={"audio_key": khoa, "text": "xin chao cac ban",
                     "duration_s": 2.5, "credit_cost": 1})
    web.get(f"/chatltt/api/luot/{kq['execution_id']}/trang-thai", headers=h)
    su = web.get(f"/chatltt/api/hoi-thoai/{cv}", headers=h).json()
    tin = {m["id"]: m for m in su["messages"]}[kq["message_id"]]
    assert tin["blocks"] == [{"type": "audio", "key": khoa}]
    # Tran 1.500 ky tu cua voice van chan o cua bao gia — khong noi.
    # ⚠️ Lấy trần từ hằng số, KHÔNG gõ `1501`. Con số ấy đúng tới 03/09/2026 rồi
    #    hết đúng khi trần công khai được nới (1.500 -> 100.000). Mệnh đề cần
    #    canh là *"vượt trần thì cửa trả 400"*, và nó không đổi theo con số.
    from apps.ltt_voice.tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI as _TRAN
    assert web.post("/chatltt/api/bao-gia", headers=h, json={
        "nang_luc": TOOL_TIENG, "tham_so": {"text": "a" * (_TRAN + 1)}},
    ).status_code == 400


# ── 4. Hong / huy ⇒ hoan DU ──────────────────────────────────────────────────

@pytest.mark.parametrize("tt,ma", [("error", "that_bai"), ("cancelled", "huy")])
def test_job_hong_hoac_huy_thi_hoan_du_va_noi_ra(web, tt, ma):
    uid, email = _user(1000)
    h = _dang_nhap(web, email)
    cv = _tao_hoi_thoai(web, h)
    bg = web.post("/chatltt/api/bao-gia", headers=h, json={
        "nang_luc": TOOL_ANH, "tham_so": {"prompt": "meo"}}).json()
    kq = web.post(f"/chatltt/api/hoi-thoai/{cv}/tao", headers=h, json={
        "nang_luc": TOOL_ANH, "tham_so": {"prompt": "meo"},
        "credit": bg["credit"]}).json()
    from platform_core import credit as C
    from platform_core.db import get_session
    gen = get_session()
    db = next(gen)
    try:
        C.hoan(db, uid, kq["job_id"])
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    _dat_job(kq["job_id"], status=tt, error="may B khong tra loi")
    st = web.get(f"/chatltt/api/luot/{kq['execution_id']}/trang-thai", headers=h).json()
    assert st["status"] == "failed" and st["error_code"] == ma
    assert st["credit"]["thu"] == 0 and st["credit"]["hoan"] == bg["credit"]
    assert _so_du(uid) == 1000
    su = web.get(f"/chatltt/api/hoi-thoai/{cv}", headers=h).json()
    tin = {m["id"]: m for m in su["messages"]}[kq["message_id"]]
    assert tin["blocks"][0]["type"] == "error"


# ── 5. Gia doi giua chung ────────────────────────────────────────────────────

def test_gia_doi_thi_tu_choi_thay_vi_tru_mot_so_khac(web):
    uid, email = _user(1000)
    h = _dang_nhap(web, email)
    cv = _tao_hoi_thoai(web, h)
    r = web.post(f"/chatltt/api/hoi-thoai/{cv}/tao", headers=h, json={
        "nang_luc": TOOL_ANH, "tham_so": {"prompt": "meo", "count": 4},
        "credit": 1})                                   # so bia, thap hon that
    assert r.status_code == 400 and r.json()["error"]["code"] == "tham_so"
    assert _so_du(uid) == 1000


def test_thieu_credit_thi_402_va_khong_tao_job(web):
    from platform_core.db import get_session
    from platform_core.models import Job
    uid, email = _user(1)
    h = _dang_nhap(web, email)
    cv = _tao_hoi_thoai(web, h)
    bg = web.post("/chatltt/api/bao-gia", headers=h, json={
        "nang_luc": TOOL_ANH, "tham_so": {"prompt": "meo", "count": 4}}).json()
    r = web.post(f"/chatltt/api/hoi-thoai/{cv}/tao", headers=h, json={
        "nang_luc": TOOL_ANH, "tham_so": {"prompt": "meo", "count": 4},
        "credit": bg["credit"]})
    assert r.status_code == 402 and r.json()["error"]["code"] == "het_credit"
    gen = get_session()
    db = next(gen)
    try:
        assert db.query(Job).filter(Job.user_id == uid).count() == 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
